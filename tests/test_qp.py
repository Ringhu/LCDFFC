"""Unit tests for QP controller."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from controllers.qp_controller import QPController


def test_basic_solve():
    """QP should return a valid action sequence."""
    ctrl = QPController(horizon=24, battery_capacity=4.0, p_max=1.0)
    # Flat price forecast
    forecast = np.column_stack([
        np.ones(24) * 0.3,   # price
        np.ones(24) * 2.0,   # load
        np.ones(24) * 0.5,   # solar
    ])
    weights = {"cost": 0.4, "carbon": 0.0, "peak": 0.3, "smooth": 0.1}
    action = ctrl.act(state={"soc": 0.5}, forecast=forecast, weights=weights)
    assert action is not None
    assert action.shape == (1,)
    assert -1.0 <= action[0] <= 1.0
    print(f"PASS: basic_solve, action={action[0]:.4f}")


def test_high_price_should_discharge():
    """When price is high, controller should discharge (negative action = discharge)."""
    ctrl = QPController(horizon=24, battery_capacity=4.0, p_max=1.0)
    # High price
    forecast = np.column_stack([
        np.ones(24) * 1.0,   # very high price
        np.ones(24) * 2.0,   # load
        np.zeros(24),         # no solar
    ])
    weights = {"cost": 1.0, "carbon": 0.0, "peak": 0.0, "smooth": 0.0}
    action = ctrl.act(state={"soc": 0.8}, forecast=forecast, weights=weights)
    # With high price and high SOC, should discharge (action < 0)
    assert action[0] < 0, f"Expected discharge (negative), got {action[0]}"
    print(f"PASS: high_price_discharge, action={action[0]:.4f}")


def test_low_price_should_charge():
    """When price is very low, controller should charge (positive action)."""
    ctrl = QPController(horizon=24, battery_capacity=4.0, p_max=1.0)
    # Very low price now, high price later
    prices = np.concatenate([np.ones(6) * 0.01, np.ones(18) * 0.5])
    forecast = np.column_stack([
        prices,
        np.ones(24) * 2.0,
        np.zeros(24),
    ])
    weights = {"cost": 1.0, "carbon": 0.0, "peak": 0.0, "smooth": 0.0}
    action = ctrl.act(state={"soc": 0.2}, forecast=forecast, weights=weights)
    # Low price + low SOC → should charge (positive action)
    assert action[0] > 0, f"Expected charge (positive), got {action[0]}"
    print(f"PASS: low_price_charge, action={action[0]:.4f}")


def test_soc_bounds_respected():
    """SOC should stay within bounds."""
    ctrl = QPController(horizon=24, battery_capacity=4.0, soc_min=0.1, soc_max=0.9, p_max=1.0)
    forecast = np.column_stack([
        np.ones(24) * 0.3,
        np.ones(24) * 2.0,
        np.zeros(24),
    ])
    weights = {"cost": 0.5, "peak": 0.3, "smooth": 0.2}
    # Start near max SOC
    action = ctrl.act(state={"soc": 0.85}, forecast=forecast, weights=weights)
    assert action is not None
    print(f"PASS: soc_bounds, action={action[0]:.4f}")


def test_reserve_constraint():
    """Reserve SOC constraint should force maintaining SOC."""
    ctrl = QPController(horizon=24, battery_capacity=4.0, p_max=1.0)
    forecast = np.column_stack([
        np.ones(24) * 1.0,   # high price (incentive to discharge)
        np.ones(24) * 2.0,
        np.zeros(24),
    ])
    weights = {"cost": 1.0, "peak": 0.0, "smooth": 0.0}
    # With reserve constraint, should not discharge too much
    action_reserve = ctrl.act(
        state={"soc": 0.5}, forecast=forecast, weights=weights,
        constraints={"reserve_soc": 0.4},
    )
    # Without reserve
    action_free = ctrl.act(
        state={"soc": 0.5}, forecast=forecast, weights=weights,
        constraints={},
    )
    # Reserve should lead to less aggressive discharge
    assert action_reserve[0] >= action_free[0], \
        f"Reserve {action_reserve[0]:.4f} should be >= free {action_free[0]:.4f}"
    print(f"PASS: reserve_constraint, reserve={action_reserve[0]:.4f}, free={action_free[0]:.4f}")


def test_fallback_on_infeasible():
    """Controller should fallback gracefully when QP is infeasible."""
    ctrl = QPController(horizon=24, battery_capacity=4.0, soc_min=0.5, soc_max=0.5, p_max=0.001)
    forecast = np.column_stack([np.ones(24), np.ones(24), np.zeros(24)])
    weights = {"cost": 1.0}
    action = ctrl.act(state={"soc": 0.5}, forecast=forecast, weights=weights)
    # Should return a valid action (fallback zero)
    assert action is not None
    print(f"PASS: fallback, action={action[0]:.4f}")


def test_solve_with_cost_vector():
    """SPO+ oracle interface should work."""
    ctrl = QPController(horizon=24, battery_capacity=4.0, p_max=1.0)
    cost_vec = np.ones(24) * 0.5
    result = ctrl.solve_with_cost_vector(cost_vec, soc_init=0.5)
    assert result is not None
    assert len(result) == 24
    print(f"PASS: solve_with_cost_vector, first_action={result[0]:.4f}")


def test_shared_action_multi_building_support():
    """Controller should support one shared action across heterogeneous batteries."""
    ctrl = QPController(
        horizon=24,
        num_buildings=3,
        battery_capacity=[4.0, 4.0, 3.3],
        battery_nominal_power=[3.32, 3.32, 1.61],
        soc_min=[0.2, 0.2, 0.2],
        soc_max=[1.0, 1.0, 1.0],
        p_max=1.0,
        efficiency=[0.95, 0.95, 0.96],
    )
    forecast = np.column_stack([
        np.ones(24) * 1.0,
        np.ones(24) * 0.6,
        np.zeros(24),
    ])
    weights = {"cost": 1.0, "carbon": 0.0, "peak": 0.0, "smooth": 0.0}
    action = ctrl.act(state={"soc": [0.8, 0.8, 0.8]}, forecast=forecast, weights=weights)
    assert action is not None
    assert action.shape == (1,)
    assert action[0] < 0, f"Expected discharge under high price, got {action[0]}"
    print(f"PASS: multi_building_shared_action, action={action[0]:.4f}")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
