from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.dataset import CityLearnDataset
from controllers.qp_controller import QPController
from eval.run_controller import get_battery_params
from models.csft import build_manual_horizon_weights

TARGET_COLS = [4, 5, 6]
TARGET_NAMES = ["price", "load", "solar"]
CARBON_COL = 3


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def infer_soc_index(data_path: str) -> int:
    loaded = np.load(data_path, allow_pickle=True)
    columns = loaded["columns"].tolist()
    for name in ["electrical_storage_soc", "electrical_storage_soc_avg"]:
        if name in columns:
            return int(columns.index(name))
    raise ValueError(f"SOC column not found in {columns}")


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


def build_stage_weights(controller_type: str) -> tuple[dict[str, float], bool]:
    if controller_type == "qp_carbon":
        return {"cost": 0.15, "carbon": 0.10, "peak": 0.65, "smooth": 0.10}, True
    if controller_type == "qp_current":
        return {"cost": 0.15, "carbon": 0.10, "peak": 0.65, "smooth": 0.10}, False
    raise ValueError(f"Unsupported controller_type: {controller_type}")


def extract_dual_prior(
    data_path: str,
    schema: str,
    forecast_config: dict,
    controller_config: dict,
    split: str,
    controller_type: str,
) -> tuple[np.ndarray, dict, dict[str, np.ndarray]]:
    history_len = int(forecast_config["model"].get("history_len", 24))
    horizon = int(forecast_config["model"]["horizon"])
    dataset = CityLearnDataset.from_file(
        data_path,
        split=split,
        history_len=history_len,
        horizon=horizon,
        target_cols=TARGET_COLS,
        return_index=False,
    )
    controller = build_controller_from_schema(schema, controller_config)
    weights, use_carbon = build_stage_weights(controller_type)
    soc_index = infer_soc_index(data_path)

    loaded = np.load(data_path, allow_pickle=True)
    raw_data = loaded["data"].astype(np.float32)
    carbon_series = raw_data[:, CARBON_COL].astype(np.float32)
    train_end = int(len(raw_data) * 0.7)
    train_targets = raw_data[:train_end, TARGET_COLS]
    channel_scale = np.std(train_targets, axis=0).astype(np.float32)
    channel_scale[channel_scale < 1e-6] = 1.0

    prior_accum = np.zeros((horizon, len(TARGET_COLS)), dtype=np.float64)
    details = {
        "price_component": np.zeros(horizon, dtype=np.float64),
        "load_component": np.zeros(horizon, dtype=np.float64),
        "solar_component": np.zeros(horizon, dtype=np.float64),
        "import_dual": np.zeros(horizon, dtype=np.float64),
        "peak_dual": np.zeros(horizon, dtype=np.float64),
        "grid_import": np.zeros(horizon, dtype=np.float64),
    }

    for i in range(len(dataset)):
        _, future_target = dataset[i]
        future_raw = future_target.numpy() * dataset.std[TARGET_COLS] + dataset.mean[TARGET_COLS]
        future_start = int(dataset.future_start_indices[i])
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

        diagnostics = controller.solve_with_diagnostics(
            state={"soc": [current_soc] * controller.num_buildings},
            forecast=future_raw,
            weights=weights,
            constraints={},
            carbon_intensity=future_carbon if use_carbon else None,
        )
        if diagnostics is None:
            continue

        grid_import = diagnostics["grid_import"]
        import_dual = diagnostics["import_dual"]
        peak_dual = diagnostics.get("peak_dual", np.zeros_like(import_dual))

        price_rel = np.abs(weights.get("cost", 0.0) * grid_import)
        load_rel = np.abs(import_dual) * controller.num_buildings
        solar_rel = np.abs(import_dual) * controller.num_buildings

        prior_accum[:, 0] += price_rel / float(channel_scale[0])
        prior_accum[:, 1] += load_rel / float(channel_scale[1])
        prior_accum[:, 2] += solar_rel / float(channel_scale[2])

        details["price_component"] += price_rel
        details["load_component"] += load_rel
        details["solar_component"] += solar_rel
        details["import_dual"] += np.abs(import_dual)
        details["peak_dual"] += np.abs(peak_dual)
        details["grid_import"] += grid_import

    prior = prior_accum / max(len(dataset), 1)
    prior = prior.astype(np.float32)
    prior = prior / (float(prior.mean()) + 1e-8)

    for key in details:
        details[key] = (details[key] / max(len(dataset), 1)).astype(np.float32)

    manual = build_manual_horizon_weights(horizon=horizon, num_targets=len(TARGET_COLS), front_steps=6, front_weight=3.0)
    manual = manual / manual.mean()
    corr = float(np.corrcoef(prior.reshape(-1), manual.reshape(-1))[0, 1])
    cosine = float(np.dot(prior.reshape(-1), manual.reshape(-1)) / ((np.linalg.norm(prior.reshape(-1)) * np.linalg.norm(manual.reshape(-1))) + 1e-8))

    metadata = {
        "split": split,
        "controller_type": controller_type,
        "history_len": history_len,
        "horizon": horizon,
        "target_names": TARGET_NAMES,
        "channel_scale": channel_scale.tolist(),
        "manual_horizon_corr": corr,
        "manual_horizon_cosine": cosine,
    }
    return prior, metadata, details


def save_prior_as_labels(
    prior: np.ndarray,
    data_path: str,
    forecast_config: dict,
    out_prefix: str,
    metadata: dict,
) -> None:
    history_len = int(forecast_config["model"].get("history_len", 24))
    horizon = int(forecast_config["model"]["horizon"])
    out_base = Path(out_prefix)
    out_base.parent.mkdir(parents=True, exist_ok=True)

    for split in ["train", "val", "test"]:
        ds = CityLearnDataset.from_file(
            data_path,
            split=split,
            history_len=history_len,
            horizon=horizon,
            target_cols=TARGET_COLS,
            return_index=False,
        )
        repeated = np.repeat(prior[None, ...], len(ds), axis=0).astype(np.float32)
        out_path = out_base.parent / f"{out_base.name}_{split}.npz"
        np.savez(
            out_path,
            sensitivity=repeated,
            future_start_indices=ds.future_start_indices.astype(np.int64),
        )
        split_meta = dict(metadata)
        split_meta["split"] = split
        split_meta["num_samples"] = int(len(ds))
        split_meta["prior_matrix"] = prior.tolist()
        out_path.with_suffix(".json").write_text(json.dumps(split_meta, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build controller-dual prior labels")
    parser.add_argument("--data_path", default="artifacts/forecast_data.npz")
    parser.add_argument("--schema", default="citylearn_challenge_2023_phase_1")
    parser.add_argument("--forecast_config", default="configs/forecast.yaml")
    parser.add_argument("--controller_config", default="configs/controller.yaml")
    parser.add_argument("--controller_type", default="qp_carbon", choices=["qp_carbon", "qp_current"])
    parser.add_argument("--split", default="train", choices=["train"])
    parser.add_argument("--output_prefix", required=True)
    parser.add_argument("--summary_path", required=True)
    args = parser.parse_args()

    forecast_config = load_config(args.forecast_config)
    controller_config = load_config(args.controller_config)
    prior, metadata, details = extract_dual_prior(
        data_path=args.data_path,
        schema=args.schema,
        forecast_config=forecast_config,
        controller_config=controller_config,
        split=args.split,
        controller_type=args.controller_type,
    )
    save_prior_as_labels(prior, args.data_path, forecast_config, args.output_prefix, metadata)

    summary = dict(metadata)
    summary["prior_matrix"] = prior.tolist()
    summary["details"] = {k: v.tolist() for k, v in details.items()}
    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
