"""Run CityLearn with forecast + QP controller and record KPIs.

Usage:
    python eval/run_controller.py --schema citylearn_challenge_2023_phase_1
    python eval/run_controller.py --checkpoint artifacts/checkpoints/gru_spo_best.pt --tag spo
    python eval/run_controller.py --forecast_mode oracle --oracle_data artifacts/forecast_data.npz
"""

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
from data.dataset import CityLearnDataset
from models.factory import build_forecaster


# Observation name -> index mapping for CityLearn 2023 Phase 1 central_agent
# These are the shared features that appear first in the observation vector
OBS_SHARED = {
    "day_type": 0,
    "hour": 1,
    "outdoor_dry_bulb_temperature": 2,
    "carbon_intensity": 14,
    "electricity_pricing": 21,
}

# Per-building features (building 0 offsets in central_agent obs)
OBS_BUILDING_0 = {
    "non_shiftable_load": 16,
    "solar_generation": 17,
    "electrical_storage_soc": 19,
    "net_electricity_consumption": 20,
}

TARGET_COLS = [4, 5, 6]


def obs_to_features(obs: list | np.ndarray, obs_names: list[str]) -> np.ndarray:
    """Extract the 9 forecast features from a CityLearn observation.

    Returns array matching forecast_data.npz columns:
        [day_type, hour, temperature, carbon_intensity, electricity_pricing,
         non_shiftable_load_avg, solar_generation_avg, electrical_storage_soc_avg,
         net_electricity_consumption_avg]
    """
    obs_flat = np.array(obs).flatten()

    # Build name->index mapping from obs_names
    name_to_idx = {}
    for i, name in enumerate(obs_names):
        if name not in name_to_idx:
            name_to_idx[name] = []
        name_to_idx[name].append(i)

    def get_val(name, avg=False):
        indices = name_to_idx.get(name, [])
        if not indices:
            return 0.0
        vals = [obs_flat[i] for i in indices]
        return float(np.mean(vals)) if avg else float(vals[0])

    return np.array([
        get_val("day_type"),
        get_val("hour"),
        get_val("outdoor_dry_bulb_temperature"),
        get_val("carbon_intensity"),
        get_val("electricity_pricing"),
        get_val("non_shiftable_load", avg=True),
        get_val("solar_generation", avg=True),
        get_val("electrical_storage_soc", avg=True),
        get_val("net_electricity_consumption", avg=True),
    ], dtype=np.float32)


def load_oracle_targets(path: str, target_cols: list[int] | None = None) -> np.ndarray:
    """Load oracle future targets from prepared forecast data."""
    cols = TARGET_COLS if target_cols is None else target_cols
    loaded = np.load(path, allow_pickle=True)
    return loaded["data"][:, cols].astype(np.float32)


def get_battery_params(env) -> dict[str, list[float]]:
    """Extract per-building battery parameters from a CityLearn environment."""
    capacities = []
    nominal_powers = []
    efficiencies = []
    soc_mins = []
    soc_maxs = []

    for building in env.buildings:
        battery = building.electrical_storage
        capacities.append(float(battery.capacity))
        nominal_powers.append(float(battery.nominal_power))
        efficiencies.append(float(battery.efficiency))
        soc_mins.append(float(1.0 - battery.depth_of_discharge))
        soc_maxs.append(1.0)

    return {
        "capacity": capacities,
        "nominal_power": nominal_powers,
        "efficiency": efficiencies,
        "soc_min": soc_mins,
        "soc_max": soc_maxs,
    }


def get_current_socs(env) -> list[float]:
    """Read each building battery's current SOC at the environment time step."""
    soc_index = max(env.time_step - 1, 0)
    return [
        float(building.electrical_storage.soc[soc_index])
        for building in env.buildings
    ]


def build_oracle_forecast(
    oracle_targets: np.ndarray,
    current_step: int,
    horizon: int,
) -> np.ndarray:
    """Slice future targets from the prepared oracle time series.

    Forecasting at step ``t`` should use future rows starting at ``t + 1``.
    If the remaining sequence is shorter than ``horizon``, pad with the last
    available row so the controller always receives a fixed-shape forecast.
    """
    start = current_step + 1
    end = start + horizon
    future = oracle_targets[start:end]

    if len(future) == 0:
        future = oracle_targets[-1:]

    if len(future) < horizon:
        pad = np.repeat(future[-1:], horizon - len(future), axis=0)
        future = np.concatenate([future, pad], axis=0)

    return future.astype(np.float32)


def build_myopic_forecast(current_features: np.ndarray, horizon: int) -> np.ndarray:
    """Repeat the current observed target values across the planning horizon."""
    current_targets = current_features[TARGET_COLS].astype(np.float32)
    return np.repeat(current_targets[None, :], horizon, axis=0)


def run_forecast_control(
    schema: str,
    checkpoint: str,
    norm_stats_path: str,
    forecast_config: dict,
    controller_config: dict,
    weights: dict[str, float],
    output_dir: str,
    tag: str = "forecast_qp",
    device: str = "cpu",
    forecast_mode: str = "learned",
    oracle_data_path: str = "artifacts/forecast_data.npz",
    constraints: dict | None = None,
) -> dict:
    """Run the forecast-then-control pipeline on CityLearn.

    Args:
        schema: CityLearn dataset name.
        checkpoint: Path to GRU model checkpoint.
        norm_stats_path: Path to normalization stats.
        forecast_config: Model config dict.
        controller_config: Controller config dict.
        weights: QP objective weights.
        output_dir: Where to save results.
        tag: Filename tag for results.
        device: torch device.
        forecast_mode: One of ``learned``, ``oracle``, or ``myopic``.
        oracle_data_path: Prepared data path used by oracle mode.
        constraints: Optional controller constraints such as reserve_soc.

    Returns:
        Dict of KPI values.
    """
    from citylearn.citylearn import CityLearnEnv

    model_cfg = forecast_config["model"]
    horizon = model_cfg["horizon"]
    constraints = constraints or {}
    mean = None
    std = None
    model = None

    if forecast_mode == "learned":
        norm_stats = np.load(norm_stats_path)
        mean, std = norm_stats["mean"], norm_stats["std"]

        model = build_forecaster(
            model_cfg,
            input_dim=len(mean),
            output_dim=model_cfg["output_dim"],
        ).to(device)
        model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
        model.eval()
    elif forecast_mode == "oracle":
        oracle_targets = load_oracle_targets(oracle_data_path)
    elif forecast_mode == "myopic":
        oracle_targets = None
    else:
        raise ValueError(f"Unsupported forecast_mode: {forecast_mode}")

    # CityLearn env
    env = CityLearnEnv(schema=schema, central_agent=True)
    obs_names = env.observation_names[0]
    num_actions = len(env.action_names[0])
    num_buildings = len(env.buildings)
    history_len = model_cfg.get("history_len", 24)
    battery_params = get_battery_params(env)

    # Controller
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

    obs = env.reset()
    features = obs_to_features(obs[0][0] if isinstance(obs[0][0], list) else obs[0], obs_names)

    # History buffer
    history_buf = deque([features.copy() for _ in range(history_len)], maxlen=history_len)

    terminated = False
    truncated = False
    step = 0
    actions_log = []

    while not (terminated or truncated):
        history_arr = np.array(history_buf)
        current_features = history_arr[-1]

        if forecast_mode == "learned":
            history_norm = (history_arr - mean) / std
            history_tensor = torch.tensor(
                history_norm, dtype=torch.float32
            ).unsqueeze(0).to(device)

            with torch.no_grad():
                pred_norm = model(history_tensor).cpu().numpy()[0]

            qp_forecast = pred_norm * std[TARGET_COLS] + mean[TARGET_COLS]
        elif forecast_mode == "oracle":
            qp_forecast = build_oracle_forecast(oracle_targets, step, ctrl.horizon)
        else:
            qp_forecast = build_myopic_forecast(current_features, ctrl.horizon)

        # The same normalized action is broadcast to all buildings, so the
        # controller tracks each battery's SOC separately.
        soc_vals = get_current_socs(env)

        # Get action from controller
        action = ctrl.act(
            state={"soc": soc_vals},
            forecast=qp_forecast,
            weights=weights,
            constraints=constraints,
        )
        battery_action = float(action[0])

        # Build full action vector: set electrical_storage actions only
        action_names = env.action_names[0]
        full_action = [0.0] * num_actions
        for i, name in enumerate(action_names):
            if name == "electrical_storage":
                full_action[i] = battery_action
        full_action = [full_action]

        obs, reward, terminated, truncated, info = env.step(full_action)
        features = obs_to_features(obs[0], obs_names)
        history_buf.append(features)
        actions_log.append(battery_action)
        step += 1

    print(f"Episode completed: {step} steps")

    # Extract KPIs
    total_cost = 0.0
    total_carbon = 0.0
    all_net_loads = []

    for b in env.buildings:
        net_elec = np.array(b.net_electricity_consumption)
        pricing = np.array(b.pricing.electricity_pricing)[:len(net_elec)]
        carbon = np.array(b.carbon_intensity.carbon_intensity)[:len(net_elec)]

        total_cost += float(np.sum(np.maximum(net_elec, 0) * pricing))
        total_carbon += float(np.sum(np.maximum(net_elec, 0) * carbon))
        all_net_loads.append(net_elec)

    district_net_load = np.sum(all_net_loads, axis=0)

    kpis = {
        "cost": total_cost,
        "carbon": total_carbon,
        "peak": float(np.max(district_net_load)),
        "ramping": float(np.sum(np.abs(np.diff(district_net_load)))),
        "avg_net_load": float(np.mean(district_net_load)),
        "num_steps": step,
        "tag": tag,
    }

    # Save
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    with open(out_path / f"{tag}_kpis.json", "w") as f:
        json.dump(kpis, f, indent=2)

    # Save action trajectory
    np.save(out_path / f"{tag}_actions.npy", np.array(actions_log))

    return kpis


def main():
    parser = argparse.ArgumentParser(description="Run forecast-control system")
    parser.add_argument("--schema", type=str, default="citylearn_challenge_2023_phase_1")
    parser.add_argument("--checkpoint", type=str, default="artifacts/checkpoints/gru_mse_best.pt")
    parser.add_argument("--norm_stats", type=str, default="artifacts/norm_stats.npz")
    parser.add_argument("--forecast_config", type=str, default="configs/forecast.yaml")
    parser.add_argument("--controller_config", type=str, default="configs/controller.yaml")
    parser.add_argument("--output_dir", type=str, default="reports/")
    parser.add_argument("--tag", type=str, default="forecast_qp")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument(
        "--forecast_mode",
        type=str,
        default="learned",
        choices=["learned", "oracle", "myopic"],
    )
    parser.add_argument("--oracle_data", type=str, default="artifacts/forecast_data.npz")
    parser.add_argument("--weight_cost", type=float, default=None)
    parser.add_argument("--weight_carbon", type=float, default=None)
    parser.add_argument("--weight_peak", type=float, default=None)
    parser.add_argument("--weight_smooth", type=float, default=None)
    parser.add_argument("--reserve_soc", type=float, default=None)
    args = parser.parse_args()

    with open(args.forecast_config) as f:
        forecast_config = yaml.safe_load(f)
    with open(args.controller_config) as f:
        controller_config = yaml.safe_load(f)

    weights = controller_config.get("default_weights", {
        "cost": 0.4, "carbon": 0.2, "peak": 0.3, "smooth": 0.1,
    })
    overrides = {
        "cost": args.weight_cost,
        "carbon": args.weight_carbon,
        "peak": args.weight_peak,
        "smooth": args.weight_smooth,
    }
    weights = {
        key: value if overrides[key] is None else overrides[key]
        for key, value in weights.items()
    }
    constraints = {}
    if args.reserve_soc is not None:
        constraints["reserve_soc"] = args.reserve_soc

    kpis = run_forecast_control(
        schema=args.schema,
        checkpoint=args.checkpoint,
        norm_stats_path=args.norm_stats,
        forecast_config=forecast_config,
        controller_config=controller_config,
        weights=weights,
        output_dir=args.output_dir,
        tag=args.tag,
        device=args.device,
        forecast_mode=args.forecast_mode,
        oracle_data_path=args.oracle_data,
        constraints=constraints,
    )

    print(f"\n{args.tag} KPIs:")
    for k, v in kpis.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")


if __name__ == "__main__":
    main()
