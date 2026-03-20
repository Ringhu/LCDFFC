"""Metrics for preference-shift control experiments."""

from __future__ import annotations

from typing import Any

import numpy as np


def compute_episode_kpis(
    district_net_load: np.ndarray,
    prices: np.ndarray,
    carbon_intensity: np.ndarray,
) -> dict[str, float]:
    """Compute episode-level KPI summary from per-step traces."""
    grid_import = np.maximum(district_net_load, 0.0)
    return {
        "cost": float(np.sum(grid_import * prices)),
        "carbon": float(np.sum(grid_import * carbon_intensity)),
        "peak": float(np.max(district_net_load)),
        "ramping": float(np.sum(np.abs(np.diff(district_net_load)))) if len(district_net_load) > 1 else 0.0,
        "avg_net_load": float(np.mean(district_net_load)),
        "num_steps": int(len(district_net_load)),
    }


def compute_segment_metrics(
    district_net_load: np.ndarray,
    prices: np.ndarray,
    carbon_intensity: np.ndarray,
    avg_soc_trace: np.ndarray,
    start_step: int,
    end_step: int,
    regime: dict[str, Any],
) -> dict[str, Any]:
    """Compute per-regime metrics for one segment."""
    start_step = max(int(start_step), 0)
    end_step = min(int(end_step), len(district_net_load))
    segment_load = district_net_load[start_step:end_step]
    segment_prices = prices[start_step:end_step]
    segment_carbon = carbon_intensity[start_step:end_step]
    segment_soc = avg_soc_trace[start_step:end_step]

    if len(segment_load) == 0:
        return {
            "name": regime["name"],
            "start_step": start_step,
            "end_step": end_step,
            "instruction": regime["instruction"],
            "metrics": {},
        }

    metrics = compute_episode_kpis(segment_load, segment_prices, segment_carbon)
    reserve_soc = regime["target_profile"]["constraints"].get("reserve_soc")
    if reserve_soc is None or len(segment_soc) == 0:
        reserve_gap = 0.0
        avg_soc_end = float(segment_soc[-1]) if len(segment_soc) > 0 else None
    else:
        avg_soc_end = float(segment_soc[-1])
        reserve_gap = max(float(reserve_soc) - avg_soc_end, 0.0)

    metrics["avg_soc_end"] = avg_soc_end
    metrics["reserve_gap"] = reserve_gap
    return {
        "name": regime["name"],
        "start_step": start_step,
        "end_step": end_step,
        "instruction": regime["instruction"],
        "target_weights": regime["target_profile"]["weights"],
        "target_constraints": regime["target_profile"]["constraints"],
        "preference_vector": regime["preference_vector"],
        "metrics": metrics,
    }


def compute_preference_score(
    segment_metrics: dict[str, Any],
    reference_metrics: dict[str, float],
) -> float:
    """Lower-is-better segment score normalized by a reference run."""
    metrics = segment_metrics["metrics"]
    weights = segment_metrics["target_weights"]
    ref_cost = max(float(reference_metrics["cost"]), 1e-8)
    ref_carbon = max(float(reference_metrics["carbon"]), 1e-8)
    ref_peak = max(float(reference_metrics["peak"]), 1e-8)

    score = (
        weights["cost"] * float(metrics["cost"]) / ref_cost
        + weights["carbon"] * float(metrics["carbon"]) / ref_carbon
        + weights["peak"] * float(metrics["peak"]) / ref_peak
    )

    reserve_soc = segment_metrics["target_constraints"].get("reserve_soc")
    if reserve_soc is not None and reserve_soc > 0:
        score += 0.2 * float(metrics.get("reserve_gap", 0.0)) / float(reserve_soc)

    return float(score)
