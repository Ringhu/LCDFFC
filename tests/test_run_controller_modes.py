"""Tests for forecast diagnostic modes in eval/run_controller.py."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.run_controller import (
    TARGET_COLS,
    build_myopic_forecast,
    build_oracle_forecast,
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


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
