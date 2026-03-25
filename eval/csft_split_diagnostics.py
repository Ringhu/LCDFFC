"""Compute chronological split masks and stress subset diagnostics for CSFT experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

TARGET_COLS = [4, 5, 6]
CARBON_COL = 3


def build_split_indices(T: int, train_ratio: float = 0.7, val_ratio: float = 0.15) -> dict[str, list[int]]:
    train_end = int(T * train_ratio)
    val_end = int(T * (train_ratio + val_ratio))
    return {
        "train": [0, train_end],
        "val": [train_end, val_end],
        "test": [val_end, T],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CSFT split and stress diagnostics")
    parser.add_argument("--data_path", type=str, default="artifacts/forecast_data.npz")
    parser.add_argument("--output_json", type=str, required=True)
    args = parser.parse_args()

    loaded = np.load(args.data_path, allow_pickle=True)
    data = loaded["data"].astype(np.float32)
    splits = build_split_indices(len(data))
    train_start, train_end = splits["train"]
    _, test_end = splits["test"]

    train_price = data[train_start:train_end, TARGET_COLS[0]]
    train_load = data[train_start:train_end, TARGET_COLS[1]]
    train_solar = data[train_start:train_end, TARGET_COLS[2]]
    train_carbon = data[train_start:train_end, CARBON_COL]
    train_net_load = train_load - train_solar

    price_threshold = float(np.quantile(train_price, 0.9))
    carbon_threshold = float(np.quantile(train_carbon, 0.9))
    net_load_threshold = float(np.quantile(train_net_load, 0.9))

    test_slice = data[splits["test"][0]:test_end]
    test_price = test_slice[:, TARGET_COLS[0]]
    test_load = test_slice[:, TARGET_COLS[1]]
    test_solar = test_slice[:, TARGET_COLS[2]]
    test_carbon = test_slice[:, CARBON_COL]
    test_net_load = test_load - test_solar

    carbon_price_mask = ((test_price >= price_threshold) | (test_carbon >= carbon_threshold)).astype(np.int32)
    peak_mask = (test_net_load >= net_load_threshold).astype(np.int32)

    result = {
        "splits": splits,
        "thresholds": {
            "price_p90": price_threshold,
            "carbon_p90": carbon_threshold,
            "net_load_p90": net_load_threshold,
        },
        "test_mask_coverage": {
            "carbon_price_stress": float(np.mean(carbon_price_mask)),
            "peak_stress": float(np.mean(peak_mask)),
        },
        "num_test_steps": int(len(test_slice)),
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"Saved diagnostics -> {output_path}")


if __name__ == "__main__":
    main()
