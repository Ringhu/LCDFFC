"""CAVS: Controller-Aware Validation Score for forecast model selection.

CAVS weights forecast errors by controller sensitivity, so that errors on
channels/horizons the QP cares about count more than errors on flat periods.
"""

from __future__ import annotations

import numpy as np


# Default KPI weights matching controller.yaml default_weights
DEFAULT_KPI_WEIGHTS = {"cost": 0.4, "carbon": 0.2, "peak": 0.3, "ramping": 0.1}


def compute_cavs(
    kpis: dict[str, float],
    ref_kpis: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Weighted relative improvement over reference (e.g. RBC) KPIs.

    CAVS(model) = sum_k w_k * (ref_k - model_k) / |ref_k|

    Positive CAVS = model is better than reference on weighted KPIs.
    """
    weights = weights or DEFAULT_KPI_WEIGHTS
    score = 0.0
    for k, w in weights.items():
        if k not in kpis or k not in ref_kpis:
            continue
        ref_val = ref_kpis[k]
        if abs(ref_val) < 1e-12:
            continue
        score += w * (ref_val - kpis[k]) / abs(ref_val)
    return score


def compute_cavs_sensitivity(
    forecast_errors: np.ndarray,
    sensitivity_map: np.ndarray,
) -> float:
    """Sensitivity-weighted mean absolute forecast error.

    Args:
        forecast_errors: shape (N, H, C) — absolute errors per window/horizon/channel
        sensitivity_map: shape (H, C) — controller sensitivity weights

    Returns:
        Scalar CAVS-global score (lower = better forecast for control).
    """
    if forecast_errors.ndim == 2:
        # (H, C) single window
        return float(np.mean(sensitivity_map * forecast_errors))
    # (N, H, C) multiple windows
    weighted = forecast_errors * sensitivity_map[None, :, :]
    return float(np.mean(weighted))


def rank_models_by_cavs(
    model_results: dict[str, dict[str, float]],
    ref_kpis: dict[str, float],
    weights: dict[str, float] | None = None,
) -> list[tuple[str, float]]:
    """Rank all models by CAVS score (descending — higher is better).

    Args:
        model_results: {model_name: {kpi_name: value}}
        ref_kpis: reference KPIs (e.g. from RBC baseline)
        weights: KPI weights for CAVS computation

    Returns:
        List of (model_name, cavs_score) sorted descending.
    """
    scores = []
    for name, kpis in model_results.items():
        s = compute_cavs(kpis, ref_kpis, weights)
        scores.append((name, s))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def rank_models_by_metric(
    model_results: dict[str, dict[str, float]],
    metric: str,
) -> list[tuple[str, float]]:
    """Rank models by a single forecast metric (ascending — lower is better).

    Args:
        model_results: {model_name: {metric_name: value}}
        metric: metric key to rank by (e.g. "mse", "mae")

    Returns:
        List of (model_name, metric_value) sorted ascending.
    """
    scores = []
    for name, metrics in model_results.items():
        if metric in metrics:
            scores.append((name, metrics[metric]))
    scores.sort(key=lambda x: x[1])
    return scores


def compare_selection_strategies(
    model_results: dict[str, dict[str, float]],
    ref_kpis: dict[str, float],
    kpi_keys: list[str] | None = None,
    weights: dict[str, float] | None = None,
) -> dict:
    """Compare MSE vs MAE vs CAVS model selection strategies.

    For each strategy, selects the best model and reports its KPIs.

    Args:
        model_results: {model_name: {"mse": ..., "mae": ..., "cost": ..., ...}}
        ref_kpis: reference KPIs for CAVS computation
        kpi_keys: which KPIs to report (default: cost, carbon, peak, ramping)
        weights: KPI weights for CAVS

    Returns:
        Dict with keys "mse_selection", "mae_selection", "cavs_selection",
        each containing selected model name and its KPIs.
    """
    kpi_keys = kpi_keys or ["cost", "carbon", "peak", "ramping"]

    mse_ranking = rank_models_by_metric(model_results, "mse")
    mae_ranking = rank_models_by_metric(model_results, "mae")
    cavs_ranking = rank_models_by_cavs(model_results, ref_kpis, weights)

    def extract_kpis(name: str) -> dict[str, float]:
        return {k: model_results[name].get(k, float("nan")) for k in kpi_keys}

    result = {}
    if mse_ranking:
        best_mse = mse_ranking[0][0]
        result["mse_selection"] = {"model": best_mse, "kpis": extract_kpis(best_mse)}
    if mae_ranking:
        best_mae = mae_ranking[0][0]
        result["mae_selection"] = {"model": best_mae, "kpis": extract_kpis(best_mae)}
    if cavs_ranking:
        best_cavs = cavs_ranking[0][0]
        result["cavs_selection"] = {"model": best_cavs, "kpis": extract_kpis(best_cavs)}

    return result
