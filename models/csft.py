"""CSFT utilities: sensitivity normalization, weighting baselines, and losses."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F


def clip_and_normalize_sensitivity(
    sensitivity: np.ndarray,
    clip_quantile: float = 0.95,
    eps: float = 1e-6,
) -> np.ndarray:
    """Clip extreme sensitivity values and normalize each sample to mean ~1.

    Args:
        sensitivity: Array of shape (..., horizon, num_targets) or (horizon, num_targets).
        clip_quantile: Quantile used for global clipping. Set <= 0 to disable clipping.
        eps: Numerical stability constant.

    Returns:
        Normalized sensitivity array with the same shape as the input.
    """
    sens = np.asarray(sensitivity, dtype=np.float32).copy()
    if sens.size == 0:
        return sens

    if clip_quantile is not None and clip_quantile > 0:
        clip_value = float(np.quantile(sens, clip_quantile))
        if clip_value > 0:
            sens = np.clip(sens, 0.0, clip_value)

    if sens.ndim == 2:
        denom = float(np.mean(sens)) + eps
        return sens / denom

    reduce_axes = tuple(range(1, sens.ndim))
    denom = np.mean(sens, axis=reduce_axes, keepdims=True) + eps
    return sens / denom


def build_manual_horizon_weights(
    horizon: int,
    num_targets: int,
    front_steps: int = 6,
    front_weight: float = 3.0,
) -> np.ndarray:
    """Build a simple front-loaded weighting prior over forecast horizons."""
    weights = np.ones((horizon, num_targets), dtype=np.float32)
    weights[: max(0, int(front_steps)), :] = float(front_weight)
    return weights


def build_event_window_weights(
    target_raw: np.ndarray,
    price_threshold: float,
    net_load_threshold: float,
    boost: float = 3.0,
) -> np.ndarray:
    """Build heuristic event-window weights from raw future targets.

    Args:
        target_raw: Array of shape (batch, horizon, 3) or (horizon, 3) with
            [price, load, solar].
        price_threshold: High-price threshold from training split.
        net_load_threshold: High-net-load threshold from training split.
        boost: Multiplicative weight for event cells.
    """
    target_arr = np.asarray(target_raw, dtype=np.float32)
    squeeze = False
    if target_arr.ndim == 2:
        target_arr = target_arr[None, ...]
        squeeze = True

    price = target_arr[:, :, 0]
    load = target_arr[:, :, 1]
    solar = target_arr[:, :, 2]
    net_load = load - solar

    event_mask = (price >= price_threshold) | (net_load >= net_load_threshold)
    weights = np.ones_like(target_arr, dtype=np.float32)
    weights[event_mask] = float(boost)

    if squeeze:
        return weights[0]
    return weights


def _elementwise_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    loss_type: str = "huber",
    huber_delta: float = 1.0,
) -> torch.Tensor:
    loss_name = loss_type.lower()
    if loss_name == "mse":
        return (pred - target) ** 2
    if loss_name == "mae":
        return torch.abs(pred - target)
    if loss_name == "huber":
        return F.huber_loss(pred, target, delta=huber_delta, reduction="none")
    raise ValueError(f"Unsupported loss_type: {loss_type}")


def compute_mixed_weighted_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    weights: torch.Tensor,
    alpha: float = 0.5,
    loss_type: str = "huber",
    huber_delta: float = 1.0,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Compute mixed uniform + weighted forecast loss."""
    elementwise = _elementwise_loss(pred, target, loss_type=loss_type, huber_delta=huber_delta)
    base_loss = elementwise.mean()
    weighted_loss = (elementwise * weights).mean()
    total_loss = float(alpha) * base_loss + (1.0 - float(alpha)) * weighted_loss
    stats = {
        "base_loss": float(base_loss.detach().cpu()),
        "weighted_loss": float(weighted_loss.detach().cpu()),
        "mean_weight": float(weights.detach().mean().cpu()),
        "max_weight": float(weights.detach().max().cpu()),
    }
    return total_loss, stats
