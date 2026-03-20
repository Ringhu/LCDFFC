"""Analyze segment-level gaps between preference-shift routing runs.

Inputs:
    - ``--results_dir``: directory containing ``*_routes.json`` traces
    - ``--summary_path``: summary JSON from ``eval/summarize_preference_shift.py``
    - ``--target_tag`` / ``--compare_tags``: run tags to compare

Outputs:
    - by default writes ``{results_dir}/{target_tag}_gap_analysis.json``
    - also prints the same JSON to stdout
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text())


def summarize_routes(routes: list[dict]) -> dict[str, dict]:
    by_regime: dict[str, list[dict]] = {}
    for row in routes:
        by_regime.setdefault(row["regime"], []).append(row)

    summary: dict[str, dict] = {}
    for regime, rows in by_regime.items():
        weight_keys = ("cost", "carbon", "peak", "smooth")
        avg_weights = {
            key: sum(float(row["weights"][key]) for row in rows) / max(len(rows), 1)
            for key in weight_keys
        }
        reserve_vals = [row["constraints"].get("reserve_soc") for row in rows if row["constraints"] is not None]
        reserve_nonnull = [float(x) for x in reserve_vals if x is not None]
        summary[regime] = {
            "num_steps": len(rows),
            "num_corrupted": sum(bool(row.get("corrupted", False)) for row in rows),
            "num_fallback_used": sum(bool(row.get("fallback_used", False)) for row in rows),
            "avg_weights": avg_weights,
            "avg_reserve_soc": (
                sum(reserve_nonnull) / len(reserve_nonnull) if reserve_nonnull else None
            ),
        }
    return summary


def build_comparison(summary: dict, target_tag: str, compare_tags: list[str]) -> dict[str, object]:
    runs = {row["tag"]: row for row in summary["runs"]}
    target = runs[target_tag]
    comparison_rows = []
    for tag in compare_tags:
        row = runs[tag]
        segment_delta = {
            regime: float(row["segment_scores"][regime]) - float(target["segment_scores"][regime])
            for regime in target["segment_scores"]
        }
        comparison_rows.append(
            {
                "tag": tag,
                "avg_preference_score": row["avg_preference_score"],
                "avg_score_delta_vs_target": float(row["avg_preference_score"]) - float(target["avg_preference_score"]),
                "avg_regret_to_best_fixed": row.get("avg_regret_to_best_fixed"),
                "avg_regret_to_best_single_fixed": row.get("avg_regret_to_best_single_fixed"),
                "segment_score_delta_vs_target": segment_delta,
            }
        )
    return {
        "target_tag": target_tag,
        "target_avg_preference_score": target["avg_preference_score"],
        "target_avg_regret_to_best_fixed": target.get("avg_regret_to_best_fixed"),
        "target_avg_regret_to_best_single_fixed": target.get("avg_regret_to_best_single_fixed"),
        "comparisons": comparison_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze preference-shift gaps at segment level")
    parser.add_argument("--results_dir", type=str, required=True)
    parser.add_argument("--summary_path", type=str, required=True)
    parser.add_argument("--target_tag", type=str, required=True)
    parser.add_argument("--compare_tags", type=str, nargs="+", required=True)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    summary = load_json(Path(args.summary_path))
    output = build_comparison(summary, args.target_tag, args.compare_tags)

    route_stats = {}
    for tag in [args.target_tag, *args.compare_tags]:
        routes = load_json(results_dir / f"{tag}_routes.json")
        route_stats[tag] = summarize_routes(routes)
    output["route_stats"] = route_stats

    output_path = Path(args.output) if args.output is not None else results_dir / f"{args.target_tag}_gap_analysis.json"
    output_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
