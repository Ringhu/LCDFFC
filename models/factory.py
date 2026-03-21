"""Factory helpers for forecasting models."""

from __future__ import annotations

from models.granite_patchtst_forecaster import GranitePatchTSTForecaster
from models.gru_forecaster import GRUForecaster
from models.patchtst_forecaster import PatchTSTForecaster
from models.transformer_forecaster import TransformerForecaster
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

    if model_type == "patchtst":
        return PatchTSTForecaster(
            input_dim=input_dim,
            history_len=history_len,
            output_dim=output_dim,
            horizon=horizon,
            patch_length=model_cfg.get("patch_length", 4),
            patch_stride=model_cfg.get("patch_stride", 4),
            d_model=model_cfg.get("d_model", 64),
            num_layers=model_cfg.get("num_layers", 3),
            num_heads=model_cfg.get("num_heads", 4),
            ff_dim=model_cfg.get("ff_dim", 128),
            dropout=model_cfg.get("dropout", 0.1),
        )

    if model_type == "transformer":
        return TransformerForecaster(
            input_dim=input_dim,
            history_len=history_len,
            d_model=model_cfg.get("d_model", 128),
            num_layers=model_cfg.get("num_layers", 3),
            num_heads=model_cfg.get("num_heads", 4),
            ff_dim=model_cfg.get("ff_dim", 256),
            output_dim=output_dim,
            horizon=horizon,
            dropout=model_cfg.get("dropout", 0.1),
        )

    if model_type == "granite_patchtst":
        return GranitePatchTSTForecaster(
            input_dim=input_dim,
            history_len=history_len,
            output_dim=output_dim,
            horizon=horizon,
            pretrained_model_name=model_cfg.get("pretrained_model_name", "ibm-granite/granite-timeseries-patchtst"),
            use_pretrained=model_cfg.get("use_pretrained", True),
            local_files_only=model_cfg.get("local_files_only", True),
            freeze_backbone=model_cfg.get("freeze_backbone", False),
        )

    raise ValueError(f"Unsupported forecaster type: {model_type}")
