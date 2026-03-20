"""Tests for configurable forecaster backbones."""

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.factory import build_forecaster


def _assert_forward(cfg: dict):
    model = build_forecaster(cfg, input_dim=9, output_dim=3)
    x = torch.randn(4, 24, 9)
    y = model(x)
    assert y.shape == (4, 24, 3)


def test_build_gru_forecaster():
    cfg = {
        "type": "gru",
        "hidden_dim": 32,
        "num_layers": 2,
        "output_dim": 3,
        "horizon": 24,
        "dropout": 0.1,
    }
    _assert_forward(cfg)


def test_build_tsmixer_forecaster():
    cfg = {
        "type": "tsmixer",
        "history_len": 24,
        "model_dim": 32,
        "num_layers": 2,
        "ff_dim": 64,
        "output_dim": 3,
        "horizon": 24,
        "dropout": 0.1,
    }
    _assert_forward(cfg)


def test_build_patchtst_forecaster():
    cfg = {
        "type": "patchtst",
        "history_len": 24,
        "patch_length": 4,
        "patch_stride": 4,
        "d_model": 32,
        "num_layers": 2,
        "num_heads": 4,
        "ff_dim": 64,
        "output_dim": 3,
        "horizon": 24,
        "dropout": 0.1,
    }
    _assert_forward(cfg)


if __name__ == "__main__":
    test_build_gru_forecaster()
    print('PASS: test_build_gru_forecaster')
    test_build_tsmixer_forecaster()
    print('PASS: test_build_tsmixer_forecaster')
    test_build_patchtst_forecaster()
    print('PASS: test_build_patchtst_forecaster')
