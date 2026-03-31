"""Aggregate and compare KPI results from different methods.

Usage:
    python eval/run_all.py --reports_dir reports/
    python eval/run_all.py --reports_dir reports/eval_2022/
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_all_kpis(reports_dir: str) -> dict[str, dict]:
    """Load all *_kpis.json files from a directory."""
    results = {}
    for f in sorted(Path(reports_dir).glob("*_kpis.json")):
        with open(f) as fp:
            data = json.load(fp)
        tag = data.get("tag", f.stem.replace("_kpis", ""))
        results[tag] = data
    return results


def compare(reports_dir: str, output_dir: str | None = None):
    """Load all KPIs and produce comparison table + chart."""
    if output_dir is None:
        output_dir = reports_dir
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    results = load_all_kpis(reports_dir)
    if not results:
        print(f"No *_kpis.json files found in {reports_dir}")
        return

    # Build comparison table
    metrics = ["cost", "carbon", "peak", "ramping"]
    rows = []
    for tag, kpis in results.items():
        row = {"method": tag}
        for m in metrics:
            row[m] = kpis.get(m, float("nan"))
        rows.append(row)

    df = pd.DataFrame(rows)
    print("\n=== KPI Comparison ===")
    print(df.to_string(index=False))

    # Save CSV
    df.to_csv(out / "comparison_table.csv", index=False)

    # Compute relative improvement over the default baseline.
    baseline_candidates = ["zero_action", "myopic_qp"]
    baseline_row = pd.DataFrame()
    baseline_name = None
    for candidate in baseline_candidates:
        candidate_row = df[df["method"].str.contains(candidate, case=False)]
        if not candidate_row.empty:
            baseline_row = candidate_row
            baseline_name = candidate
            break

    if not baseline_row.empty:
        baseline_vals = baseline_row.iloc[0]
        label = baseline_name.replace("_", "-") if baseline_name else "baseline"
        print(f"\n=== Relative to {label} (%) ===")
        for _, row in df.iterrows():
            method_name = row["method"].lower()
            if any(candidate in method_name for candidate in baseline_candidates):
                continue
            improvements = []
            for m in metrics:
                if baseline_vals[m] != 0:
                    pct = (baseline_vals[m] - row[m]) / abs(baseline_vals[m]) * 100
                    improvements.append(f"{m}: {pct:+.2f}%")
                else:
                    improvements.append(f"{m}: N/A")
            print(f"  {row['method']}: {', '.join(improvements)}")

    # Bar chart
    if len(df) >= 2:
        fig, axes = plt.subplots(1, len(metrics), figsize=(4 * len(metrics), 5))
        if len(metrics) == 1:
            axes = [axes]

        colors = plt.cm.Set2(np.linspace(0, 1, len(df)))
        x = np.arange(len(df))

        for ax, m in zip(axes, metrics):
            vals = df[m].values
            bars = ax.bar(x, vals, color=colors)
            ax.set_title(m.capitalize())
            ax.set_xticks(x)
            ax.set_xticklabels(df["method"].values, rotation=45, ha="right", fontsize=8)
            ax.grid(True, alpha=0.3, axis="y")

        fig.suptitle("KPI Comparison", fontsize=14)
        fig.tight_layout()
        fig.savefig(out / "comparison_plot.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"\nPlot saved: {out / 'comparison_plot.png'}")

    print(f"Table saved: {out / 'comparison_table.csv'}")


def main():
    parser = argparse.ArgumentParser(description="Compare KPI results")
    parser.add_argument("--reports_dir", type=str, default="reports/")
    parser.add_argument("--output_dir", type=str, default=None)
    args = parser.parse_args()

    compare(args.reports_dir, args.output_dir)


if __name__ == "__main__":
    main()
