"""Run preference-shift experiments on top of the existing forecast + QP loop.

Examples:
    CUDA_VISIBLE_DEVICES=3 python eval/run_preference_shift.py --router_type heuristic --max_steps 96 --device cuda:0
    CUDA_VISIBLE_DEVICES=2 python eval/run_preference_shift.py --router_type text --device cuda:0 --tag pref_text
    CUDA_VISIBLE_DEVICES=2 python eval/run_preference_shift.py --router_type fixed --fixed_regime cost --device cuda:0 --tag fixed_cost
"""

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
from eval.preference_shift_metrics import compute_episode_kpis, compute_segment_metrics
from eval.run_controller import (
    TARGET_COLS,
    build_myopic_forecast,
    build_oracle_forecast,
    get_battery_params,
    get_current_socs,
    load_oracle_targets,
    obs_to_features,
)
from llm_router.preference_routers import (
    build_default_preference_schedule,
    HeuristicPreferenceRouter,
    make_router,
    resolve_regime,
)
from models.gru_forecaster import GRUForecaster


def build_route_context(
    current_features: np.ndarray,
    qp_forecast: np.ndarray,
    soc_vals: list[float],
    regime,
) -> dict[str, object]:
    """Build a compact routing context for the high-level router."""
    current_price = float(current_features[4])
    current_carbon = float(current_features[3])
    current_load = float(current_features[5])
    current_solar = float(current_features[6])
    load_peak_forecast = float(np.max(qp_forecast[:, 1])) if qp_forecast.shape[1] > 1 else current_load
    price_delta = float(qp_forecast[-1, 0] - qp_forecast[0, 0]) if qp_forecast.shape[1] > 0 else 0.0

    if load_peak_forecast > 1.5:
        grid_stress = "critical"
    elif load_peak_forecast > 1.0:
        grid_stress = "high"
    elif load_peak_forecast > 0.6:
        grid_stress = "medium"
    else:
        grid_stress = "low"

    if price_delta > 0.005:
        price_trend = "rising"
    elif price_delta < -0.005:
        price_trend = "falling"
    else:
        price_trend = "stable"

    return {
        "regime_name": regime.name,
        "instruction": regime.instruction,
        "preference_vector": regime.preference_vector,
        "hour": int(current_features[1]),
        "day_type": int(current_features[0]),
        "price": current_price,
        "carbon_intensity": current_carbon,
        "non_shiftable_load": current_load,
        "solar_generation": current_solar,
        "price_trend": price_trend,
        "grid_stress": grid_stress,
        "soc_avg": float(np.mean(soc_vals)),
        "load_peak_forecast": load_peak_forecast,
    }


def load_model_if_needed(
    forecast_mode: str,
    checkpoint: str,
    norm_stats_path: str,
    forecast_config: dict,
    device: str,
):
    """Load the low-level forecaster when the experiment uses learned forecasts."""
    model_cfg = forecast_config["model"]
    if forecast_mode != "learned":
        return None, None, None

    norm_stats = np.load(norm_stats_path)
    mean, std = norm_stats["mean"], norm_stats["std"]
    model = GRUForecaster(
        input_dim=len(mean),
        hidden_dim=model_cfg["hidden_dim"],
        num_layers=model_cfg["num_layers"],
        output_dim=model_cfg["output_dim"],
        horizon=model_cfg["horizon"],
        dropout=0.0,
    ).to(device)
    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
    model.eval()
    return model, mean, std


def run_preference_shift(
    schema: str,
    checkpoint: str,
    norm_stats_path: str,
    forecast_config: dict,
    controller_config: dict,
    output_dir: str,
    tag: str,
    router_type: str,
    fixed_regime: str,
    forecast_mode: str,
    oracle_data_path: str,
    device: str,
    max_steps: int | None = None,
    corruption_every: int = 0,
    corruption_mode: str = "extreme_peak",
    route_fallback: str = "none",
) -> dict[str, object]:
    """Run one preference-shift experiment."""
    from citylearn.citylearn import CityLearnEnv

    env = CityLearnEnv(schema=schema, central_agent=True)
    resolved_device = device if (device.startswith("cuda") and torch.cuda.is_available()) else "cpu"
    model_cfg = forecast_config["model"]
    history_len = model_cfg.get("history_len", 24)
    horizon = model_cfg["horizon"]

    model, mean, std = load_model_if_needed(
        forecast_mode, checkpoint, norm_stats_path, forecast_config, resolved_device
    )
    oracle_targets = load_oracle_targets(oracle_data_path) if forecast_mode == "oracle" else None

    obs_names = env.observation_names[0]
    num_actions = len(env.action_names[0])
    battery_params = get_battery_params(env)
    batt_cfg = controller_config.get("battery", {})
    ctrl = QPController(
        horizon=controller_config.get("horizon", horizon),
        num_buildings=len(env.buildings),
        battery_capacity=battery_params["capacity"],
        battery_nominal_power=battery_params["nominal_power"],
        soc_min=battery_params["soc_min"],
        soc_max=battery_params["soc_max"],
        p_max=batt_cfg.get("p_max", 1.0),
        efficiency=battery_params["efficiency"],
        time_step_hours=env.seconds_per_time_step / 3600.0,
    )

    obs = env.reset()
    first_obs = obs[0][0] if isinstance(obs[0][0], list) else obs[0]
    features = obs_to_features(first_obs, obs_names)
    history_buf = deque([features.copy() for _ in range(history_len)], maxlen=history_len)

    planned_total_steps = env.time_steps - 1
    if max_steps is not None:
        planned_total_steps = min(planned_total_steps, int(max_steps))
    schedule = build_default_preference_schedule(planned_total_steps)
    router = make_router(router_type, fixed_regime=fixed_regime)
    fallback_router = HeuristicPreferenceRouter() if route_fallback == "heuristic" else None

    terminated = False
    truncated = False
    step = 0
    actions_log = []
    route_trace = []

    while not (terminated or truncated) and step < planned_total_steps:
        history_arr = np.array(history_buf)
        current_features = history_arr[-1]

        if forecast_mode == "learned":
            history_norm = (history_arr - mean) / std
            history_tensor = torch.tensor(history_norm, dtype=torch.float32).unsqueeze(0).to(resolved_device)
            with torch.no_grad():
                pred_norm = model(history_tensor).cpu().numpy()[0]
            qp_forecast = pred_norm * std[TARGET_COLS] + mean[TARGET_COLS]
        elif forecast_mode == "oracle":
            qp_forecast = build_oracle_forecast(oracle_targets, step, ctrl.horizon)
        else:
            qp_forecast = build_myopic_forecast(current_features, ctrl.horizon)

        regime = resolve_regime(schedule, step)
        soc_vals = get_current_socs(env)
        route_context = build_route_context(current_features, qp_forecast, soc_vals, regime)
        strategy = router.route(route_context)
        corrupted = False

        if corruption_every > 0 and step > 0 and step % corruption_every == 0:
            corrupted = True
            if corruption_mode == "extreme_peak":
                strategy = {
                    "weights": {"cost": 0.05, "carbon": 0.05, "peak": 0.8, "smooth": 0.1},
                    "constraints": {"reserve_soc": None, "max_charge_rate": None},
                }
            elif corruption_mode == "extreme_cost":
                strategy = {
                    "weights": {"cost": 0.8, "carbon": 0.05, "peak": 0.05, "smooth": 0.1},
                    "constraints": {"reserve_soc": None, "max_charge_rate": None},
                }
            elif corruption_mode == "invalid_missing_constraints":
                strategy = {"weights": {"cost": 1.5}}
            else:
                raise ValueError(f"Unsupported corruption_mode: {corruption_mode}")

        fallback_used = False
        if route_fallback == "schema":
            strategy = {
                "weights": dict(strategy.get("weights", {})),
                "constraints": dict(strategy.get("constraints", {})) if isinstance(strategy.get("constraints", {}), dict) else {},
            }
            from llm_router.json_schema import validate_router_output
            validated = validate_router_output(strategy)
            fallback_used = corrupted and validated != strategy
            strategy = validated
        elif route_fallback == "heuristic" and corrupted:
            strategy = fallback_router.route(route_context)
            fallback_used = True

        battery_action = float(
            ctrl.act(
                state={"soc": soc_vals},
                forecast=qp_forecast,
                weights=strategy["weights"],
                constraints=strategy["constraints"],
            )[0]
        )

        full_action = [0.0] * num_actions
        for i, name in enumerate(env.action_names[0]):
            if name == "electrical_storage":
                full_action[i] = battery_action
        obs, reward, terminated, truncated, info = env.step([full_action])

        features = obs_to_features(obs[0], obs_names)
        history_buf.append(features)
        actions_log.append(battery_action)
        route_trace.append(
            {
                "step": step,
                "regime": regime.name,
                "instruction": regime.instruction,
                "weights": strategy["weights"],
                "constraints": strategy["constraints"],
                "battery_action": battery_action,
                "soc_avg": float(np.mean(soc_vals)),
                "grid_stress": route_context["grid_stress"],
                "corrupted": corrupted,
                "fallback_used": fallback_used,
            }
        )
        step += 1

    all_net_loads = []
    for building in env.buildings:
        all_net_loads.append(np.array(building.net_electricity_consumption[:step], dtype=np.float32))
    district_net_load = np.sum(all_net_loads, axis=0)
    prices = np.array(env.buildings[0].pricing.electricity_pricing[:step], dtype=np.float32)
    carbon = np.array(env.buildings[0].carbon_intensity.carbon_intensity[:step], dtype=np.float32)
    avg_soc_trace = np.mean(
        [np.array(building.electrical_storage.soc[:step], dtype=np.float32) for building in env.buildings],
        axis=0,
    )

    episode_kpis = compute_episode_kpis(district_net_load, prices, carbon)
    episode_kpis["tag"] = tag
    episode_kpis["router_type"] = router_type
    episode_kpis["forecast_mode"] = forecast_mode
    episode_kpis["fixed_regime"] = fixed_regime if router_type == "fixed" else None
    episode_kpis["corruption_every"] = corruption_every
    episode_kpis["corruption_mode"] = corruption_mode if corruption_every > 0 else None
    episode_kpis["route_fallback"] = route_fallback

    segment_summaries = []
    for regime in schedule:
        segment_summaries.append(
            compute_segment_metrics(
                district_net_load,
                prices,
                carbon,
                avg_soc_trace,
                regime.start_step,
                min(regime.end_step, step),
                {
                    "name": regime.name,
                    "instruction": regime.instruction,
                    "preference_vector": regime.preference_vector,
                    "target_profile": regime.target_profile,
                },
            )
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{tag}_kpis.json").write_text(json.dumps(episode_kpis, indent=2))
    (out_dir / f"{tag}_segments.json").write_text(json.dumps(segment_summaries, indent=2))
    (out_dir / f"{tag}_routes.json").write_text(json.dumps(route_trace, indent=2))
    np.save(out_dir / f"{tag}_actions.npy", np.array(actions_log, dtype=np.float32))

    print(f"Preference-shift episode completed: {step} steps")
    print(f"{tag} KPIs:")
    for key, value in episode_kpis.items():
        print(f"  {key}: {value}")

    return {"episode_kpis": episode_kpis, "segments": segment_summaries}


def main():
    parser = argparse.ArgumentParser(description="Run preference-shift routing experiments")
    parser.add_argument("--schema", type=str, default="citylearn_challenge_2023_phase_1")
    parser.add_argument("--checkpoint", type=str, default="artifacts/checkpoints/gru_mse_best.pt")
    parser.add_argument("--norm_stats", type=str, default="artifacts/norm_stats.npz")
    parser.add_argument("--forecast_config", type=str, default="configs/forecast.yaml")
    parser.add_argument("--controller_config", type=str, default="configs/controller.yaml")
    parser.add_argument("--output_dir", type=str, default="reports/preference_shift")
    parser.add_argument("--tag", type=str, default="preference_shift")
    parser.add_argument(
        "--router_type",
        choices=["fixed", "heuristic", "numeric", "text", "text_v2", "text_v3", "text_v4", "text_best"],
        default="heuristic",
    )
    parser.add_argument("--fixed_regime", choices=["balanced", "cost", "carbon", "peak", "reserve"], default="balanced")
    parser.add_argument("--forecast_mode", choices=["learned", "oracle", "myopic"], default="learned")
    parser.add_argument("--oracle_data", type=str, default="artifacts/forecast_data.npz")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--max_steps", type=int, default=None)
    parser.add_argument("--corruption_every", type=int, default=0)
    parser.add_argument(
        "--corruption_mode",
        type=str,
        default="extreme_peak",
        choices=["extreme_peak", "extreme_cost", "invalid_missing_constraints"],
    )
    parser.add_argument(
        "--route_fallback",
        type=str,
        default="none",
        choices=["none", "schema", "heuristic"],
    )
    args = parser.parse_args()

    with open(args.forecast_config) as f:
        forecast_config = yaml.safe_load(f)
    with open(args.controller_config) as f:
        controller_config = yaml.safe_load(f)

    run_preference_shift(
        schema=args.schema,
        checkpoint=args.checkpoint,
        norm_stats_path=args.norm_stats,
        forecast_config=forecast_config,
        controller_config=controller_config,
        output_dir=args.output_dir,
        tag=args.tag,
        router_type=args.router_type,
        fixed_regime=args.fixed_regime,
        forecast_mode=args.forecast_mode,
        oracle_data_path=args.oracle_data,
        device=args.device,
        max_steps=args.max_steps,
        corruption_every=args.corruption_every,
        corruption_mode=args.corruption_mode,
        route_fallback=args.route_fallback,
    )


if __name__ == "__main__":
    main()
