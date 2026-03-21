"""Unit tests for non-QP controller baselines."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from controllers.baseline_controllers import ActionGridController, ForecastHeuristicController


def test_heuristic_discharges_when_current_conditions_are_bad():
    ctrl = ForecastHeuristicController(horizon=24, battery_capacity=4.0, p_max=1.0)
    prices = np.concatenate([np.ones(6) * 1.0, np.ones(18) * 0.2])
    load = np.ones(24) * 2.2
    solar = np.zeros(24)
    carbon = np.concatenate([np.ones(6) * 0.8, np.ones(18) * 0.2])
    forecast = np.column_stack([prices, load, solar])
    action = ctrl.act(
        state={"soc": 0.85},
        forecast=forecast,
        weights={"cost": 0.5, "carbon": 0.2, "peak": 0.3, "smooth": 0.0},
        constraints={"reserve_soc": 0.2},
        carbon_intensity=carbon,
    )
    assert action.shape == (1,)
    assert action[0] < 0, f"Expected discharge action, got {action[0]}"


def test_heuristic_charges_when_future_risk_is_higher():
    ctrl = ForecastHeuristicController(horizon=24, battery_capacity=4.0, p_max=1.0)
    prices = np.concatenate([np.ones(6) * 0.05, np.ones(18) * 0.9])
    load = np.concatenate([np.ones(12) * 0.5, np.ones(12) * 2.5])
    solar = np.zeros(24)
    carbon = np.concatenate([np.ones(6) * 0.1, np.ones(18) * 0.9])
    forecast = np.column_stack([prices, load, solar])
    action = ctrl.act(
        state={"soc": 0.25},
        forecast=forecast,
        weights={"cost": 0.4, "carbon": 0.2, "peak": 0.4, "smooth": 0.0},
        constraints={"reserve_soc": 0.2},
        carbon_intensity=carbon,
    )
    assert action[0] > 0, f"Expected charge action, got {action[0]}"


def test_action_grid_respects_reserve_constraint():
    ctrl = ActionGridController(horizon=24, battery_capacity=4.0, p_max=1.0)
    prices = np.ones(24) * 1.0
    load = np.ones(24) * 2.0
    solar = np.zeros(24)
    carbon = np.ones(24) * 0.5
    forecast = np.column_stack([prices, load, solar])
    action = ctrl.act(
        state={"soc": 0.2},
        forecast=forecast,
        weights={"cost": 0.6, "carbon": 0.1, "peak": 0.3, "smooth": 0.0},
        constraints={"reserve_soc": 0.25},
        carbon_intensity=carbon,
    )
    assert action[0] >= 0.0, f"Reserve-constrained action should not discharge, got {action[0]}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            raise
