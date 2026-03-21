"""Evaluate official zero-shot time-series foundation models on CityLearn targets."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from eval.foundation_model_adapters import build_adapter

TARGET_SPECS = [
    (4, "electricity_pricing"),
    (5, "non_shiftable_load_avg"),
    (6, "solar_generation_avg"),
]


def evaluate_model(adapter, data: np.ndarray, test_start: int) -> dict:
    horizon = adapter.horizon
    model_start = time.perf_counter()
    squared_errors = {name: [] for _, name in TARGET_SPECS}
    abs_errors = {name: [] for _, name in TARGET_SPECS}
    per_call_times = []

    max_t = len(data) - horizon
    for t in range(test_start, max_t):
        for col, name in TARGET_SPECS:
            history = data[:t, col]
            tic = time.perf_counter()
            pred = adapter.forecast_univariate(history)
            per_call_times.append(time.perf_counter() - tic)
            truth = data[t : t + horizon, col].astype(np.float32)
            squared_errors[name].append((pred - truth) ** 2)
            abs_errors[name].append(np.abs(pred - truth))

    metrics = {}
    all_sq = []
    all_abs = []
    for name in squared_errors:
        sq = np.concatenate([arr.reshape(-1) for arr in squared_errors[name]])
        ab = np.concatenate([arr.reshape(-1) for arr in abs_errors[name]])
        metrics[name] = {"mse": float(np.mean(sq)), "mae": float(np.mean(ab))}
        all_sq.append(sq)
        all_abs.append(ab)

    all_sq = np.concatenate(all_sq)
    all_abs = np.concatenate(all_abs)
    metrics["overall_mse"] = float(np.mean(all_sq))
    metrics["overall_mae"] = float(np.mean(all_abs))
    metrics["num_eval_windows"] = int(max_t - test_start)
    metrics["num_calls"] = int(len(per_call_times))
    metrics["avg_call_sec"] = float(np.mean(per_call_times)) if per_call_times else 0.0
    metrics["total_runtime_sec"] = float(time.perf_counter() - model_start)
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate official zero-shot foundation models")
    parser.add_argument("--data_path", type=str, default="artifacts/forecast_data.npz")
    parser.add_argument("--models", nargs="+", default=["chronos2", "moirai2", "timesfm2.5", "moment"])
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--context_length", type=int, default=512)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--output", type=str, default="reports/foundation_zero_shot_summary.json")
    args = parser.parse_args()

    loaded = np.load(args.data_path, allow_pickle=True)
    data = loaded["data"].astype(np.float32)
    test_start = int(len(data) * 0.85)
    device = args.device if (args.device.startswith("cuda") and torch.cuda.is_available()) else "cpu"

    summary = {
        "data_path": args.data_path,
        "test_start": int(test_start),
        "horizon": int(args.horizon),
        "context_length": int(args.context_length),
        "device": device,
        "models": {},
    }

    for name in args.models:
        print(f"\n=== Evaluating {name} ===")
        adapter = build_adapter(name, device=device, horizon=args.horizon, context_length=args.context_length)
        metrics = evaluate_model(adapter, data, test_start=test_start)
        summary["models"][name] = metrics
        print(json.dumps(metrics, indent=2))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2))
    print(f"\nSaved summary to {output}")


if __name__ == "__main__":
    main()
