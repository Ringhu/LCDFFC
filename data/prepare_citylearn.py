"""Extract historical data from CityLearn schema and save as processed CSV/NPZ.

Usage:
    python data/prepare_citylearn.py --schema citylearn_challenge_2023_phase_1 --output_dir artifacts/

The schema can be a built-in dataset name (e.g., 'citylearn_challenge_2023_phase_1')
or a path to a local schema.json file.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


# Features we extract per building (shared features only appear once)
SHARED_FEATURES = [
    "day_type", "hour", "outdoor_dry_bulb_temperature",
    "carbon_intensity", "electricity_pricing",
]

PER_BUILDING_FEATURES = [
    "non_shiftable_load", "solar_generation",
    "electrical_storage_soc", "net_electricity_consumption",
]


def extract_from_schema(schema: str) -> tuple[pd.DataFrame, dict]:
    """Load CityLearn env and extract time-series data by running a zero-action episode.

    Args:
        schema: Built-in dataset name or path to schema.json.

    Returns:
        Tuple of (DataFrame with all features, metadata dict with env info).
    """
    from citylearn.citylearn import CityLearnEnv

    env = CityLearnEnv(schema=schema, central_agent=True)
    num_buildings = len(env.buildings)
    obs_names = env.observation_names[0]  # central_agent: single list
    time_steps = env.time_steps

    # Collect battery info
    battery_info = []
    for b in env.buildings:
        batt = b.electrical_storage
        battery_info.append({
            "capacity": batt.capacity,
            "efficiency": batt.efficiency,
            "nominal_power": batt.nominal_power,
        })

    # Run episode with zero actions to collect observations
    obs_list = env.reset()
    all_obs = [obs_list[0][0]]  # first observation (central_agent returns nested list)

    num_actions = len(env.action_names[0])
    zero_action = [[0.0] * num_actions]

    for step in range(time_steps - 1):
        obs_list, _, terminated, truncated, _ = env.step(zero_action)
        all_obs.append(obs_list[0])
        if terminated or truncated:
            break

    # Convert to array
    obs_array = np.array(all_obs, dtype=np.float32)
    print(f"Collected {obs_array.shape[0]} timesteps, {obs_array.shape[1]} features")

    # Build DataFrame with named columns
    # In central_agent mode, obs_names contains shared + per-building features
    # We need to create unique column names for per-building features
    columns = []
    for name in obs_names:
        if name in [c for c in columns]:
            # Duplicate name -> add building suffix
            count = sum(1 for c in columns if c.startswith(name))
            columns.append(f"{name}_b{count}")
        else:
            columns.append(name)

    df = pd.DataFrame(obs_array, columns=columns)

    # Build metadata
    metadata = {
        "schema": schema,
        "num_buildings": num_buildings,
        "time_steps": obs_array.shape[0],
        "num_features": obs_array.shape[1],
        "battery_info": battery_info,
        "columns": columns,
        "shared_features": [c for c in columns if c in SHARED_FEATURES],
        "stats": {},
    }
    for col in df.columns:
        metadata["stats"][col] = {
            "mean": float(df[col].mean()),
            "std": float(df[col].std()),
            "min": float(df[col].min()),
            "max": float(df[col].max()),
        }

    return df, metadata


def build_forecast_dataset(df: pd.DataFrame, num_buildings: int) -> pd.DataFrame:
    """Build a clean dataset with the features needed for forecasting.

    Extracts shared weather/price features and per-building load/solar.
    Returns a DataFrame suitable for the CityLearnDataset sliding window.
    """
    # Shared features (same for all buildings)
    shared_cols = [c for c in df.columns if c in SHARED_FEATURES]

    # Per-building features: average across buildings for a centralized model
    per_building_cols = {}
    for feat in PER_BUILDING_FEATURES:
        matching = [c for c in df.columns if c == feat or c.startswith(f"{feat}_b")]
        if matching:
            per_building_cols[feat] = matching

    result = df[shared_cols].copy()
    for feat, cols in per_building_cols.items():
        if len(cols) == 1:
            result[feat] = df[cols[0]].values
        else:
            # Average across buildings
            result[f"{feat}_avg"] = df[cols].mean(axis=1).values

    return result


def save_processed(df: pd.DataFrame, forecast_df: pd.DataFrame,
                   metadata: dict, output_dir: str) -> None:
    """Save all processed data to output directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Full raw data
    df.to_csv(output_path / "citylearn_data.csv", index=False)
    np.savez(output_path / "citylearn_data.npz",
             data=df.values, columns=np.array(df.columns.tolist()))

    # Forecast-ready dataset
    forecast_df.to_csv(output_path / "forecast_data.csv", index=False)
    np.savez(output_path / "forecast_data.npz",
             data=forecast_df.values,
             columns=np.array(forecast_df.columns.tolist()))

    # Metadata
    with open(output_path / "data_summary.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Full data: {df.shape} -> {output_path / 'citylearn_data.csv'}")
    print(f"Forecast data: {forecast_df.shape} -> {output_path / 'forecast_data.csv'}")
    print(f"Metadata -> {output_path / 'data_summary.json'}")


def main():
    parser = argparse.ArgumentParser(description="Prepare CityLearn data")
    parser.add_argument("--schema", type=str,
                        default="citylearn_challenge_2023_phase_1",
                        help="Built-in dataset name or path to schema.json")
    parser.add_argument("--output_dir", type=str, default="artifacts/")
    args = parser.parse_args()

    print(f"Extracting data from: {args.schema}")
    df, metadata = extract_from_schema(args.schema)

    forecast_df = build_forecast_dataset(df, metadata["num_buildings"])
    print(f"\nForecast dataset columns: {list(forecast_df.columns)}")

    save_processed(df, forecast_df, metadata, args.output_dir)
    print("\nDone!")


if __name__ == "__main__":
    main()
