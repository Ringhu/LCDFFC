"""GRU-based multi-step forecaster."""

import torch
from torch import Tensor, nn

from models.base_forecaster import BaseForecaster


class GRUForecaster(BaseForecaster):
    """GRU encoder with linear decoder for multi-step forecasting.

    Args:
        input_dim: Number of input features.
        hidden_dim: GRU hidden state dimension.
        num_layers: Number of GRU layers.
        output_dim: Number of target features to predict.
        horizon: Default prediction horizon.
        dropout: Dropout rate between GRU layers.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        output_dim: int = 1,
        horizon: int = 24,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.horizon = horizon
        self.output_dim = output_dim

        self.encoder = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.decoder = nn.Linear(hidden_dim, horizon * output_dim)

    def forward(self, history: Tensor) -> Tensor:
        """Encode history and decode to multi-step predictions.

        Args:
            history: (batch, history_len, input_dim)

        Returns:
            (batch, horizon, output_dim)
        """
        _, hidden = self.encoder(history)
        last_hidden = hidden[-1]  # (batch, hidden_dim)
        out = self.decoder(last_hidden)  # (batch, horizon * output_dim)
        return out.view(-1, self.horizon, self.output_dim)

    def predict(self, history: Tensor, horizon: int | None = None) -> Tensor:
        """Inference prediction.

        Args:
            history: (batch, history_len, input_dim)
            horizon: Ignored in this implementation (fixed at init).

        Returns:
            (batch, horizon, output_dim)
        """
        self.eval()
        with torch.no_grad():
            return self.forward(history)
