"""Generate offline CSFT sensitivity labels for fixed forecast-then-control.

Usage:
    python scripts/generate_csft_labels.py \
        --data_path artifacts/forecast_data.npz \
        --forecast_config configs/forecast.yaml \
        --controller_config configs/controller.yaml \
        --output_path artifacts/csft_labels_qp_carbon_train.npz
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from controllers.qp_controller import QPController
from data.dataset import CityLearnDataset
from eval.run_controller import get_battery_params
from models.csft import clip_and_normalize_sensitivity

TARGET_COLS = [4, 5, 6]
TARGET_NAMES = ["price", "load", "solar"]
CARBON_COL = 3


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_controller_from_schema(schema: str, controller_config: dict) -> QPController:
    from citylearn.citylearn import CityLearnEnv

    env = CityLearnEnv(schema=schema, central_agent=True)
    battery_params = get_battery_params(env)
    batt_cfg = controller_config.get("battery", {})
    return QPController(
        horizon=controller_config.get("horizon", 24),
        num_buildings=len(env.buildings),
        battery_capacity=battery_params["capacity"],
        battery_nominal_power=battery_params["nominal_power"],
        soc_min=battery_params["soc_min"],
        soc_max=battery_params["soc_max"],
        p_max=batt_cfg.get("p_max", 1.0),
        efficiency=battery_params["efficiency"],
        time_step_hours=env.seconds_per_time_step / 3600.0,
    )


def infer_soc_index(data_path: str) -> int:
    loaded = np.load(data_path, allow_pickle=True)
    columns = loaded["columns"].tolist()
    candidates = ["electrical_storage_soc", "electrical_storage_soc_avg"]
    for name in candidates:
        if name in columns:
            return int(columns.index(name))
    raise ValueError(
        f"Could not find SOC column in forecast_data.npz. Tried: {candidates}. Available columns: {columns}"
    )


def build_stage_weights(controller_type: str) -> tuple[dict[str, float], bool]:
    if controller_type == "qp_carbon":
        return {"cost": 0.15, "carbon": 0.10, "peak": 0.65, "smooth": 0.10}, True
    if controller_type == "qp_current":
        return {"cost": 0.15, "carbon": 0.10, "peak": 0.65, "smooth": 0.10}, False
    raise ValueError(f"Unsupported controller_type: {controller_type}")


def compute_stage_objective(
    ctrl: QPController,
    current_soc: float,
    future_targets: np.ndarray,
    future_carbon: np.ndarray | None,
    weights: dict[str, float],
    use_carbon: bool,
) -> float:
    carbon = None
    if use_carbon and future_carbon is not None:
        carbon = future_carbon.copy()
    action = ctrl.act(
        state={"soc": [current_soc] * ctrl.num_buildings},
        forecast=future_targets,
        weights=weights,
        constraints={},
        carbon_intensity=carbon,
    )
    action_value = float(action[0])
    aggregate_storage_power = float(np.sum(ctrl.battery_nominal_power) * ctrl.time_step_hours)
    price = float(future_targets[0, 0])
    load = float(future_targets[0, 1])
    solar = float(future_targets[0, 2])
    net_load = ctrl.num_buildings * (load - solar) + aggregate_storage_power * action_value
    grid_import = max(net_load, 0.0)
    objective = 0.0
    objective += weights.get("cost", 0.0) * price * grid_import
    if use_carbon and future_carbon is not None:
        objective += weights.get("carbon", 0.0) * float(future_carbon[0]) * grid_import
    objective += weights.get("peak", 0.0) * grid_import
    objective += weights.get("smooth", 0.0) * (action_value ** 2)
    return float(objective)


def generate_labels(
    data_path: str,
    schema: str,
    forecast_config: dict,
    controller_config: dict,
    split: str,
    controller_type: str,
    max_samples: int | None,
    clip_quantile: float,
) -> tuple[np.ndarray, np.ndarray, dict]:
    history_len = int(forecast_config["model"].get("history_len", 24))
    horizon = int(forecast_config["model"]["horizon"])
    dataset = CityLearnDataset.from_file(
        data_path,
        split=split,
        history_len=history_len,
        horizon=horizon,
        target_cols=TARGET_COLS,
    )
    controller = build_controller_from_schema(schema, controller_config)
    weights, use_carbon = build_stage_weights(controller_type)
    soc_index = infer_soc_index(data_path)

    loaded = np.load(data_path, allow_pickle=True)
    raw_data = loaded["data"].astype(np.float32)
    train_end = int(len(raw_data) * 0.7)
    num_samples = len(dataset) if max_samples is None else min(len(dataset), int(max_samples))
    sensitivity = np.zeros((num_samples, horizon, len(TARGET_COLS)), dtype=np.float32)
    future_start_indices = dataset.future_start_indices[:num_samples].copy()

    deltas = np.zeros(len(TARGET_COLS), dtype=np.float32)
    train_slice = raw_data[:train_end, TARGET_COLS]
    carbon_series = raw_data[:, CARBON_COL].astype(np.float32)
    for idx in range(len(TARGET_COLS)):
        channel_std = float(np.std(train_slice[:, idx]))
        deltas[idx] = max(1e-3, 0.1 * channel_std)

    for i in range(num_samples):
        _, future_target = dataset[i]
        future_raw = future_target.numpy() * dataset.std[TARGET_COLS] + dataset.mean[TARGET_COLS]
        future_start = int(future_start_indices[i])
        current_t = future_start - 1
        current_soc = float(raw_data[current_t, soc_index])
        carbon_end = future_start + horizon
        future_carbon = carbon_series[future_start:carbon_end]
        if len(future_carbon) == 0:
            future_carbon = carbon_series[-1:]
        if len(future_carbon) < horizon:
            future_carbon = np.concatenate(
                [future_carbon, np.repeat(future_carbon[-1:], horizon - len(future_carbon))],
                axis=0,
            )

        for h in range(horizon):
            for c in range(len(TARGET_COLS)):
                delta = deltas[c]
                future_plus = future_raw.copy()
                future_minus = future_raw.copy()
                future_plus[h, c] += delta
                future_minus[h, c] -= delta
                obj_plus = compute_stage_objective(controller, current_soc, future_plus, future_carbon, weights, use_carbon)
                obj_minus = compute_stage_objective(controller, current_soc, future_minus, future_carbon, weights, use_carbon)
                sensitivity[i, h, c] = abs(obj_plus - obj_minus) / (2.0 * delta)

    normalized = clip_and_normalize_sensitivity(sensitivity, clip_quantile=clip_quantile)
    metadata = {
        "split": split,
        "controller_type": controller_type,
        "num_samples": int(num_samples),
        "history_len": int(history_len),
        "horizon": int(horizon),
        "target_cols": TARGET_COLS,
        "target_names": TARGET_NAMES,
        "deltas": deltas.tolist(),
        "raw_mean": float(np.mean(sensitivity)),
        "raw_max": float(np.max(sensitivity)),
        "normalized_mean": float(np.mean(normalized)),
        "normalized_max": float(np.max(normalized)),
        "clip_quantile": float(clip_quantile),
    }
    return normalized, future_start_indices, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate offline CSFT sensitivity labels")
    parser.add_argument("--data_path", type=str, default="artifacts/forecast_data.npz")
    parser.add_argument("--schema", type=str, default="citylearn_challenge_2023_phase_1")
    parser.add_argument("--forecast_config", type=str, default="configs/forecast.yaml")
    parser.add_argument("--controller_config", type=str, default="configs/controller.yaml")
    parser.add_argument("--output_path", type=str, required=True)
    parser.add_argument("--metadata_path", type=str, default=None)
    parser.add_argument("--split", type=str, default="train", choices=["train", "val", "test"])
    parser.add_argument("--controller_type", type=str, default="qp_carbon", choices=["qp_carbon", "qp_current"])
    parser.add_argument("--max_samples", type=int, default=None)
    parser.add_argument("--clip_quantile", type=float, default=0.95)
    args = parser.parse_args()

    forecast_config = load_config(args.forecast_config)
    controller_config = load_config(args.controller_config)
    labels, future_start_indices, metadata = generate_labels(
        data_path=args.data_path,
        schema=args.schema,
        forecast_config=forecast_config,
        controller_config=controller_config,
        split=args.split,
        controller_type=args.controller_type,
        max_samples=args.max_samples,
        clip_quantile=args.clip_quantile,
    )

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output_path, sensitivity=labels, future_start_indices=future_start_indices)

    metadata_path = Path(args.metadata_path) if args.metadata_path else output_path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))
    print(f"Saved labels -> {output_path}")
    print(f"Saved metadata -> {metadata_path}")


if __name__ == "__main__":
    main()
