"""Transformer encoder based multi-step forecaster."""

from __future__ import annotations

import math

import torch
from torch import Tensor, nn

from models.base_forecaster import BaseForecaster


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512):
        super().__init__()
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0), persistent=False)

    def forward(self, x: Tensor) -> Tensor:
        return x + self.pe[:, : x.size(1)]


class TransformerForecaster(BaseForecaster):
    """Transformer encoder forecaster with a flattened prediction head."""

    def __init__(
        self,
        input_dim: int,
        history_len: int,
        d_model: int = 128,
        num_layers: int = 3,
        num_heads: int = 4,
        ff_dim: int = 256,
        output_dim: int = 1,
        horizon: int = 24,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.horizon = horizon
        self.output_dim = output_dim
        self.history_len = history_len

        self.input_proj = nn.Linear(input_dim, d_model)
        self.positional_encoding = PositionalEncoding(d_model=d_model, max_len=history_len)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Flatten(),
            nn.Linear(history_len * d_model, horizon * output_dim),
        )

    def forward(self, history: Tensor) -> Tensor:
        x = self.input_proj(history)
        x = self.positional_encoding(x)
        x = self.encoder(x)
        out = self.head(x)
        return out.view(-1, self.horizon, self.output_dim)

    def predict(self, history: Tensor, horizon: int | None = None) -> Tensor:
        self.eval()
        with torch.no_grad():
            return self.forward(history)
