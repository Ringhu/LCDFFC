"""Abstract base class for forecasting models."""

from abc import ABC, abstractmethod
from typing import Any

import torch
from torch import Tensor, nn


class BaseForecaster(ABC, nn.Module):
    """Base interface for all forecasting models.

    Subclasses must implement `forward` and `predict`.
    """

    @abstractmethod
    def forward(self, history: Tensor) -> Tensor:
        """Forward pass for training.

        Args:
            history: (batch, history_len, num_features)

        Returns:
            Predictions of shape (batch, horizon, num_targets).
        """
        ...

    @abstractmethod
    def predict(self, history: Tensor, horizon: int) -> Tensor:
        """Inference-time prediction.

        Args:
            history: (batch, history_len, num_features)
            horizon: Number of future steps to predict.

        Returns:
            Predictions of shape (batch, horizon, num_targets).
        """
        ...

    def train_step(self, batch: tuple, loss_fn: Any) -> dict:
        """Single training step.

        Args:
            batch: (history, target) tensors.
            loss_fn: Loss function (e.g., MSE or SPO+).

        Returns:
            Dict with at least {"loss": scalar_tensor}.
        """
        history, target = batch
        pred = self.forward(history)
        loss = loss_fn(pred, target)
        return {"loss": loss}
