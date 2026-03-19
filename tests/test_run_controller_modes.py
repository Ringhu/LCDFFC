"""Tests for forecast diagnostic modes in eval/run_controller.py."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.run_controller import (
    TARGET_COLS,
    build_myopic_forecast,
    build_oracle_forecast,
    get_battery_params,
    get_current_socs,
    load_oracle_targets,
)


def test_build_myopic_forecast():
    current = np.arange(9, dtype=np.float32)
    forecast = build_myopic_forecast(current, horizon=4)
    expected = np.repeat(current[TARGET_COLS][None, :], 4, axis=0)
    assert forecast.shape == (4, 3)
    assert np.allclose(forecast, expected)
    print("PASS: myopic_forecast")


def test_build_oracle_forecast_basic():
    oracle = np.arange(30, dtype=np.float32).reshape(10, 3)
    forecast = build_oracle_forecast(oracle, current_step=2, horizon=4)
    expected = oracle[3:7]
    assert forecast.shape == (4, 3)
    assert np.allclose(forecast, expected)
    print("PASS: oracle_forecast_basic")


def test_build_oracle_forecast_padding():
    oracle = np.arange(18, dtype=np.float32).reshape(6, 3)
    forecast = build_oracle_forecast(oracle, current_step=4, horizon=4)
    expected = np.vstack([oracle[5], oracle[5], oracle[5], oracle[5]])
    assert forecast.shape == (4, 3)
    assert np.allclose(forecast, expected)
    print("PASS: oracle_forecast_padding")


def test_load_oracle_targets():
    oracle = load_oracle_targets("artifacts/forecast_data.npz")
    assert oracle.ndim == 2
    assert oracle.shape[1] == 3
    print("PASS: load_oracle_targets")


def test_get_battery_params_uses_per_building_metadata():
    class Battery:
        def __init__(self, capacity, nominal_power, efficiency, depth_of_discharge):
            self.capacity = capacity
            self.nominal_power = nominal_power
            self.efficiency = efficiency
            self.depth_of_discharge = depth_of_discharge

    class Building:
        def __init__(self, battery):
            self.electrical_storage = battery

    class Env:
        def __init__(self):
            self.buildings = [
                Building(Battery(4.0, 3.32, 0.95, 0.8)),
                Building(Battery(3.3, 1.61, 0.96, 0.8)),
            ]

    params = get_battery_params(Env())
    assert np.allclose(params["capacity"], [4.0, 3.3])
    assert np.allclose(params["nominal_power"], [3.32, 1.61])
    assert np.allclose(params["efficiency"], [0.95, 0.96])
    assert np.allclose(params["soc_min"], [0.2, 0.2])
    assert np.allclose(params["soc_max"], [1.0, 1.0])
    print("PASS: battery_params_from_env")


def test_get_current_socs_reads_current_timestep():
    class Battery:
        def __init__(self, soc):
            self.soc = np.array(soc, dtype=np.float32)

    class Building:
        def __init__(self, battery):
            self.electrical_storage = battery

    class Env:
        def __init__(self):
            self.time_step = 2
            self.buildings = [
                Building(Battery([0.2, 0.4, 0.0])),
                Building(Battery([0.2, 0.6, 0.0])),
            ]

    socs = get_current_socs(Env())
    assert np.allclose(socs, [0.4, 0.6])
    print("PASS: current_soc_indexing")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
