from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
import torch
import yaml

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from controllers.qp_controller import QPController
from data.dataset import CityLearnDataset
from eval.run_controller import (
    get_battery_params,
    get_current_socs,
    load_oracle_series,
    obs_to_features,
)
from models.csft import build_manual_horizon_weights
from models.factory import build_forecaster

TARGET_COLS = [4, 5, 6]
TARGET_NAMES = ["price", "load", "solar"]
CARBON_COL = 3


def unwrap_obs(obs):
    if isinstance(obs, tuple):
        obs = obs[0]
    if isinstance(obs, list) and len(obs) == 1:
        obs = obs[0]
    return obs


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_controller_from_schema(schema: str, controller_config: dict) -> tuple[QPController, list[str]]:
    from citylearn.citylearn import CityLearnEnv

    env = CityLearnEnv(schema=schema, central_agent=True)
    battery_params = get_battery_params(env)
    batt_cfg = controller_config.get("battery", {})
    ctrl = QPController(
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
    return ctrl, env.observation_names[0]


def solve_action_sequence(
    ctrl: QPController,
    soc_vals: list[float],
    forecast: np.ndarray,
    weights: dict[str, float],
    carbon_forecast: np.ndarray | None,
) -> np.ndarray | None:
    fc, carbon = ctrl._prepare_forecast(forecast, carbon_forecast)
    return ctrl._build_and_solve(
        soc_init=ctrl._as_array(soc_vals, ctrl.num_buildings),
        forecast=fc,
        weights=weights,
        constraints={},
        carbon_intensity=carbon,
        collect_diagnostics=False,
    )


def compute_stage_objective_from_solution(
    ctrl: QPController,
    action_seq: np.ndarray,
    future_targets: np.ndarray,
    future_carbon: np.ndarray | None,
    weights: dict[str, float],
) -> float:
    action_arr = np.asarray(action_seq)
    action_value = float(action_arr[0]) if action_arr.ndim == 1 else float(action_arr[0, 0])
    aggregate_storage_power = float(np.sum(ctrl.battery_nominal_power) * ctrl.time_step_hours)
    price = float(future_targets[0, 0])
    load = float(future_targets[0, 1])
    solar = float(future_targets[0, 2])
    net_load = ctrl.num_buildings * (load - solar) + aggregate_storage_power * action_value
    grid_import = max(net_load, 0.0)
    objective = 0.0
    objective += weights.get("cost", 0.0) * price * grid_import
    if weights.get("carbon", 0.0) > 0 and future_carbon is not None:
        objective += weights.get("carbon", 0.0) * float(future_carbon[0]) * grid_import
    objective += weights.get("peak", 0.0) * grid_import
    objective += weights.get("smooth", 0.0) * (action_value ** 2)
    return float(objective)


def load_model(checkpoint: str, config: dict, device: str, input_dim: int, output_dim: int):
    model = build_forecaster(config["model"], input_dim=input_dim, output_dim=output_dim).to(device)
    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
    model.eval()
    return model


def build_stage_weights(controller_type: str) -> tuple[dict[str, float], bool]:
    if controller_type == "qp_carbon":
        return {"cost": 0.15, "carbon": 0.10, "peak": 0.65, "smooth": 0.10}, True
    if controller_type == "qp_current":
        return {"cost": 0.15, "carbon": 0.0, "peak": 0.65, "smooth": 0.10}, False
    raise ValueError(f"Unsupported controller_type: {controller_type}")


def extract_replay_prior(
    schema: str,
    data_path: str,
    checkpoint: str,
    forecast_config: dict,
    controller_config: dict,
    controller_type: str,
    device: str,
) -> tuple[np.ndarray, dict]:
    from citylearn.citylearn import CityLearnEnv

    weights, use_carbon = build_stage_weights(controller_type)
    history_len = int(forecast_config["model"].get("history_len", 24))
    horizon = int(forecast_config["model"]["horizon"])
    loaded = np.load(data_path, allow_pickle=True)
    full_data = loaded["data"].astype(np.float32)
    ds_train = CityLearnDataset.from_file(data_path, split="train", history_len=history_len, horizon=horizon, target_cols=TARGET_COLS)
    channel_scale = np.std(full_data[: int(len(full_data) * 0.7), TARGET_COLS], axis=0).astype(np.float32)
    channel_scale[channel_scale < 1e-6] = 1.0

    env = CityLearnEnv(schema=schema, central_agent=True)
    obs_names = env.observation_names[0]
    ctrl, _ = build_controller_from_schema(schema, controller_config)
    model = load_model(checkpoint, forecast_config, device, input_dim=ds_train.num_features, output_dim=ds_train.num_targets)
    mean, std = ds_train.mean, ds_train.std
    oracle_carbon = load_oracle_series(data_path, CARBON_COL)

    obs = env.reset()
    raw_obs = unwrap_obs(obs)
    features = obs_to_features(raw_obs, obs_names)
    history_buf = deque([features.copy() for _ in range(history_len)], maxlen=history_len)

    positive_steps = 0
    sensitivity_sum = np.zeros((horizon, len(TARGET_COLS)), dtype=np.float64)
    sensitivity_count = np.zeros((horizon, len(TARGET_COLS)), dtype=np.int64)
    terminated = False
    truncated = False
    step = 0

    train_target_std = channel_scale.astype(np.float32)
    deltas = np.maximum(1e-3, 0.1 * train_target_std)

    while not (terminated or truncated):
        history_arr = np.array(history_buf)
        history_norm = (history_arr - mean) / std
        history_tensor = torch.tensor(history_norm, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            pred_norm = model(history_tensor).cpu().numpy()[0]
        qp_forecast = pred_norm * std[TARGET_COLS] + mean[TARGET_COLS]
        soc_vals = get_current_socs(env)
        carbon_forecast = None
        if use_carbon:
            carbon_forecast = oracle_carbon[step + 1 : step + 1 + ctrl.horizon]
            if len(carbon_forecast) == 0:
                carbon_forecast = oracle_carbon[-1:]
            if len(carbon_forecast) < ctrl.horizon:
                pad = np.repeat(carbon_forecast[-1:], ctrl.horizon - len(carbon_forecast), axis=0)
                carbon_forecast = np.concatenate([carbon_forecast, pad], axis=0)
            carbon_forecast = carbon_forecast.astype(np.float32)

        base_action_seq = solve_action_sequence(ctrl, soc_vals, qp_forecast, weights, carbon_forecast)
        if base_action_seq is not None:
            positive_steps += 1
            for h in range(horizon):
                for c in range(len(TARGET_COLS)):
                    delta = float(deltas[c])
                    future_plus = qp_forecast.copy()
                    future_minus = qp_forecast.copy()
                    future_plus[h, c] += delta
                    future_minus[h, c] -= delta
                    act_plus = solve_action_sequence(ctrl, soc_vals, future_plus, weights, carbon_forecast)
                    act_minus = solve_action_sequence(ctrl, soc_vals, future_minus, weights, carbon_forecast)
                    if act_plus is None or act_minus is None:
                        continue
                    obj_plus = compute_stage_objective_from_solution(ctrl, act_plus, future_plus, carbon_forecast, weights)
                    obj_minus = compute_stage_objective_from_solution(ctrl, act_minus, future_minus, carbon_forecast, weights)
                    sens = abs(obj_plus - obj_minus) / (2.0 * delta)
                    sensitivity_sum[h, c] += float(sens / max(train_target_std[c], 1e-6))
                    sensitivity_count[h, c] += 1

        action = ctrl.act(
            state={"soc": soc_vals},
            forecast=qp_forecast,
            weights=weights,
            constraints={},
            carbon_intensity=carbon_forecast,
        )
        num_actions = len(env.action_names[0])
        full_action = [0.0] * num_actions
        for i, name in enumerate(env.action_names[0]):
            if name == "electrical_storage":
                full_action[i] = float(action[0])
        obs, reward, terminated, truncated, info = env.step([full_action])
        raw_obs = unwrap_obs(obs)
        features = obs_to_features(raw_obs, obs_names)
        history_buf.append(features)
        step += 1

    prior = np.divide(
        sensitivity_sum,
        np.maximum(sensitivity_count, 1),
        out=np.zeros_like(sensitivity_sum, dtype=np.float64),
        where=sensitivity_count > 0,
    ).astype(np.float32)
    if float(prior.mean()) > 0:
        prior = prior / (float(prior.mean()) + 1e-8)

    manual = build_manual_horizon_weights(horizon=horizon, num_targets=len(TARGET_COLS), front_steps=6, front_weight=3.0)
    manual = manual / manual.mean()
    prior_flat = prior.reshape(-1)
    manual_flat = manual.reshape(-1)
    if np.allclose(prior_flat, 0.0):
        corr = None
        cosine = 0.0
    else:
        corr = float(np.corrcoef(prior_flat, manual_flat)[0, 1])
        cosine = float(np.dot(prior_flat, manual_flat) / ((np.linalg.norm(prior_flat) * np.linalg.norm(manual_flat)) + 1e-8))

    metadata = {
        "controller_type": controller_type,
        "history_len": history_len,
        "horizon": horizon,
        "target_names": TARGET_NAMES,
        "solved_replay_steps": int(positive_steps),
        "total_replay_steps": int(step),
        "solved_fraction": float(positive_steps / max(step, 1)),
        "nonzero_prior_fraction": float(np.mean(prior > 0)),
        "manual_horizon_corr": corr,
        "manual_horizon_cosine": cosine,
        "channel_scale": train_target_std.tolist(),
        "sensitivity_count": sensitivity_count.tolist(),
        "prior_matrix": prior.tolist(),
    }
    return prior, metadata


def save_prior_as_labels(prior: np.ndarray, data_path: str, forecast_config: dict, out_prefix: str, metadata: dict) -> None:
    history_len = int(forecast_config["model"].get("history_len", 24))
    horizon = int(forecast_config["model"]["horizon"])
    out_base = Path(out_prefix)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for split in ["train", "val", "test"]:
        ds = CityLearnDataset.from_file(data_path, split=split, history_len=history_len, horizon=horizon, target_cols=TARGET_COLS, return_index=False)
        repeated = np.repeat(prior[None, ...], len(ds), axis=0).astype(np.float32)
        out_path = out_base.parent / f"{out_base.name}_{split}.npz"
        np.savez(out_path, sensitivity=repeated, future_start_indices=ds.future_start_indices.astype(np.int64))
        split_meta = dict(metadata)
        split_meta["split"] = split
        split_meta["num_samples"] = int(len(ds))
        out_path.with_suffix('.json').write_text(json.dumps(split_meta, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build replay-calibrated controller prior labels")
    parser.add_argument("--schema", default="citylearn_challenge_2023_phase_1")
    parser.add_argument("--data_path", default="artifacts/forecast_data.npz")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--forecast_config", default="configs/forecast.yaml")
    parser.add_argument("--controller_config", default="configs/controller.yaml")
    parser.add_argument("--controller_type", default="qp_carbon", choices=["qp_carbon", "qp_current"])
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output_prefix", required=True)
    parser.add_argument("--summary_path", required=True)
    args = parser.parse_args()

    forecast_config = load_config(args.forecast_config)
    if args.controller_type != "qp_carbon":
        raise ValueError("Q202 currently requires qp_carbon")
    if str(forecast_config["model"].get("type", "")).lower() != "gru":
        raise ValueError("Q202 currently requires the GRU forecaster")
    controller_config = load_config(args.controller_config)
    prior, metadata = extract_replay_prior(
        schema=args.schema,
        data_path=args.data_path,
        checkpoint=args.checkpoint,
        forecast_config=forecast_config,
        controller_config=controller_config,
        controller_type=args.controller_type,
        device=args.device,
    )
    save_prior_as_labels(prior, args.data_path, forecast_config, args.output_prefix, metadata)
    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
