"""TSMixer-style multi-step forecaster."""

import torch
from torch import Tensor, nn

from models.base_forecaster import BaseForecaster


class MixerBlock(nn.Module):
    """Simple temporal-channel mixer block."""

    def __init__(self, seq_len: int, model_dim: int, ff_dim: int, dropout: float = 0.1):
        super().__init__()
        self.time_norm = nn.LayerNorm(model_dim)
        self.time_mlp = nn.Sequential(
            nn.Linear(seq_len, ff_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ff_dim, seq_len),
            nn.Dropout(dropout),
        )
        self.feature_norm = nn.LayerNorm(model_dim)
        self.feature_mlp = nn.Sequential(
            nn.Linear(model_dim, ff_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ff_dim, model_dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: Tensor) -> Tensor:
        y = self.time_norm(x)
        y = y.transpose(1, 2)
        y = self.time_mlp(y)
        y = y.transpose(1, 2)
        x = x + y
        z = self.feature_norm(x)
        z = self.feature_mlp(z)
        return x + z


class TSMixerForecaster(BaseForecaster):
    """TSMixer-style forecaster with a flattened prediction head."""

    def __init__(
        self,
        input_dim: int,
        history_len: int,
        model_dim: int = 64,
        num_layers: int = 4,
        ff_dim: int = 128,
        output_dim: int = 1,
        horizon: int = 24,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.horizon = horizon
        self.output_dim = output_dim
        self.history_len = history_len

        self.input_proj = nn.Linear(input_dim, model_dim)
        self.blocks = nn.ModuleList(
            [MixerBlock(history_len, model_dim, ff_dim, dropout=dropout) for _ in range(num_layers)]
        )
        self.head = nn.Sequential(
            nn.LayerNorm(model_dim),
            nn.Flatten(),
            nn.Linear(history_len * model_dim, horizon * output_dim),
        )

    def forward(self, history: Tensor) -> Tensor:
        x = self.input_proj(history)
        for block in self.blocks:
            x = block(x)
        out = self.head(x)
        return out.view(-1, self.horizon, self.output_dim)

    def predict(self, history: Tensor, horizon: int | None = None) -> Tensor:
        self.eval()
        with torch.no_grad():
            return self.forward(history)
