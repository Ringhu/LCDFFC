"""QP-based MPC controller using cvxpy.

Receding horizon: plans over `horizon` steps, executes only the first action.

Forecast columns convention (matching forecast_data.npz):
    0: electricity_pricing
    1: non_shiftable_load (avg across buildings)
    2: solar_generation (avg across buildings)
"""

from typing import Any

import cvxpy as cp
import numpy as np

from controllers.safe_fallback import SafeFallback


# Forecast column indices
COL_PRICE = 0
COL_LOAD = 1
COL_SOLAR = 2


class QPController:
    """Quadratic Programming controller for battery management.

    Objective:
        min  w_cost * Σ(price * net_load) + w_carbon * Σ(carbon * net_load)
           + w_peak * peak_var + w_smooth * Σ(Δaction²)

    where net_load[t] = base_load[t] - solar[t] + action[t]
    """

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
        self.horizon = horizon
        self.num_buildings = num_buildings
        self.p_max = p_max
        self.time_step_hours = time_step_hours
        self.battery_capacity = self._as_array(battery_capacity, num_buildings)
        self.battery_nominal_power = self._as_array(
            1.0 if battery_nominal_power is None else battery_nominal_power,
            num_buildings,
        )
        self.soc_min = self._as_array(soc_min, num_buildings)
        self.soc_max = self._as_array(soc_max, num_buildings)
        self.efficiency = self._as_array(efficiency, num_buildings)
        self.fallback = SafeFallback()

    @staticmethod
    def _as_array(
        value: float | list[float] | np.ndarray,
        length: int,
    ) -> np.ndarray:
        """Convert scalar or sequence inputs to a fixed-length float array."""
        arr = np.asarray(value, dtype=np.float32)

        if arr.ndim == 0:
            return np.full(length, float(arr), dtype=np.float32)

        arr = arr.reshape(-1)
        if len(arr) != length:
            raise ValueError(f"Expected {length} values, got {len(arr)}")

        return arr.astype(np.float32)

    def _prepare_forecast(
        self,
        forecast: np.ndarray,
        carbon_intensity: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray | None]:
        """Clip/pad forecast inputs to controller horizon."""
        H = min(self.horizon, len(forecast))
        fc = forecast[:H]
        if fc.ndim == 1:
            fc = fc.reshape(-1, 1)

        if H < self.horizon:
            pad = np.tile(fc[-1:], (self.horizon - H, 1))
            fc = np.concatenate([fc, pad], axis=0)
            H = self.horizon

        carbon = carbon_intensity[:H] if carbon_intensity is not None else None
        if carbon is not None and len(carbon) < H:
            pad = np.repeat(carbon[-1:], H - len(carbon), axis=0)
            carbon = np.concatenate([carbon, pad], axis=0)
        return fc, carbon

    def act(
        self,
        state: dict[str, Any],
        forecast: np.ndarray,
        weights: dict[str, float],
        constraints: dict[str, Any] | None = None,
        carbon_intensity: np.ndarray | None = None,
    ) -> np.ndarray:
        """Solve QP and return the first action."""
        constraints = constraints or {}
        soc = self._as_array(state["soc"], self.num_buildings)
        fc, carbon = self._prepare_forecast(forecast, carbon_intensity)

        result = self._build_and_solve(soc, fc, weights, constraints, carbon)
        if result is not None:
            return np.array([np.clip(result[0], -self.p_max, self.p_max)])
        return self.fallback.act(state)

    def solve_with_diagnostics(
        self,
        state: dict[str, Any],
        forecast: np.ndarray,
        weights: dict[str, float],
        constraints: dict[str, Any] | None = None,
        carbon_intensity: np.ndarray | None = None,
    ) -> dict[str, np.ndarray] | None:
        """Solve the QP and return action sequence plus diagnostics.

        This is intended for analysis / supervision extraction only. Unlike
        ``act()``, it does not apply the fallback policy when the QP fails.
        """
        constraints = constraints or {}
        soc = self._as_array(state["soc"], self.num_buildings)
        fc, carbon = self._prepare_forecast(forecast, carbon_intensity)

        result = self._build_and_solve(
            soc,
            fc,
            weights,
            constraints,
            carbon,
            collect_diagnostics=True,
        )
        if result is None:
            return None
        action_values, diagnostics = result
        diagnostics["action"] = np.asarray(action_values, dtype=np.float32)
        return diagnostics

    def _build_and_solve(
        self,
        soc_init: np.ndarray,
        forecast: np.ndarray,
        weights: dict[str, float],
        constraints: dict[str, Any] | None = None,
        carbon_intensity: np.ndarray | None = None,
        collect_diagnostics: bool = False,
    ) -> np.ndarray | tuple[np.ndarray, dict[str, np.ndarray]] | None:
        """Build and solve the QP problem."""
        constraints = constraints or {}
        H = self.horizon
        charge = cp.Variable(H, nonneg=True)
        discharge = cp.Variable(H, nonneg=True)
        action = charge - discharge
        soc = cp.Variable((self.num_buildings, H + 1))

        prices = forecast[:H, COL_PRICE] if forecast.shape[1] > COL_PRICE else np.ones(H)
        base_load_avg = forecast[:H, COL_LOAD] if forecast.shape[1] > COL_LOAD else np.zeros(H)
        solar_avg = forecast[:H, COL_SOLAR] if forecast.shape[1] > COL_SOLAR else np.zeros(H)
        aggregate_base_load = base_load_avg * self.num_buildings
        aggregate_solar = solar_avg * self.num_buildings
        aggregate_storage_power = float(np.sum(self.battery_nominal_power) * self.time_step_hours)

        net_load = aggregate_base_load - aggregate_solar + aggregate_storage_power * action
        grid_import = cp.Variable(H, nonneg=True)

        objective_terms = []
        w_cost = weights.get("cost", 0.0)
        if w_cost > 0:
            objective_terms.append(w_cost * (prices @ grid_import))

        carbon = None
        w_carbon = weights.get("carbon", 0.0)
        if w_carbon > 0 and carbon_intensity is not None:
            carbon = carbon_intensity[:H]
            objective_terms.append(w_carbon * (carbon @ grid_import))

        w_peak = weights.get("peak", 0.0)
        peak_var = None
        if w_peak > 0:
            peak_var = cp.Variable()
            objective_terms.append(w_peak * peak_var)

        w_smooth = weights.get("smooth", 0.0)
        if w_smooth > 0:
            objective_terms.append(w_smooth * cp.sum_squares(action[1:] - action[:-1]))

        objective_terms.append(1e-6 * (cp.sum_squares(charge) + cp.sum_squares(discharge)))
        if not objective_terms:
            objective_terms.append(0)
        objective = cp.Minimize(sum(objective_terms))

        charge_gain = (
            self.efficiency * self.battery_nominal_power * self.time_step_hours
        ) / self.battery_capacity
        discharge_gain = (
            self.battery_nominal_power * self.time_step_hours
        ) / (self.efficiency * self.battery_capacity)

        soc_init_constraint = soc[:, 0] == soc_init
        dynamics_constraint = (
            soc[:, 1:] == soc[:, :-1]
            + cp.multiply(charge_gain[:, None], cp.reshape(charge, (1, H), order="C"))
            - cp.multiply(discharge_gain[:, None], cp.reshape(discharge, (1, H), order="C"))
        )
        soc_min_constraint = soc >= self.soc_min[:, None]
        soc_max_constraint = soc <= self.soc_max[:, None]
        charge_cap_constraint = charge <= self.p_max
        discharge_cap_constraint = discharge <= self.p_max
        import_constraint = grid_import >= net_load

        constraints_list = [
            soc_init_constraint,
            dynamics_constraint,
            soc_min_constraint,
            soc_max_constraint,
            charge_cap_constraint,
            discharge_cap_constraint,
            import_constraint,
        ]

        peak_constraint = None
        if peak_var is not None:
            peak_constraint = grid_import <= peak_var
            constraints_list.append(peak_constraint)

        reserve_constraint = None
        reserve_soc = constraints.get("reserve_soc")
        if reserve_soc is not None:
            reserve = self._as_array(reserve_soc, self.num_buildings)
            reserve_constraint = soc[:, H] >= reserve
            constraints_list.append(reserve_constraint)

        max_charge_constraint = None
        max_charge = constraints.get("max_charge_rate")
        if max_charge is not None:
            max_charge_constraint = charge <= max_charge
            constraints_list.append(max_charge_constraint)

        prob = cp.Problem(objective, constraints_list)
        solved = False
        for solver, kwargs in (
            (cp.CLARABEL, {}),
            (cp.OSQP, {"warm_start": True, "max_iter": 4000, "eps_abs": 1e-3, "eps_rel": 1e-3}),
        ):
            try:
                prob.solve(solver=solver, **kwargs)
            except cp.SolverError:
                continue
            if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
                solved = True
                break

        if not solved:
            return None

        action_value = np.asarray(action.value, dtype=np.float32)
        if not collect_diagnostics:
            return action_value

        diagnostics = {
            "prices": np.asarray(prices, dtype=np.float32),
            "base_load": np.asarray(aggregate_base_load, dtype=np.float32),
            "solar": np.asarray(aggregate_solar, dtype=np.float32),
            "net_load": np.asarray(net_load.value, dtype=np.float32),
            "grid_import": np.asarray(grid_import.value, dtype=np.float32),
            "soc": np.asarray(soc.value, dtype=np.float32),
            "import_dual": np.asarray(import_constraint.dual_value, dtype=np.float32),
        }
        if carbon is not None:
            diagnostics["carbon_intensity"] = np.asarray(carbon, dtype=np.float32)
        if peak_var is not None:
            diagnostics["peak_var"] = np.asarray([peak_var.value], dtype=np.float32)
            diagnostics["peak_dual"] = np.asarray(peak_constraint.dual_value, dtype=np.float32)
        if reserve_constraint is not None:
            diagnostics["reserve_dual"] = np.asarray(reserve_constraint.dual_value, dtype=np.float32)
        if max_charge_constraint is not None:
            diagnostics["max_charge_dual"] = np.asarray(max_charge_constraint.dual_value, dtype=np.float32)
        return action_value, diagnostics

    def solve_with_cost_vector(
        self,
        cost_vector: np.ndarray,
        soc_init: float,
        base_load: np.ndarray | None = None,
        solar: np.ndarray | None = None,
    ) -> np.ndarray | None:
        """Solve QP with an explicit cost vector (for SPO+ oracle)."""
        H = self.horizon
        actions = cp.Variable(H)
        soc = cp.Variable(H + 1)

        objective = cp.Minimize(cost_vector @ actions)
        constraints_list = [
            soc[0] == soc_init,
            soc[1:] == soc[:-1] + self.efficiency * actions / self.battery_capacity,
            soc >= self.soc_min,
            soc <= self.soc_max,
            actions >= -self.p_max,
            actions <= self.p_max,
        ]

        prob = cp.Problem(objective, constraints_list)
        try:
            prob.solve(solver=cp.OSQP, warm_start=True, max_iter=4000)
        except cp.SolverError:
            return None

        if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            return actions.value
        return None
