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

    Args:
        horizon: Planning horizon (number of steps).
        num_buildings: Number of buildings (for central_agent mode).
        battery_capacity: Battery capacity in kWh.
        soc_min: Minimum SOC fraction.
        soc_max: Maximum SOC fraction.
        p_max: Maximum charge/discharge rate (normalized).
        efficiency: Battery round-trip efficiency.
    """

    def __init__(
        self,
        horizon: int = 24,
        num_buildings: int = 1,
        battery_capacity: float = 4.0,
        soc_min: float = 0.0,
        soc_max: float = 1.0,
        p_max: float = 1.0,
        efficiency: float = 0.95,
    ):
        self.horizon = horizon
        self.num_buildings = num_buildings
        self.battery_capacity = battery_capacity
        self.soc_min = soc_min
        self.soc_max = soc_max
        self.p_max = p_max
        self.efficiency = efficiency
        self.fallback = SafeFallback()

    def act(
        self,
        state: dict[str, Any],
        forecast: np.ndarray,
        weights: dict[str, float],
        constraints: dict[str, Any] | None = None,
        carbon_intensity: np.ndarray | None = None,
    ) -> np.ndarray:
        """Solve QP and return the first action.

        Args:
            state: Must include "soc" — current SOC as float or list of floats.
            forecast: Shape (horizon, 3) with [price, load, solar] columns.
            weights: {"cost", "carbon", "peak", "smooth"} floats.
            constraints: Optional {"reserve_soc": float, "max_charge_rate": float}.
            carbon_intensity: Optional (horizon,) carbon intensity array.

        Returns:
            Action value(s) for the current timestep.
        """
        constraints = constraints or {}
        soc = state["soc"]
        if isinstance(soc, (list, np.ndarray)):
            soc = float(soc[0]) if len(soc) > 0 else 0.5

        # Clip forecast to horizon
        H = min(self.horizon, len(forecast))
        fc = forecast[:H]
        if fc.ndim == 1:
            fc = fc.reshape(-1, 1)

        # Pad if forecast is shorter than horizon
        if H < self.horizon:
            pad = np.tile(fc[-1:], (self.horizon - H, 1))
            fc = np.concatenate([fc, pad], axis=0)
            H = self.horizon

        carbon = carbon_intensity[:H] if carbon_intensity is not None else None

        result = self._build_and_solve(soc, fc, weights, constraints, carbon)

        if result is not None:
            return np.array([np.clip(result[0], -self.p_max, self.p_max)])
        else:
            return self.fallback.act(state)

    def _build_and_solve(
        self,
        soc_init: float,
        forecast: np.ndarray,
        weights: dict[str, float],
        constraints: dict[str, Any] | None = None,
        carbon_intensity: np.ndarray | None = None,
    ) -> np.ndarray | None:
        """Build and solve the QP problem.

        Args:
            soc_init: Current SOC fraction.
            forecast: (horizon, num_cols) — at minimum [price, load, solar].
            weights: Objective term weights.
            constraints: Additional constraints.
            carbon_intensity: Optional (horizon,) array.

        Returns:
            Optimal action sequence of shape (horizon,), or None if infeasible.
        """
        constraints = constraints or {}
        H = self.horizon
        actions = cp.Variable(H)
        soc = cp.Variable(H + 1)

        # Extract forecast components
        prices = forecast[:H, COL_PRICE] if forecast.shape[1] > COL_PRICE else np.ones(H)
        base_load = forecast[:H, COL_LOAD] if forecast.shape[1] > COL_LOAD else np.zeros(H)
        solar = forecast[:H, COL_SOLAR] if forecast.shape[1] > COL_SOLAR else np.zeros(H)

        # Net load = base_load - solar + battery_action (positive = charge = draw from grid)
        net_load = base_load - solar + actions

        # === Objective terms ===
        objective_terms = []

        # 1) Electricity cost: Σ price[t] * net_load[t]
        w_cost = weights.get("cost", 0)
        if w_cost > 0:
            objective_terms.append(w_cost * (prices @ net_load))

        # 2) Carbon emissions: Σ carbon[t] * net_load[t]
        w_carbon = weights.get("carbon", 0)
        if w_carbon > 0 and carbon_intensity is not None:
            carbon = carbon_intensity[:H]
            objective_terms.append(w_carbon * (carbon @ net_load))

        # 3) Peak demand: epigraph formulation — min peak_var s.t. net_load[t] <= peak_var
        w_peak = weights.get("peak", 0)
        if w_peak > 0:
            peak_var = cp.Variable()
            objective_terms.append(w_peak * peak_var)
        else:
            peak_var = None

        # 4) Action smoothness: Σ (action[t] - action[t-1])²
        w_smooth = weights.get("smooth", 0)
        if w_smooth > 0:
            objective_terms.append(w_smooth * cp.sum_squares(actions[1:] - actions[:-1]))

        if not objective_terms:
            objective_terms.append(0)

        objective = cp.Minimize(sum(objective_terms))

        # === Constraints ===
        # Battery SOC dynamics (simplified single efficiency)
        eff = self.efficiency
        cap = self.battery_capacity
        constraints_list = [
            soc[0] == soc_init,
            soc[1:] == soc[:-1] + eff * actions / cap,
            soc >= self.soc_min,
            soc <= self.soc_max,
            actions >= -self.p_max,
            actions <= self.p_max,
        ]

        # Peak epigraph constraint
        if peak_var is not None:
            constraints_list.append(net_load <= peak_var)

        # Reserve SOC constraint
        reserve_soc = constraints.get("reserve_soc")
        if reserve_soc is not None:
            constraints_list.append(soc[H] >= reserve_soc)

        # Custom max charge rate
        max_charge = constraints.get("max_charge_rate")
        if max_charge is not None:
            constraints_list.append(actions <= max_charge)

        # === Solve ===
        prob = cp.Problem(objective, constraints_list)
        try:
            prob.solve(solver=cp.OSQP, warm_start=True, max_iter=4000,
                       eps_abs=1e-3, eps_rel=1e-3)
        except cp.SolverError:
            return None

        if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            return actions.value
        return None

    def solve_with_cost_vector(
        self,
        cost_vector: np.ndarray,
        soc_init: float,
        base_load: np.ndarray | None = None,
        solar: np.ndarray | None = None,
    ) -> np.ndarray | None:
        """Solve QP with an explicit cost vector (for SPO+ oracle).

        Args:
            cost_vector: (horizon,) cost coefficients for the actions.
            soc_init: Current SOC.
            base_load: (horizon,) base load (optional, for net_load computation).
            solar: (horizon,) solar generation (optional).

        Returns:
            Optimal action sequence (horizon,), or None if infeasible.
        """
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
