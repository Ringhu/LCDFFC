from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

from data.dataset import CityLearnDataset
from eval.run_controller import build_oracle_forecast, load_oracle_targets
from models.factory import build_forecaster

TARGET_COLS = [4, 5, 6]
TARGET_NAMES = ["price", "load", "solar"]


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_model(checkpoint: str, config: dict, device: str):
    dataset = CityLearnDataset.from_file(
        "artifacts/forecast_data.npz",
        split="train",
        history_len=config["model"].get("history_len", 24),
        horizon=config["model"]["horizon"],
        target_cols=TARGET_COLS,
        return_index=False,
    )
    model = build_forecaster(
        config["model"],
        input_dim=dataset.num_features,
        output_dim=dataset.num_targets,
    ).to(device)
    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
    model.eval()
    return model, dataset.mean, dataset.std


def collect_predictions(checkpoint: str, config_path: str, split: str, device: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    config = load_config(config_path)
    model, mean, std = load_model(checkpoint, config, device)
    ds = CityLearnDataset.from_file(
        "artifacts/forecast_data.npz",
        split=split,
        history_len=config["model"].get("history_len", 24),
        horizon=config["model"]["horizon"],
        target_cols=TARGET_COLS,
        return_index=True,
    )
    preds, targets, indices = [], [], []
    for i in range(len(ds)):
        history, target, idx = ds[i]
        with torch.no_grad():
            pred = model(history.unsqueeze(0).to(device)).cpu().numpy()[0]
        preds.append(pred)
        targets.append(target.numpy())
        indices.append(idx)
    return np.asarray(preds, dtype=np.float32), np.asarray(targets, dtype=np.float32), np.asarray(indices, dtype=np.int64)


def run_r201(oracle_data: str, horizon: int, output_path: Path) -> dict:
    oracle_targets = load_oracle_targets(oracle_data)
    max_abs_error = {name: 0.0 for name in TARGET_NAMES}
    for step in range(20):
        sliced = build_oracle_forecast(oracle_targets, step, horizon)
        env_future = oracle_targets[step + 1 : step + 1 + horizon]
        if len(env_future) < horizon:
            pad = np.repeat(env_future[-1:], horizon - len(env_future), axis=0)
            env_future = np.concatenate([env_future, pad], axis=0)
        diff = np.abs(sliced - env_future)
        for j, name in enumerate(TARGET_NAMES):
            max_abs_error[name] = max(max_abs_error[name], float(np.max(diff[:, j])))
    passed = all(v <= 1e-6 for v in max_abs_error.values())
    result = {
        "check": "R201_oracle_alignment",
        "max_abs_error": max_abs_error,
        "threshold": 1e-6,
        "pass": bool(passed),
    }
    output_path.write_text(json.dumps(result, indent=2))
    return result


def run_r202(
    uniform_ckpt: str,
    csft_ckpt: str,
    config_path: str,
    labels_path: str,
    device: str,
    output_path: Path,
) -> dict:
    labels = np.load(labels_path)
    sensitivity = labels["sensitivity"].astype(np.float32)
    preds_u, targets_u, indices_u = collect_predictions(uniform_ckpt, config_path, "test", device)
    preds_c, targets_c, indices_c = collect_predictions(csft_ckpt, config_path, "test", device)
    if not np.array_equal(indices_u, indices_c):
        raise ValueError("Uniform and CSFT sample indices do not align")
    if not np.allclose(targets_u, targets_c):
        raise ValueError("Uniform and CSFT targets do not align")

    flat_sens = sensitivity.reshape(-1)
    flat_u = np.abs(preds_u - targets_u).reshape(-1)
    flat_c = np.abs(preds_c - targets_c).reshape(-1)
    order = np.argsort(flat_sens, kind="stable")
    n = len(flat_sens)
    decile_size = max(1, n // 10)
    deciles = []
    for d in range(10):
        start = d * decile_size
        end = (d + 1) * decile_size if d < 9 else n
        idx = order[start:end]
        if idx.size == 0:
            deciles.append({"decile": d + 1, "uniform_mae": None, "csft_mae": None, "sens_min": None, "sens_max": None})
            continue
        deciles.append({
            "decile": d + 1,
            "uniform_mae": float(flat_u[idx].mean()),
            "csft_mae": float(flat_c[idx].mean()),
            "sens_min": float(flat_sens[idx].min()),
            "sens_max": float(flat_sens[idx].max()),
        })

    top_idx = order[int(0.9 * n):]
    top_mae_u = float(flat_u[top_idx].mean())
    top_mae_c = float(flat_c[top_idx].mean())
    ratio = top_mae_c / top_mae_u if top_mae_u > 0 else float("inf")

    passed = ratio <= 1.05
    result = {
        "check": "R202_raw_label_utility",
        "num_cells": int(n),
        "top_decile_num_cells": int(len(top_idx)),
        "uniform_top_decile_mae": top_mae_u,
        "raw_csft_top_decile_mae": top_mae_c,
        "ratio": ratio,
        "threshold": 1.05,
        "pass": bool(passed),
        "deciles": deciles,
    }
    output_path.write_text(json.dumps(result, indent=2))
    return result


def build_stabilized_labels(input_path: str, output_path: str) -> dict:
    loaded = np.load(input_path)
    if "raw_sensitivity" not in loaded:
        raise ValueError(f"Missing raw_sensitivity in {input_path}. Regenerate labels first.")
    raw = loaded["raw_sensitivity"].astype(np.float32)
    future_start_indices = loaded["future_start_indices"].astype(np.int64)

    positive = raw[raw > 0]
    if positive.size == 0:
        raise ValueError("All raw sensitivities are non-positive")
    q95_train = float(np.quantile(positive, 0.95))
    clipped_all = np.clip(raw, 0.0, q95_train)
    positive_clipped = clipped_all[clipped_all > 0]
    m_train = float(np.median(positive_clipped))
    eps = 1e-8
    u = np.log1p(clipped_all / (m_train + eps)).astype(np.float32)
    denom = np.mean(u, axis=(1, 2), keepdims=True) + eps
    weights = (u / denom).astype(np.float32)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out, raw_sensitivity=raw, sensitivity=weights, future_start_indices=future_start_indices)
    metadata = {
        "q95_train": q95_train,
        "m_train": m_train,
        "eps": eps,
        "transform": "log1p",
        "normalization": "per-sample-mean",
    }
    out.with_suffix(".json").write_text(json.dumps(metadata, indent=2))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Run R201/R202 preflight and build stabilized labels")
    parser.add_argument("--mode", choices=["r201", "r202", "stabilize"], required=True)
    parser.add_argument("--oracle_data", default="artifacts/forecast_data.npz")
    parser.add_argument("--forecast_config", default="configs/forecast.yaml")
    parser.add_argument("--uniform_ckpt", default="artifacts/checkpoints/gru_uniform_best_r103_uniform_seed42.pt")
    parser.add_argument("--csft_ckpt", default="artifacts/checkpoints/gru_csft_best_r105_csft_seed42.pt")
    parser.add_argument("--labels_path", default="artifacts/csft_labels_qp_carbon_test.npz")
    parser.add_argument("--input_labels", default="artifacts/csft_labels_qp_carbon_train.npz")
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    config = load_config(args.forecast_config)
    horizon = int(config["model"]["horizon"])

    if args.mode == "r201":
        result = run_r201(args.oracle_data, horizon, Path(args.output_path))
    elif args.mode == "r202":
        result = run_r202(
            args.uniform_ckpt,
            args.csft_ckpt,
            args.forecast_config,
            args.labels_path,
            args.device,
            Path(args.output_path),
        )
    else:
        result = build_stabilized_labels(args.input_labels, args.output_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
