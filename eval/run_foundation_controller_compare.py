"""Compare multiple controller families under the same foundation-model forecasts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from controllers.baseline_controllers import ActionGridController, ForecastHeuristicController
from controllers.qp_controller import QPController
from eval.foundation_model_adapters import build_adapter
from eval.run_controller import get_battery_params, get_current_socs, obs_to_features

PRICE_COL = 4
LOAD_COL = 5
SOLAR_COL = 6
CARBON_COL = 3


def _build_controller(controller_type: str, controller_config: dict, env):
    battery_params = get_battery_params(env)
    batt_cfg = controller_config.get("battery", {})
    common_kwargs = dict(
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
    if controller_type in {"qp_current", "qp_carbon"}:
        return QPController(**common_kwargs)
    if controller_type == "forecast_heuristic":
        return ForecastHeuristicController(**common_kwargs)
    if controller_type == "action_grid":
        return ActionGridController(**common_kwargs)
    if controller_type == "zero_action":
        return None
    raise ValueError(f"Unsupported controller_type: {controller_type}")


def _predict_foundation_forecasts(adapter, history_arr: np.ndarray, include_carbon: bool):
    price = adapter.forecast_univariate(history_arr[:, PRICE_COL])
    load = adapter.forecast_univariate(history_arr[:, LOAD_COL])
    solar = adapter.forecast_univariate(history_arr[:, SOLAR_COL])
    qp_forecast = np.stack([price, load, solar], axis=-1).astype(np.float32)
    carbon = None
    if include_carbon:
        carbon = adapter.forecast_univariate(history_arr[:, CARBON_COL]).astype(np.float32)
    return qp_forecast, carbon


def run_controller_compare(
    schema: str,
    foundation_model: str,
    controller_type: str,
    controller_config: dict,
    weights: dict[str, float],
    output_dir: str,
    tag: str,
    device: str,
    context_length: int,
    horizon: int,
    constraints: dict | None = None,
    max_steps: int | None = None,
):
    from citylearn.citylearn import CityLearnEnv

    constraints = constraints or {}
    env = CityLearnEnv(schema=schema, central_agent=True)
    obs_names = env.observation_names[0]
    num_actions = len(env.action_names[0])
    resolved_device = device if (device.startswith("cuda") and torch.cuda.is_available()) else "cpu"
    adapter = build_adapter(foundation_model, device=resolved_device, horizon=horizon, context_length=context_length)
    ctrl = _build_controller(controller_type, controller_config, env)

    obs = env.reset()
    first_obs = obs[0][0] if isinstance(obs[0][0], list) else obs[0]
    history = [obs_to_features(first_obs, obs_names).copy()]

    terminated = False
    truncated = False
    step = 0
    actions_log: list[float] = []
    planned_steps = env.time_steps - 1 if max_steps is None else min(env.time_steps - 1, int(max_steps))
    include_carbon = controller_type in {"qp_carbon", "forecast_heuristic", "action_grid"}

    while not (terminated or truncated) and step < planned_steps:
        history_arr = np.asarray(history, dtype=np.float32)
        qp_forecast, carbon_forecast = _predict_foundation_forecasts(adapter, history_arr, include_carbon)
        soc_vals = get_current_socs(env)

        if controller_type == "zero_action":
            battery_action = 0.0
        else:
            action = ctrl.act(
                state={"soc": soc_vals},
                forecast=qp_forecast,
                weights=weights,
                constraints=constraints,
                carbon_intensity=carbon_forecast,
            )
            if controller_type == "qp_current":
                action = ctrl.act(
                    state={"soc": soc_vals},
                    forecast=qp_forecast,
                    weights=weights,
                    constraints=constraints,
                    carbon_intensity=None,
                )
            battery_action = float(action[0])

        full_action = [0.0] * num_actions
        for i, name in enumerate(env.action_names[0]):
            if name == "electrical_storage":
                full_action[i] = battery_action
        obs, reward, terminated, truncated, info = env.step([full_action])
        history.append(obs_to_features(obs[0], obs_names).copy())
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
        "avg_abs_action": float(np.mean(np.abs(actions_log))) if actions_log else 0.0,
        "num_steps": int(len(district_net_load)),
        "tag": tag,
        "foundation_model": foundation_model,
        "controller_type": controller_type,
        "used_carbon_forecast": bool(include_carbon),
    }
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{tag}_kpis.json").write_text(json.dumps(kpis, indent=2))
    np.save(out_dir / f"{tag}_actions.npy", np.array(actions_log, dtype=np.float32))
    print(json.dumps(kpis, indent=2))
    return kpis


def main():
    parser = argparse.ArgumentParser(description="Compare controller families under the same foundation-model forecasts")
    parser.add_argument("--schema", type=str, required=True)
    parser.add_argument("--foundation_model", type=str, required=True, choices=["chronos2", "moirai2", "timesfm2.5", "moment"])
    parser.add_argument(
        "--controller_type",
        type=str,
        required=True,
        choices=["zero_action", "qp_current", "qp_carbon", "forecast_heuristic", "action_grid"],
    )
    parser.add_argument("--controller_config", type=str, default="configs/controller.yaml")
    parser.add_argument("--output_dir", type=str, default="reports/foundation_controller_compare")
    parser.add_argument("--tag", type=str, required=True)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--context_length", type=int, default=512)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--max_steps", type=int, default=None)
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

    run_controller_compare(
        schema=args.schema,
        foundation_model=args.foundation_model,
        controller_type=args.controller_type,
        controller_config=controller_config,
        weights=weights,
        output_dir=args.output_dir,
        tag=args.tag,
        device=args.device,
        context_length=args.context_length,
        horizon=args.horizon,
        constraints=constraints,
        max_steps=args.max_steps,
    )


if __name__ == "__main__":
    main()
