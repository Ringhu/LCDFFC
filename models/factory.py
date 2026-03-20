"""Factory helpers for forecasting models."""

from __future__ import annotations

from models.gru_forecaster import GRUForecaster
from models.tsmixer_forecaster import TSMixerForecaster


def build_forecaster(model_cfg: dict, input_dim: int, output_dim: int):
    model_type = str(model_cfg.get("type", "gru")).lower()
    horizon = int(model_cfg["horizon"])
    history_len = int(model_cfg.get("history_len", 24))

    if model_type == "gru":
        return GRUForecaster(
            input_dim=input_dim,
            hidden_dim=model_cfg.get("hidden_dim", 64),
            num_layers=model_cfg.get("num_layers", 2),
            output_dim=output_dim,
            horizon=horizon,
            dropout=model_cfg.get("dropout", 0.1),
        )

    if model_type == "tsmixer":
        return TSMixerForecaster(
            input_dim=input_dim,
            history_len=history_len,
            model_dim=model_cfg.get("model_dim", 64),
            num_layers=model_cfg.get("num_layers", 4),
            ff_dim=model_cfg.get("ff_dim", 128),
            output_dim=output_dim,
            horizon=horizon,
            dropout=model_cfg.get("dropout", 0.1),
        )

    raise ValueError(f"Unsupported forecaster type: {model_type}")
