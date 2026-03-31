"""Run CityLearn with a zero-action baseline (no battery control) and record KPIs.

Usage:
    python eval/run_zero_action.py --schema citylearn_challenge_2023_phase_1
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_zero_action_baseline(schema: str, output_dir: str) -> dict:
    """Run CityLearn with zero battery actions and collect metrics.

    CityLearn 2023 buildings have internal default controllers for subsystems
    such as DHW/cooling. With zero battery actions, the district follows its
    default behavior without explicit battery control.

    Args:
        schema: CityLearn dataset name or schema path.
        output_dir: Where to save KPI report.

    Returns:
        Dict of KPI values.
    """
    from citylearn.citylearn import CityLearnEnv

    env = CityLearnEnv(schema=schema, central_agent=True)
    num_actions = len(env.action_names[0])
    zero_action = [[0.0] * num_actions]

    obs = env.reset()
    all_obs = [obs[0][0] if isinstance(obs[0][0], list) else obs[0]]

    terminated = False
    truncated = False
    step = 0

    while not (terminated or truncated):
        obs, reward, terminated, truncated, info = env.step(zero_action)
        all_obs.append(obs[0])
        step += 1

    print(f"Zero-action episode completed: {step} steps")

    total_cost = 0.0
    total_carbon = 0.0
    all_net_loads = []

    for building in env.buildings:
        net_elec = np.array(building.net_electricity_consumption)
        pricing = np.array(building.pricing.electricity_pricing)[:len(net_elec)]
        carbon = np.array(building.carbon_intensity.carbon_intensity)[:len(net_elec)]

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
    }

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    with open(out_path / "zero_action_kpis.json", "w") as f:
        json.dump(kpis, f, indent=2)

    return kpis


def main():
    parser = argparse.ArgumentParser(description="Run zero-action baseline")
    parser.add_argument("--schema", type=str, default="citylearn_challenge_2023_phase_1")
    parser.add_argument("--output_dir", type=str, default="reports/")
    args = parser.parse_args()

    kpis = run_zero_action_baseline(args.schema, args.output_dir)
    print("\nZero-action KPIs:")
    for k, v in kpis.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")


if __name__ == "__main__":
    main()
