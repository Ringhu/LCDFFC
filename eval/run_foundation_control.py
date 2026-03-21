"""Run CityLearn control with zero-shot foundation-model forecasts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
import torch
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from controllers.qp_controller import QPController
from eval.foundation_model_adapters import build_adapter
from eval.run_controller import get_battery_params, get_current_socs, obs_to_features

TARGET_COLS = [4, 5, 6]


def run_foundation_control(
    schema: str,
    foundation_model: str,
    controller_config: dict,
    weights: dict[str, float],
    output_dir: str,
    tag: str,
    device: str,
    context_length: int,
    horizon: int,
    constraints: dict | None = None,
):
    from citylearn.citylearn import CityLearnEnv

    constraints = constraints or {}
    env = CityLearnEnv(schema=schema, central_agent=True)
    obs_names = env.observation_names[0]
    num_actions = len(env.action_names[0])
    num_buildings = len(env.buildings)
    battery_params = get_battery_params(env)
    batt_cfg = controller_config.get("battery", {})
    ctrl = QPController(
        horizon=controller_config.get("horizon", horizon),
        num_buildings=num_buildings,
        battery_capacity=battery_params["capacity"],
        battery_nominal_power=battery_params["nominal_power"],
        soc_min=battery_params["soc_min"],
        soc_max=battery_params["soc_max"],
        p_max=batt_cfg.get("p_max", 1.0),
        efficiency=battery_params["efficiency"],
        time_step_hours=env.seconds_per_time_step / 3600.0,
    )

    resolved_device = device if (device.startswith("cuda") and torch.cuda.is_available()) else "cpu"
    adapter = build_adapter(foundation_model, device=resolved_device, horizon=horizon, context_length=context_length)

    obs = env.reset()
    first_obs = obs[0][0] if isinstance(obs[0][0], list) else obs[0]
    features = obs_to_features(first_obs, obs_names)
    history = [features.copy()]

    terminated = False
    truncated = False
    step = 0
    actions_log = []

    while not (terminated or truncated):
        raw_history = np.asarray(history, dtype=np.float32)
        preds = []
        for col in TARGET_COLS:
            pred = adapter.forecast_univariate(raw_history[:, col])
            preds.append(pred)
        qp_forecast = np.stack(preds, axis=-1).astype(np.float32)

        soc_vals = get_current_socs(env)
        battery_action = float(
            ctrl.act(
                state={"soc": soc_vals},
                forecast=qp_forecast,
                weights=weights,
                constraints=constraints,
            )[0]
        )

        full_action = [0.0] * num_actions
        for i, name in enumerate(env.action_names[0]):
            if name == "electrical_storage":
                full_action[i] = battery_action
        obs, reward, terminated, truncated, info = env.step([full_action])
        features = obs_to_features(obs[0], obs_names)
        history.append(features.copy())
        actions_log.append(battery_action)
        step += 1

    all_net_loads = []
    for building in env.buildings:
        all_net_loads.append(np.array(building.net_electricity_consumption[:step], dtype=np.float32))
    district_net_load = np.sum(all_net_loads, axis=0)
    prices = np.array(env.buildings[0].pricing.electricity_pricing[:step], dtype=np.float32)
    carbon = np.array(env.buildings[0].carbon_intensity.carbon_intensity[:step], dtype=np.float32)
    grid_import = np.maximum(district_net_load, 0.0)
    kpis = {
        "cost": float(np.sum(grid_import * prices)),
        "carbon": float(np.sum(grid_import * carbon)),
        "peak": float(np.max(district_net_load)),
        "ramping": float(np.sum(np.abs(np.diff(district_net_load)))) if len(district_net_load) > 1 else 0.0,
        "avg_net_load": float(np.mean(district_net_load)),
        "num_steps": int(len(district_net_load)),
        "tag": tag,
        "foundation_model": foundation_model,
    }
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{tag}_kpis.json").write_text(json.dumps(kpis, indent=2))
    np.save(out_dir / f"{tag}_actions.npy", np.array(actions_log, dtype=np.float32))
    print(json.dumps(kpis, indent=2))
    return kpis


def main():
    parser = argparse.ArgumentParser(description="Run CityLearn with zero-shot foundation forecasts + QP")
    parser.add_argument("--schema", type=str, required=True)
    parser.add_argument("--foundation_model", type=str, required=True, choices=["chronos2", "moirai2", "timesfm2.5", "moment"])
    parser.add_argument("--controller_config", type=str, default="configs/controller.yaml")
    parser.add_argument("--output_dir", type=str, default="reports/foundation_control")
    parser.add_argument("--tag", type=str, required=True)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--context_length", type=int, default=512)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--weight_cost", type=float, default=0.15)
    parser.add_argument("--weight_carbon", type=float, default=0.10)
    parser.add_argument("--weight_peak", type=float, default=0.65)
    parser.add_argument("--weight_smooth", type=float, default=0.10)
    parser.add_argument("--reserve_soc", type=float, default=0.2)
    args = parser.parse_args()

    with open(args.controller_config) as f:
        controller_config = yaml.safe_load(f)

    weights = {
        "cost": args.weight_cost,
        "carbon": args.weight_carbon,
        "peak": args.weight_peak,
        "smooth": args.weight_smooth,
    }
    constraints = {"reserve_soc": args.reserve_soc, "max_charge_rate": None}

    run_foundation_control(
        schema=args.schema,
        foundation_model=args.foundation_model,
        controller_config=controller_config,
        weights=weights,
        output_dir=args.output_dir,
        tag=args.tag,
        device=args.device,
        context_length=args.context_length,
        horizon=args.horizon,
        constraints=constraints,
    )


if __name__ == "__main__":
    main()
