"""Non-QP controller baselines for foundation-model control experiments."""

from __future__ import annotations

from typing import Any

import numpy as np

from controllers.qp_controller import COL_LOAD, COL_PRICE, COL_SOLAR


class SharedBatteryControllerBase:
    """Utility base for controllers that emit one shared normalized battery action."""

    def __init__(
        self,
        horizon: int = 24,
        num_buildings: int = 1,
        battery_capacity: float | list[float] | np.ndarray = 4.0,
        battery_nominal_power: float | list[float] | np.ndarray | None = None,
        soc_min: float | list[float] | np.ndarray = 0.0,
        soc_max: float | list[float] | np.ndarray = 1.0,
        p_max: float = 1.0,
        efficiency: float | list[float] | np.ndarray = 0.95,
        time_step_hours: float = 1.0,
    ):
        self.horizon = int(horizon)
        self.num_buildings = int(num_buildings)
        self.p_max = float(p_max)
        self.time_step_hours = float(time_step_hours)
        self.battery_capacity = self._as_array(battery_capacity, self.num_buildings)
        self.battery_nominal_power = self._as_array(
            1.0 if battery_nominal_power is None else battery_nominal_power,
            self.num_buildings,
        )
        self.soc_min = self._as_array(soc_min, self.num_buildings)
        self.soc_max = self._as_array(soc_max, self.num_buildings)
        self.efficiency = self._as_array(efficiency, self.num_buildings)
        self.aggregate_storage_power = float(np.sum(self.battery_nominal_power) * self.time_step_hours)
        self.charge_gain = (
            self.efficiency * self.battery_nominal_power * self.time_step_hours
        ) / self.battery_capacity
        self.discharge_gain = (
            self.battery_nominal_power * self.time_step_hours
        ) / (self.efficiency * self.battery_capacity)

    @staticmethod
    def _as_array(value: float | list[float] | np.ndarray, length: int) -> np.ndarray:
        arr = np.asarray(value, dtype=np.float32)
        if arr.ndim == 0:
            return np.full(length, float(arr), dtype=np.float32)
        arr = arr.reshape(-1)
        if len(arr) != length:
            raise ValueError(f"Expected {length} values, got {len(arr)}")
        return arr.astype(np.float32)

    def _parse_soc(self, state: dict[str, Any]) -> np.ndarray:
        return self._as_array(state["soc"], self.num_buildings)

    def _reserve_target(self, constraints: dict[str, Any] | None) -> float:
        constraints = constraints or {}
        reserve = constraints.get("reserve_soc")
        if reserve is None:
            return 0.0
        reserve_arr = self._as_array(reserve, self.num_buildings)
        return float(np.mean(reserve_arr))

    def _extract_series(
        self,
        forecast: np.ndarray,
        carbon_intensity: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
        fc = np.asarray(forecast, dtype=np.float32)
        prices = fc[:, COL_PRICE]
        load = fc[:, COL_LOAD]
        solar = fc[:, COL_SOLAR]
        carbon = None
        if carbon_intensity is not None:
            carbon = np.asarray(carbon_intensity, dtype=np.float32)[: len(fc)]
        return prices, load, solar, carbon

    def _district_net_load(self, load: np.ndarray, solar: np.ndarray) -> np.ndarray:
        return (load - solar) * self.num_buildings

    def _transition_soc(self, soc: np.ndarray, action: float) -> np.ndarray:
        action = float(np.clip(action, -self.p_max, self.p_max))
        charge = max(action, 0.0)
        discharge = max(-action, 0.0)
        next_soc = soc + self.charge_gain * charge - self.discharge_gain * discharge
        return np.clip(next_soc, self.soc_min, self.soc_max)

    def _bounds_project(self, action: float, soc: np.ndarray, reserve_target: float) -> float:
        action = float(np.clip(action, -self.p_max, self.p_max))
        next_soc = self._transition_soc(soc, action)
        avg_next = float(np.mean(next_soc))
        if avg_next < reserve_target:
            action = max(action, 0.0)
            next_soc = self._transition_soc(soc, action)
            avg_next = float(np.mean(next_soc))
            if avg_next < reserve_target:
                gap = reserve_target - avg_next
                action = min(self.p_max, action + max(0.2, 2.0 * gap))
        if float(np.mean(soc)) >= 0.98:
            action = min(action, 0.0)
        if float(np.mean(soc)) <= float(np.mean(self.soc_min)) + 1e-3:
            action = max(action, 0.0)
        return float(np.clip(action, -self.p_max, self.p_max))


class ForecastHeuristicController(SharedBatteryControllerBase):
    """Rule-based controller using horizon statistics instead of optimization."""

    def act(
        self,
        state: dict[str, Any],
        forecast: np.ndarray,
        weights: dict[str, float],
        constraints: dict[str, Any] | None = None,
        carbon_intensity: np.ndarray | None = None,
    ) -> np.ndarray:
        soc = self._parse_soc(state)
        reserve_target = self._reserve_target(constraints)
        prices, load, solar, carbon = self._extract_series(forecast, carbon_intensity)
        net_load = self._district_net_load(load, solar)

        current_price = float(prices[0])
        future_price = float(np.mean(prices[1:])) if len(prices) > 1 else current_price
        current_net = float(net_load[0])
        future_peak = float(np.max(net_load))
        future_mean = float(np.mean(net_load))
        soc_avg = float(np.mean(soc))

        price_scale = max(float(np.std(prices)), 1e-3)
        net_scale = max(float(np.std(net_load)), 1e-3)
        carbon_scale = 1.0
        current_carbon = future_carbon = 0.0
        if carbon is not None and len(carbon) > 0:
            current_carbon = float(carbon[0])
            future_carbon = float(np.mean(carbon[1:])) if len(carbon) > 1 else current_carbon
            carbon_scale = max(float(np.std(carbon)), 1e-3)

        reserve_term = max(reserve_target + 0.05 - soc_avg, 0.0)
        charge_score = (
            weights.get("cost", 0.0) * max(future_price - current_price, 0.0) / price_scale
            + weights.get("carbon", 0.0) * max(future_carbon - current_carbon, 0.0) / carbon_scale
            + weights.get("peak", 0.0) * max(future_peak - current_net, 0.0) / net_scale
            + 1.5 * reserve_term
        )
        discharge_score = (
            weights.get("cost", 0.0) * max(current_price - future_price, 0.0) / price_scale
            + weights.get("carbon", 0.0) * max(current_carbon - future_carbon, 0.0) / carbon_scale
            + weights.get("peak", 0.0) * max(current_net - future_mean, 0.0) / net_scale
        )

        action = float(np.clip(charge_score - discharge_score, -self.p_max, self.p_max))
        if soc_avg <= reserve_target + 0.03:
            action = max(action, 0.0)
        action = self._bounds_project(action, soc, reserve_target)
        return np.array([action], dtype=np.float32)


class ActionGridController(SharedBatteryControllerBase):
    """Discrete action-grid controller with one-step proxy scoring."""

    def __init__(self, *args, action_grid: list[float] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        grid = action_grid if action_grid is not None else [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0]
        self.action_grid = np.asarray(grid, dtype=np.float32)

    def _score_action(
        self,
        action: float,
        soc: np.ndarray,
        prices: np.ndarray,
        net_load: np.ndarray,
        weights: dict[str, float],
        reserve_target: float,
        carbon: np.ndarray | None,
    ) -> float:
        next_soc = self._transition_soc(soc, action)
        avg_next_soc = float(np.mean(next_soc))
        current_net = float(net_load[0] + self.aggregate_storage_power * action)
        grid_import = max(current_net, 0.0)
        future_peak = float(np.max(net_load[1:])) if len(net_load) > 1 else current_net
        future_price = float(np.mean(prices[1:])) if len(prices) > 1 else float(prices[0])
        current_price = float(prices[0])
        future_carbon = current_carbon = 0.0
        if carbon is not None and len(carbon) > 0:
            current_carbon = float(carbon[0])
            future_carbon = float(np.mean(carbon[1:])) if len(carbon) > 1 else current_carbon

        reserve_penalty = 12.0 * max(reserve_target - avg_next_soc, 0.0)
        high_soc_penalty = 2.0 * max(avg_next_soc - 0.98, 0.0)
        future_storage_value = (
            weights.get("cost", 0.0) * max(future_price - current_price, 0.0)
            + weights.get("carbon", 0.0) * max(future_carbon - current_carbon, 0.0)
            + weights.get("peak", 0.0) * max(future_peak - current_net, 0.0)
        )

        score = (
            weights.get("cost", 0.0) * current_price * grid_import
            + weights.get("carbon", 0.0) * current_carbon * grid_import
            + weights.get("peak", 0.0) * max(current_net, future_peak)
            + weights.get("smooth", 0.0) * (action ** 2)
            + reserve_penalty
            + high_soc_penalty
            - 0.5 * max(action, 0.0) * future_storage_value
        )
        return float(score)

    def act(
        self,
        state: dict[str, Any],
        forecast: np.ndarray,
        weights: dict[str, float],
        constraints: dict[str, Any] | None = None,
        carbon_intensity: np.ndarray | None = None,
    ) -> np.ndarray:
        soc = self._parse_soc(state)
        reserve_target = self._reserve_target(constraints)
        prices, load, solar, carbon = self._extract_series(forecast, carbon_intensity)
        net_load = self._district_net_load(load, solar)

        best_action = 0.0
        best_score = float("inf")
        for raw_action in self.action_grid:
            candidate = self._bounds_project(float(raw_action), soc, reserve_target)
            score = self._score_action(candidate, soc, prices, net_load, weights, reserve_target, carbon)
            if score < best_score:
                best_score = score
                best_action = candidate

        return np.array([best_action], dtype=np.float32)
