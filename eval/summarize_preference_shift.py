"""Aggregate preference-shift experiment outputs into comparable scores."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.preference_shift_metrics import compute_preference_score


def load_segments(path: Path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description="Summarize preference-shift experiment results")
    parser.add_argument("--results_dir", type=str, required=True)
    parser.add_argument("--reference_tag", type=str, default="fixed_balanced")
    parser.add_argument("--fixed_tags", type=str, nargs="+", required=True)
    parser.add_argument("--target_tags", type=str, nargs="+", required=True)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    reference_segments = load_segments(results_dir / f"{args.reference_tag}_segments.json")
    reference_by_name = {seg["name"]: seg["metrics"] for seg in reference_segments}

    fixed_scores_by_regime: dict[str, list[tuple[str, float]]] = {}
    run_rows = []
    for tag in args.fixed_tags + args.target_tags:
        segments = load_segments(results_dir / f"{tag}_segments.json")
        segment_scores = []
        for seg in segments:
            ref = reference_by_name[seg["name"]]
            score = compute_preference_score(seg, ref)
            seg["preference_score"] = score
            segment_scores.append((seg["name"], score))
            if tag in args.fixed_tags:
                fixed_scores_by_regime.setdefault(seg["name"], []).append((tag, score))
        avg_score = sum(score for _, score in segment_scores) / max(len(segment_scores), 1)
        run_rows.append({"tag": tag, "avg_preference_score": avg_score, "segment_scores": dict(segment_scores)})

    best_fixed_by_regime = {
        regime: min(scores, key=lambda item: item[1]) for regime, scores in fixed_scores_by_regime.items()
    }

    for row in run_rows:
        regrets = {}
        for regime, score in row["segment_scores"].items():
            best_tag, best_score = best_fixed_by_regime[regime]
            regrets[regime] = score - best_score
        row["regret_to_best_fixed"] = regrets
        row["avg_regret_to_best_fixed"] = sum(regrets.values()) / max(len(regrets), 1)

    summary = {
        "reference_tag": args.reference_tag,
        "best_fixed_by_regime": {
            regime: {"tag": tag, "score": score} for regime, (tag, score) in best_fixed_by_regime.items()
        },
        "runs": run_rows,
    }

    output_path = Path(args.output) if args.output is not None else results_dir / "preference_shift_summary.json"
    output_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
