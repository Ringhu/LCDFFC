"""PatchTST-based multi-step forecaster."""

from __future__ import annotations

import torch
from torch import Tensor, nn
from transformers import PatchTSTConfig, PatchTSTForPrediction

from models.base_forecaster import BaseForecaster


class PatchTSTForecaster(BaseForecaster):
    """PatchTST wrapper that fits the repository forecasting interface.

    The built-in transformers PatchTST expects the input channel count to match the
    output channel count. In this project the history contains 9 normalized features
    while the forecaster only predicts 3 target channels. We therefore learn a light
    input projection from the full feature history to the target-channel history,
    then apply PatchTST on the projected sequence.
    """

    def __init__(
        self,
        input_dim: int,
        history_len: int,
        output_dim: int = 1,
        horizon: int = 24,
        patch_length: int = 4,
        patch_stride: int = 4,
        d_model: int = 64,
        num_layers: int = 3,
        num_heads: int = 4,
        ff_dim: int = 128,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.horizon = horizon
        self.output_dim = output_dim
        self.history_len = history_len

        self.input_proj = nn.Linear(input_dim, output_dim)
        config = PatchTSTConfig(
            num_input_channels=output_dim,
            context_length=history_len,
            prediction_length=horizon,
            patch_length=patch_length,
            patch_stride=patch_stride,
            d_model=d_model,
            num_hidden_layers=num_layers,
            num_attention_heads=num_heads,
            ffn_dim=ff_dim,
            attention_dropout=dropout,
            ff_dropout=dropout,
            head_dropout=dropout,
            positional_dropout=dropout,
            path_dropout=dropout,
            loss='mse',
            do_mask_input=False,
            scaling='std',
        )
        self.backbone = PatchTSTForPrediction(config)

    def forward(self, history: Tensor) -> Tensor:
        projected = self.input_proj(history)
        outputs = self.backbone(past_values=projected)
        return outputs.prediction_outputs

    def predict(self, history: Tensor, horizon: int | None = None) -> Tensor:
        self.eval()
        with torch.no_grad():
            return self.forward(history)
