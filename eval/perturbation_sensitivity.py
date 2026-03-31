"""Channel-horizon perturbation sensitivity analysis.

Perturbs oracle forecast at each (channel, horizon) cell, reruns the QP,
and measures KPI change to build a sensitivity heatmap.

Usage:
    python eval/perturbation_sensitivity.py --help
    python eval/perturbation_sensitivity.py \\
        --schema citylearn_challenge_2023_phase_1 \\
        --oracle_data artifacts/forecast_data.npz \\
        --output_dir reports/cavs/sensitivity \\
        --delta 0.1
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
from eval.run_controller import (
    TARGET_COLS,
    build_oracle_forecast,
    get_battery_params,
    get_current_socs,
    load_oracle_series,
    load_oracle_targets,
    obs_to_features,
)


def compute_kpi_from_env(env) -> dict[str, float]:
    """Extract KPIs from a completed CityLearn environment."""
    total_cost = 0.0
    total_carbon = 0.0
    all_net_loads = []
    for b in env.buildings:
        net_elec = np.array(b.net_electricity_consumption)
        pricing = np.array(b.pricing.electricity_pricing)[: len(net_elec)]
        carbon = np.array(b.carbon_intensity.carbon_intensity)[: len(net_elec)]
        total_cost += float(np.sum(np.maximum(net_elec, 0) * pricing))
        total_carbon += float(np.sum(np.maximum(net_elec, 0) * carbon))
        all_net_loads.append(net_elec)
    district = np.sum(all_net_loads, axis=0)
    return {
        "cost": total_cost,
        "carbon": total_carbon,
        "peak": float(np.max(district)),
        "ramping": float(np.sum(np.abs(np.diff(district)))),
    }


def run_oracle_episode(
    schema: str,
    oracle_data_path: str,
    controller_config: dict,
    weights: dict[str, float],
    forecast_modifier=None,
) -> dict[str, float]:
    """Run one oracle episode, optionally modifying the forecast each step.

    Args:
        schema: CityLearn dataset name.
        oracle_data_path: Path to prepared forecast data.
        controller_config: Controller config dict.
        weights: QP objective weights.
        forecast_modifier: Optional callable(forecast, step) -> modified_forecast.

    Returns:
        Dict of KPI values.
    """
    from collections import deque

    from citylearn.citylearn import CityLearnEnv

    oracle_targets = load_oracle_targets(oracle_data_path)
    oracle_carbon = load_oracle_series(oracle_data_path, 3)

    env = CityLearnEnv(schema=schema, central_agent=True)
    obs_names = env.observation_names[0]
    num_actions = len(env.action_names[0])
    num_buildings = len(env.buildings)
    battery_params = get_battery_params(env)
    horizon = controller_config.get("horizon", 24)

    batt_cfg = controller_config.get("battery", {})
    ctrl = QPController(
        horizon=horizon,
        num_buildings=num_buildings,
        battery_capacity=battery_params["capacity"],
        battery_nominal_power=battery_params["nominal_power"],
        soc_min=battery_params["soc_min"],
        soc_max=battery_params["soc_max"],
        p_max=batt_cfg.get("p_max", 1.0),
        efficiency=battery_params["efficiency"],
        time_step_hours=env.seconds_per_time_step / 3600.0,
    )

    obs = env.reset()
    features = obs_to_features(
        obs[0][0] if isinstance(obs[0][0], list) else obs[0], obs_names
    )
    history_buf = deque([features.copy() for _ in range(24)], maxlen=24)

    terminated = False
    truncated = False
    step = 0

    while not (terminated or truncated):
        forecast = build_oracle_forecast(oracle_targets, step, ctrl.horizon)

        if forecast_modifier is not None:
            forecast = forecast_modifier(forecast.copy(), step)

        soc_vals = get_current_socs(env)
        carbon_forecast = oracle_carbon[step + 1 : step + 1 + ctrl.horizon]
        if len(carbon_forecast) == 0:
            carbon_forecast = oracle_carbon[-1:]
        if len(carbon_forecast) < ctrl.horizon:
            pad_len = ctrl.horizon - len(carbon_forecast)
            carbon_forecast = np.concatenate(
                [carbon_forecast, np.repeat(carbon_forecast[-1:], pad_len, axis=0)]
            )

        action = ctrl.act(
            state={"soc": soc_vals},
            forecast=forecast,
            weights=weights,
            carbon_intensity=carbon_forecast.astype(np.float32),
        )
        battery_action = float(action[0])
        full_action = [0.0] * num_actions
        for i, name in enumerate(env.action_names[0]):
            if name == "electrical_storage":
                full_action[i] = battery_action
        obs, reward, terminated, truncated, info = env.step([full_action])
        features = obs_to_features(obs[0], obs_names)
        history_buf.append(features)
        step += 1

    return compute_kpi_from_env(env)


def compute_sensitivity_map(
    schema: str,
    oracle_data_path: str,
    controller_config: dict,
    weights: dict[str, float],
    delta: float = 0.1,
    horizon: int = 24,
    num_channels: int = 3,
) -> np.ndarray:
    """Compute (H, C) sensitivity map via finite-difference perturbation.

    For each (h, c) cell, adds +delta and -delta to the oracle forecast at
    that position, runs the full episode, and measures KPI change.

    Returns:
        sensitivity: shape (horizon, num_channels), absolute KPI sensitivity.
    """
    # Baseline run (unperturbed oracle)
    baseline_kpis = run_oracle_episode(
        schema, oracle_data_path, controller_config, weights
    )
    baseline_cost = baseline_kpis["cost"]

    sensitivity = np.zeros((horizon, num_channels), dtype=np.float64)

    for h in range(horizon):
        for c in range(num_channels):
            # +delta perturbation
            def perturb_plus(forecast, step, _h=h, _c=c, _d=delta):
                forecast[_h, _c] += _d
                return forecast

            kpis_plus = run_oracle_episode(
                schema, oracle_data_path, controller_config, weights,
                forecast_modifier=perturb_plus,
            )

            # -delta perturbation
            def perturb_minus(forecast, step, _h=h, _c=c, _d=delta):
                forecast[_h, _c] -= _d
                return forecast

            kpis_minus = run_oracle_episode(
                schema, oracle_data_path, controller_config, weights,
                forecast_modifier=perturb_minus,
            )

            # Central difference on cost KPI
            sensitivity[h, c] = abs(kpis_plus["cost"] - kpis_minus["cost"]) / (2 * delta)

    # Normalize to [0, 1]
    max_val = sensitivity.max()
    if max_val > 0:
        sensitivity = sensitivity / max_val

    return sensitivity


def main():
    parser = argparse.ArgumentParser(
        description="Channel-horizon perturbation sensitivity analysis"
    )
    parser.add_argument("--schema", type=str, default="citylearn_challenge_2023_phase_1")
    parser.add_argument("--oracle_data", type=str, default="artifacts/forecast_data.npz")
    parser.add_argument("--controller_config", type=str, default="configs/controller.yaml")
    parser.add_argument("--output_dir", type=str, default="reports/cavs/sensitivity")
    parser.add_argument("--delta", type=float, default=0.1, help="Perturbation magnitude")
    parser.add_argument("--weight_cost", type=float, default=None)
    parser.add_argument("--weight_carbon", type=float, default=None)
    parser.add_argument("--weight_peak", type=float, default=None)
    parser.add_argument("--weight_smooth", type=float, default=None)
    args = parser.parse_args()

    with open(args.controller_config) as f:
        controller_config = yaml.safe_load(f)

    weights = controller_config.get("default_weights", {
        "cost": 0.4, "carbon": 0.2, "peak": 0.3, "smooth": 0.1,
    })
    for k in ["cost", "carbon", "peak", "smooth"]:
        override = getattr(args, f"weight_{k}", None)
        if override is not None:
            weights[k] = override

    horizon = controller_config.get("horizon", 24)
    num_channels = len(TARGET_COLS)

    print(f"Computing sensitivity map: {horizon}x{num_channels}, delta={args.delta}")
    sensitivity = compute_sensitivity_map(
        schema=args.schema,
        oracle_data_path=args.oracle_data,
        controller_config=controller_config,
        weights=weights,
        delta=args.delta,
        horizon=horizon,
        num_channels=num_channels,
    )

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    np.save(out_path / "sensitivity_map.npy", sensitivity)

    # Save as JSON for readability
    result = {
        "schema": args.schema,
        "delta": args.delta,
        "horizon": horizon,
        "num_channels": num_channels,
        "sensitivity": sensitivity.tolist(),
    }
    with open(out_path / "sensitivity_map.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Sensitivity map saved to {out_path}")
    print(f"Shape: {sensitivity.shape}, max={sensitivity.max():.4f}, mean={sensitivity.mean():.4f}")


if __name__ == "__main__":
    main()