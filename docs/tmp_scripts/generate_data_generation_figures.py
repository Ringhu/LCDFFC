"""Generate data-generation figures for the documentation.

Outputs:
  - docs/assets/data_generation_sample.png
  - docs/assets/data_generation_flow.svg
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PROCESSED_COLORS = {
    "electricity_pricing": "#2563eb",
    "non_shiftable_load_avg": "#dc2626",
    "solar_generation_avg": "#f59e0b",
}


def _load_data(forecast_data_path: str, data_summary_path: str) -> tuple[np.ndarray, list[str], dict]:
    loaded = np.load(forecast_data_path, allow_pickle=True)
    data = loaded["data"].astype(np.float32)
    columns = [str(c) for c in loaded["columns"].tolist()]
    with open(data_summary_path) as f:
        summary = json.load(f)
    return data, columns, summary


def make_sample_figure(
    forecast_data_path: str,
    data_summary_path: str,
    output_path: str,
    history_len: int = 24,
    horizon: int = 24,
) -> None:
    data, columns, summary = _load_data(forecast_data_path, data_summary_path)
    col_idx = {name: i for i, name in enumerate(columns)}

    price = data[:, col_idx["electricity_pricing"]]
    load = data[:, col_idx["non_shiftable_load_avg"]]
    solar = data[:, col_idx["solar_generation_avg"]]

    week = min(168, len(data))
    start = min(96, max(0, len(data) - (history_len + horizon + 1)))
    history_slice = slice(start, start + history_len)
    future_slice = slice(start + history_len, start + history_len + horizon)
    window_x = np.arange(start, start + history_len + horizon)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes = axes.ravel()

    series_specs = [
        ("electricity_pricing", price, "Price", axes[0]),
        ("non_shiftable_load_avg", load, "Load", axes[1]),
        ("solar_generation_avg", solar, "Solar", axes[2]),
    ]

    for name, values, title, ax in series_specs:
        ax.plot(np.arange(week), values[:week], color=PROCESSED_COLORS[name], linewidth=2.0)
        ax.set_title(f"{title} Sample (first {week} steps)")
        ax.set_xlabel("Time step")
        ax.grid(True, alpha=0.25)
        ax.set_xlim(0, week - 1)

    ax = axes[3]
    ax.axvspan(history_slice.start, history_slice.stop - 1, color="#bfdbfe", alpha=0.55, label=f"History ({history_len})")
    ax.axvspan(future_slice.start, future_slice.stop - 1, color="#fed7aa", alpha=0.55, label=f"Future target ({horizon})")
    ax.plot(window_x, price[window_x], color=PROCESSED_COLORS["electricity_pricing"], linewidth=2.0, label="Price")
    ax.plot(window_x, load[window_x], color=PROCESSED_COLORS["non_shiftable_load_avg"], linewidth=2.0, label="Load")
    ax.plot(window_x, solar[window_x], color=PROCESSED_COLORS["solar_generation_avg"], linewidth=2.0, label="Solar")
    ax.axvline(history_slice.stop - 0.5, color="#111827", linestyle="--", linewidth=1.5)
    ax.set_title("Example Sliding-Window Training Sample")
    ax.set_xlabel("Global time step")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=9, ncol=2)

    schema = summary.get("schema", "unknown_schema")
    num_buildings = summary.get("num_buildings", "unknown")
    time_steps = summary.get("time_steps", len(data))
    fig.suptitle(
        f"Processed Forecast Data Example | schema={schema} | buildings={num_buildings} | steps={time_steps}",
        fontsize=14,
    )
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _draw_box(ax, xy, wh, title, body_lines, facecolor, title_size=11, body_size=9.5):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.5,
        edgecolor="#0f172a",
        facecolor=facecolor,
    )
    ax.add_patch(patch)
    ax.text(
        x + 0.022,
        y + h - 0.028,
        title,
        fontsize=title_size,
        weight="bold",
        va="top",
        ha="left",
        color="#0f172a",
    )
    ax.text(
        x + 0.022,
        y + h - 0.075,
        "\n".join(body_lines),
        fontsize=body_size,
        va="top",
        ha="left",
        color="#1f2937",
        linespacing=1.35,
    )


def _draw_arrow(ax, start, end):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.5,
        color="#334155",
        connectionstyle="arc3,rad=0.0",
    )
    ax.add_patch(arrow)


def make_flow_figure(output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 10))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    _draw_box(
        ax,
        (0.12, 0.77),
        (0.76, 0.12),
        "1. Scenario Selection",
        [
            "Use a challenge scenario or local schema.json path.",
            "For offline runs, prefer the cached local schema path.",
        ],
        "#dbeafe",
    )
    _draw_box(
        ax,
        (0.12, 0.58),
        (0.76, 0.12),
        "2. Zero-Action CityLearn Rollout",
        [
            "Create CityLearnEnv(..., central_agent=True).",
            "Call reset(), then step through the full episode with zero battery actions.",
        ],
        "#dcfce7",
    )
    _draw_box(
        ax,
        (0.12, 0.39),
        (0.76, 0.12),
        "3. Raw Observation Archive",
        [
            "Save all collected observations as citylearn_data.csv and citylearn_data.npz.",
            "This keeps shared features and per-building features before aggregation.",
        ],
        "#fde68a",
    )
    _draw_box(
        ax,
        (0.12, 0.20),
        (0.76, 0.12),
        "4. Processed Forecast Dataset",
        [
            "Keep shared features and average selected per-building series.",
            "Write forecast_data.csv and forecast_data.npz with the fixed 9-column format.",
        ],
        "#fce7f3",
    )
    _draw_box(
        ax,
        (0.06, 0.02),
        (0.39, 0.14),
        "5A. Sliding Windows + Splits",
        [
            "Chronological 70/15/15 split",
            "24-step history -> 24-step future target",
            "Save norm_stats.npz from train split",
        ],
        "#cffafe",
        title_size=10.5,
        body_size=8.4,
    )
    _draw_box(
        ax,
        (0.53, 0.02),
        (0.39, 0.14),
        "5B. Model Training / Evaluation",
        [
            "Train forecasting backbones with",
            "scripts/train_forecaster.py",
            "run_controller.py reuses the same 9-column feature order",
        ],
        "#ddd6fe",
        title_size=10.5,
        body_size=8.4,
    )

    arrows = [
        ((0.50, 0.77), (0.50, 0.70)),
        ((0.50, 0.58), (0.50, 0.51)),
        ((0.50, 0.39), (0.50, 0.32)),
        ((0.30, 0.20), (0.25, 0.16)),
        ((0.70, 0.20), (0.75, 0.16)),
    ]

    for start, end in arrows:
        _draw_arrow(ax, start, end)

    ax.text(
        0.5,
        0.97,
        "CityLearn Data Generation and Training Data Pipeline",
        ha="center",
        va="top",
        fontsize=16,
        weight="bold",
        color="#0f172a",
    )
    ax.text(
        0.5,
        0.94,
        "Current LCDFFC data path: zero-action rollout -> raw observations -> processed forecast data -> sliding-window supervision.",
        ha="center",
        va="top",
        fontsize=10,
        color="#334155",
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="svg", bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate data-generation documentation figures")
    parser.add_argument("--forecast-data", default="artifacts/forecast_data.npz")
    parser.add_argument("--data-summary", default="artifacts/data_summary.json")
    parser.add_argument("--output-dir", default="docs/assets")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    make_sample_figure(
        forecast_data_path=args.forecast_data,
        data_summary_path=args.data_summary,
        output_path=str(output_dir / "data_generation_sample.png"),
    )
    make_flow_figure(str(output_dir / "data_generation_flow.svg"))

    print(f"Wrote {output_dir / 'data_generation_sample.png'}")
    print(f"Wrote {output_dir / 'data_generation_flow.svg'}")


if __name__ == "__main__":
    main()
