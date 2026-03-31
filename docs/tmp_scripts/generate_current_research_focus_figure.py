"""Generate a current-thesis-only research workflow figure for LCDFFC."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


def draw_box(ax, x, y, w, h, title, lines, facecolor):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=facecolor,
        edgecolor="#0f172a",
        linewidth=1.6,
    )
    ax.add_patch(box)
    ax.text(
        x + 0.018,
        y + h - 0.03,
        title,
        ha="left",
        va="top",
        fontsize=10.5,
        weight="bold",
        color="#0f172a",
    )
    ax.text(
        x + 0.018,
        y + h - 0.08,
        "\n".join(lines),
        ha="left",
        va="top",
        fontsize=8.8,
        color="#1f2937",
        linespacing=1.35,
    )


def draw_arrow(ax, x1, y1, x2, y2):
    arrow = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.6,
        color="#334155",
        connectionstyle="arc3,rad=0",
    )
    ax.add_patch(arrow)


def main():
    out_dir = Path("docs/assets/notion")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "lcdffc-current-research-focus-20260331.png"

    fig, ax = plt.subplots(figsize=(16, 5.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    boxes = [
        (
            0.03,
            0.22,
            0.17,
            0.52,
            "1. Research Problem",
            [
                "Average forecast error",
                "is not a reliable proxy",
                "for downstream control KPI.",
            ],
            "#dbeafe",
        ),
        (
            0.23,
            0.22,
            0.17,
            0.52,
            "2. Candidate Models",
            [
                "GRU, PatchTST, TSMixer,",
                "DLinear, Chronos-2,",
                "Moirai2, TimesFM 2.5,",
                "plus myopic / oracle diagnostics.",
            ],
            "#dcfce7",
        ),
        (
            0.43,
            0.22,
            0.17,
            0.52,
            "3. Evaluation Protocol",
            [
                "Run each model through",
                "forecast + qp_carbon control",
                "on 5 scenarios in 2023,",
                "then 3 transfer scenarios in 2022.",
            ],
            "#fde68a",
        ),
        (
            0.63,
            0.22,
            0.17,
            0.52,
            "4. Mechanism Analysis",
            [
                "Measure rank reversals,",
                "channel-horizon sensitivity,",
                "and event-critical errors.",
            ],
            "#fce7f3",
        ),
        (
            0.83,
            0.22,
            0.14,
            0.52,
            "5. Expected Outcome",
            [
                "Show systematic",
                "forecast-control",
                "misalignment, then",
                "test whether CAVS",
                "selects better models",
                "than MSE / MAE.",
            ],
            "#ddd6fe",
        ),
    ]

    for x, y, w, h, title, lines, color in boxes:
        draw_box(ax, x, y, w, h, title, lines, color)

    arrow_y = 0.48
    draw_arrow(ax, 0.20, arrow_y, 0.23, arrow_y)
    draw_arrow(ax, 0.40, arrow_y, 0.43, arrow_y)
    draw_arrow(ax, 0.60, arrow_y, 0.63, arrow_y)
    draw_arrow(ax, 0.80, arrow_y, 0.83, arrow_y)

    ax.text(
        0.5,
        0.92,
        "LCDFFC Current Research Focus",
        ha="center",
        va="top",
        fontsize=18,
        weight="bold",
        color="#0f172a",
    )
    ax.text(
        0.5,
        0.87,
        "Current thesis only: forecast-control misalignment and controller-aware model selection",
        ha="center",
        va="top",
        fontsize=10.5,
        color="#475569",
    )

    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(out_path)


if __name__ == "__main__":
    main()
