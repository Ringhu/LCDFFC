"""Multi-model CAVS validation harness.

Wraps existing run_controller.py in a sweep across models and scenarios,
collects forecast metrics + control KPIs + CAVS scores, and outputs a
JSON comparison table.

Usage:
    python eval/run_cavs_validation.py --help
    python eval/run_cavs_validation.py --config configs/cavs.yaml
    python eval/run_cavs_validation.py --config configs/cavs.yaml --dry_run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from eval.cavs_scoring import compare_selection_strategies, compute_cavs, rank_models_by_cavs


def load_kpis(path: str) -> dict[str, float]:
    """Load KPIs from a JSON file."""
    with open(path) as f:
        return json.load(f)


def run_single_model(
    model_cfg: dict,
    schema: str,
    output_dir: str,
    device: str = "cpu",
) -> dict[str, float]:
    """Run a single model through the forecast-control pipeline.

    Delegates to eval/run_controller.py's run_forecast_control().
    """
    from eval.run_controller import run_forecast_control

    forecast_config_path = model_cfg.get("forecast_config", "configs/forecast.yaml")
    controller_config_path = model_cfg.get("controller_config", "configs/controller.yaml")

    with open(forecast_config_path) as f:
        forecast_config = yaml.safe_load(f)
    with open(controller_config_path) as f:
        controller_config = yaml.safe_load(f)

    weights = controller_config.get("default_weights", {
        "cost": 0.4, "carbon": 0.2, "peak": 0.3, "smooth": 0.1,
    })

    tag = model_cfg.get("tag", "model")
    forecast_mode = model_cfg.get("forecast_mode", "learned")

    kpis = run_forecast_control(
        schema=schema,
        checkpoint=model_cfg.get("checkpoint", ""),
        norm_stats_path=model_cfg.get("norm_stats", "artifacts/norm_stats.npz"),
        forecast_config=forecast_config,
        controller_config=controller_config,
        weights=weights,
        output_dir=output_dir,
        tag=tag,
        device=device,
        forecast_mode=forecast_mode,
        oracle_data_path=model_cfg.get("oracle_data", "artifacts/forecast_data.npz"),
    )
    return kpis


def run_sweep(config: dict, dry_run: bool = False) -> dict:
    """Run full CAVS validation sweep.

    Args:
        config: Loaded cavs.yaml configuration.
        dry_run: If True, print what would run without executing.

    Returns:
        Dict with per-scenario results and selection comparisons.
    """
    models = config["models"]
    scenarios = config["scenarios"]
    device = config.get("device", "cpu")
    output_base = config.get("output_dir", "reports/cavs")
    ref_model = config.get("reference_model", "myopic_qp")

    all_results = {}

    for scenario in scenarios:
        scenario_name = scenario if isinstance(scenario, str) else scenario["name"]
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario_name}")
        print(f"{'='*60}")

        scenario_results = {}
        output_dir = str(Path(output_base) / scenario_name)

        for model_cfg in models:
            model_name = model_cfg["name"]
            if dry_run:
                print(f"  [DRY RUN] Would run: {model_name} on {scenario_name}")
                continue

            print(f"  Running: {model_name}...")
            try:
                kpis = run_single_model(
                    model_cfg, scenario_name, output_dir, device
                )
                scenario_results[model_name] = kpis
                print(f"    cost={kpis['cost']:.2f}, carbon={kpis['carbon']:.2f}")
            except Exception as e:
                print(f"    FAILED: {e}")
                scenario_results[model_name] = {"error": str(e)}

        if not dry_run and ref_model in scenario_results:
            ref_kpis = scenario_results[ref_model]
            comparison = compare_selection_strategies(
                scenario_results, ref_kpis
            )
            scenario_results["_selection_comparison"] = comparison

        all_results[scenario_name] = scenario_results

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Multi-model CAVS validation harness"
    )
    parser.add_argument(
        "--config", type=str, default="configs/cavs.yaml",
        help="Path to CAVS sweep configuration",
    )
    parser.add_argument(
        "--dry_run", action="store_true",
        help="Print what would run without executing",
    )
    parser.add_argument(
        "--output_dir", type=str, default=None,
        help="Override output directory from config",
    )
    parser.add_argument(
        "--device", type=str, default=None,
        help="Override device from config",
    )
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    if args.output_dir:
        config["output_dir"] = args.output_dir
    if args.device:
        config["device"] = args.device

    results = run_sweep(config, dry_run=args.dry_run)

    if not args.dry_run:
        out_path = Path(config.get("output_dir", "reports/cavs"))
        out_path.mkdir(parents=True, exist_ok=True)
        with open(out_path / "cavs_comparison.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {out_path / 'cavs_comparison.json'}")


if __name__ == "__main__":
    main()
