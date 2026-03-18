"""Smoke tests: verify all modules can be imported and basic interfaces exist."""

import importlib
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_data():
    mod = importlib.import_module("data")
    assert hasattr(mod, "CityLearnDataset")


def test_import_models():
    mod = importlib.import_module("models")
    assert hasattr(mod, "BaseForecaster")
    assert hasattr(mod, "GRUForecaster")


def test_import_controllers():
    mod = importlib.import_module("controllers")
    # QPController requires cvxpy; test SafeFallback which has no heavy deps
    from controllers.safe_fallback import SafeFallback
    assert SafeFallback is not None
    try:
        assert hasattr(mod, "QPController")
    except ImportError:
        pass  # cvxpy not installed; OK for smoke test


def test_import_llm_router():
    mod = importlib.import_module("llm_router")
    assert hasattr(mod, "LLMRouter")


def test_dataset_basic():
    import numpy as np
    from data.dataset import CityLearnDataset

    data = np.random.randn(100, 5)
    ds = CityLearnDataset(data, history_len=10, horizon=5)
    assert len(ds) == 86  # 100 - 10 - 5 + 1
    hist, fut = ds[0]
    assert hist.shape == (10, 5)
    assert fut.shape == (5, 5)


def test_gru_forward():
    import torch
    from models.gru_forecaster import GRUForecaster

    model = GRUForecaster(input_dim=5, hidden_dim=32, num_layers=1, output_dim=3, horizon=12)
    x = torch.randn(4, 10, 5)
    y = model(x)
    assert y.shape == (4, 12, 3)


def test_safe_fallback():
    from controllers.safe_fallback import SafeFallback

    fb = SafeFallback()
    action = fb.act({"soc": [0.5, 0.6]})
    assert action.shape == (2,)
    assert (action == 0).all()


def test_json_schema_validation():
    from llm_router.json_schema import validate_router_output

    valid = {"weights": {"cost": 0.4, "carbon": 0.2, "peak": 0.3, "smooth": 0.1}}
    result = validate_router_output(valid)
    assert abs(sum(result["weights"].values()) - 1.0) < 1e-6


def test_configs_exist():
    config_dir = Path(__file__).parent.parent / "configs"
    expected = ["data.yaml", "forecast.yaml", "controller.yaml", "eval.yaml", "llm_router.yaml"]
    for name in expected:
        assert (config_dir / name).exists(), f"Missing config: {name}"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
