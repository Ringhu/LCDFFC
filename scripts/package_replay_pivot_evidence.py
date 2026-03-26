from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Package replay-pivot evidence summary")
    parser.add_argument("--r201", required=True)
    parser.add_argument("--r202", required=True)
    parser.add_argument("--offline_prior_summary", required=True)
    parser.add_argument("--output_json", required=True)
    parser.add_argument("--output_md", required=True)
    args = parser.parse_args()

    r201 = load_json(args.r201)
    r202 = load_json(args.r202)
    offline = load_json(args.offline_prior_summary)

    solved_fraction = 0.0
    details = offline.get("details", {})
    import_dual = details.get("import_dual", [])
    if import_dual:
        nonzero = sum(1 for x in import_dual if abs(x) > 1e-12)
        solved_fraction = nonzero / len(import_dual)

    prior = offline.get("prior_matrix", [])
    prior_nonzero = any(any(abs(v) > 1e-12 for v in row) for row in prior) if prior else False

    summary = {
        "oracle_alignment_pass": bool(r201.get("pass", False)),
        "raw_csft_utility_pass": bool(r202.get("pass", False)),
        "raw_csft_top_decile_ratio": float(r202.get("ratio", float("nan"))),
        "offline_dual_prior_nonzero": bool(prior_nonzero),
        "offline_dual_solved_fraction": float(solved_fraction),
        "offline_dual_manual_horizon_corr": offline.get("manual_horizon_corr"),
        "offline_dual_manual_horizon_cosine": offline.get("manual_horizon_cosine"),
        "frozen_conclusion": (
            "raw-CSFT is falsified in the current setting; oracle alignment is valid; "
            "offline train-window dual prior extraction did not produce a usable prior"
        ),
    }

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2))

    md = f"""# Replay Pivot Frozen Evidence

## R201
- PASS: {r201.get('pass')}
- max_abs_error: {r201.get('max_abs_error')}

## R202
- PASS: {r202.get('pass')}
- raw-CSFT top-decile ratio: {r202.get('ratio')}
- threshold: {r202.get('threshold')}

## Offline Dual Prior Extraction
- prior nonzero: {prior_nonzero}
- solved fraction: {solved_fraction}
- manual horizon corr: {offline.get('manual_horizon_corr')}
- manual horizon cosine: {offline.get('manual_horizon_cosine')}

## Formal Conclusion
- {summary['frozen_conclusion']}
"""
    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
