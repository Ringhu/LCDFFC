"""Tests for CSFT utilities and label generation."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.csft import (
    build_event_window_weights,
    build_manual_horizon_weights,
    clip_and_normalize_sensitivity,
    compute_mixed_weighted_loss,
)


PROJECT_ROOT = Path(__file__).parent.parent


def test_clip_and_normalize_sensitivity_keeps_shape_and_mean():
    sensitivity = np.array(
        [
            [[1.0, 2.0], [3.0, 4.0]],
            [[2.0, 2.0], [2.0, 10.0]],
        ],
        dtype=np.float32,
    )
    normalized = clip_and_normalize_sensitivity(sensitivity, clip_quantile=0.95)
    assert normalized.shape == sensitivity.shape
    sample_means = normalized.mean(axis=(1, 2))
    assert np.allclose(sample_means, np.ones_like(sample_means), atol=1e-4)


def test_build_manual_horizon_weights_front_loads():
    weights = build_manual_horizon_weights(horizon=6, num_targets=3, front_steps=2, front_weight=5.0)
    assert weights.shape == (6, 3)
    assert np.all(weights[:2] == 5.0)
    assert np.all(weights[2:] == 1.0)


def test_build_event_window_weights_boosts_events():
    target = np.array(
        [
            [1.0, 3.0, 0.0],
            [5.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    weights = build_event_window_weights(target, price_threshold=4.0, net_load_threshold=2.0, boost=3.0)
    assert weights.shape == target.shape
    assert np.all(weights[0] == 3.0)
    assert np.all(weights[1] == 3.0)
    assert np.all(weights[2] == 1.0)


def test_compute_mixed_weighted_loss_returns_valid_stats():
    pred = torch.tensor([[[1.0], [2.0]]], dtype=torch.float32)
    target = torch.tensor([[[0.0], [0.0]]], dtype=torch.float32)
    weights = torch.tensor([[[1.0], [3.0]]], dtype=torch.float32)
    loss, stats = compute_mixed_weighted_loss(pred, target, weights, alpha=0.5, loss_type="mse")
    assert float(loss) > 0
    assert stats["weighted_loss"] > stats["base_loss"]


def test_csft_split_diagnostics_cli(tmp_path):
    output_json = tmp_path / "split_diag.json"
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "eval" / "csft_split_diagnostics.py"),
        "--data_path",
        str(PROJECT_ROOT / "artifacts" / "forecast_data.npz"),
        "--output_json",
        str(output_json),
    ]
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    result = json.loads(output_json.read_text())
    assert "splits" in result
    assert "thresholds" in result
    assert result["num_test_steps"] > 0


def test_generate_csft_labels_cli_small(tmp_path):
    output_npz = tmp_path / "labels_train_small.npz"
    output_json = tmp_path / "labels_train_small.json"
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_csft_labels.py"),
        "--data_path",
        str(PROJECT_ROOT / "artifacts" / "forecast_data.npz"),
        "--forecast_config",
        str(PROJECT_ROOT / "configs" / "forecast.yaml"),
        "--controller_config",
        str(PROJECT_ROOT / "configs" / "controller.yaml"),
        "--output_path",
        str(output_npz),
        "--metadata_path",
        str(output_json),
        "--split",
        "train",
        "--controller_type",
        "qp_carbon",
        "--max_samples",
        "2",
    ]
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    loaded = np.load(output_npz)
    sensitivity = loaded["sensitivity"]
    metadata = json.loads(output_json.read_text())
    assert sensitivity.ndim == 3
    assert sensitivity.shape[0] == 2
    assert metadata["controller_type"] == "qp_carbon"
    assert metadata["normalized_mean"] > 0
