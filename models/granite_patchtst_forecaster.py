"""Granite PatchTST initialized forecaster."""

from __future__ import annotations

import torch
from torch import Tensor
from transformers import PatchTSTConfig, PatchTSTForPrediction

from models.base_forecaster import BaseForecaster


class GranitePatchTSTForecaster(BaseForecaster):
    """Foundation-like PatchTST baseline initialized from Granite weights.

    This baseline uses the first 7 forecast features only, matching the channel
    count of the cached Granite pretrained model. The model predicts 7 channels
    and returns the 3 task targets (price/load/solar) via channel slicing.
    """

    def __init__(
        self,
        input_dim: int,
        history_len: int,
        output_dim: int = 3,
        horizon: int = 24,
        pretrained_model_name: str | None = "ibm-granite/granite-timeseries-patchtst",
        use_pretrained: bool = True,
        local_files_only: bool = True,
        freeze_backbone: bool = False,
    ):
        super().__init__()
        self.horizon = horizon
        self.output_dim = output_dim
        self.history_len = history_len
        self.input_channels = min(int(input_dim), 7)
        self.target_slice = slice(4, 7)
        self.pretrained_model_name = pretrained_model_name
        self.use_pretrained = bool(use_pretrained and pretrained_model_name)

        if self.input_channels < 7:
            raise ValueError("Granite baseline expects at least 7 input features")

        if pretrained_model_name:
            base_cfg = PatchTSTConfig.from_pretrained(pretrained_model_name, local_files_only=local_files_only)
        else:
            base_cfg = PatchTSTConfig(
                num_input_channels=7,
                context_length=history_len,
                prediction_length=horizon,
                patch_length=12,
                patch_stride=12,
                d_model=128,
                num_hidden_layers=3,
                num_attention_heads=16,
                ffn_dim=512,
                loss="mse",
            )

        config = PatchTSTConfig(
            num_input_channels=7,
            context_length=history_len,
            prediction_length=horizon,
            patch_length=base_cfg.patch_length,
            patch_stride=base_cfg.patch_stride,
            d_model=base_cfg.d_model,
            num_hidden_layers=base_cfg.num_hidden_layers,
            num_attention_heads=base_cfg.num_attention_heads,
            ffn_dim=base_cfg.ffn_dim,
            dropout=getattr(base_cfg, "dropout", 0.1),
            attention_dropout=base_cfg.attention_dropout,
            ff_dropout=base_cfg.ff_dropout,
            head_dropout=base_cfg.head_dropout,
            positional_dropout=base_cfg.positional_dropout,
            path_dropout=base_cfg.path_dropout,
            activation_function=base_cfg.activation_function,
            norm_type=base_cfg.norm_type,
            norm_eps=base_cfg.norm_eps,
            bias=base_cfg.bias,
            pre_norm=base_cfg.pre_norm,
            use_cls_token=base_cfg.use_cls_token,
            share_embedding=base_cfg.share_embedding,
            share_projection=base_cfg.share_projection,
            scaling=base_cfg.scaling,
            loss="mse",
        )
        self.backbone = PatchTSTForPrediction(config)

        if self.use_pretrained:
            pretrained = PatchTSTForPrediction.from_pretrained(
                pretrained_model_name,
                local_files_only=local_files_only,
            )
            current = self.backbone.state_dict()
            loaded = {
                key: value
                for key, value in pretrained.state_dict().items()
                if key in current and current[key].shape == value.shape
            }
            self.backbone.load_state_dict(loaded, strict=False)

        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False

    def forward(self, history: Tensor) -> Tensor:
        inputs = history[..., :7]
        outputs = self.backbone(past_values=inputs).prediction_outputs
        outputs = outputs[:, : self.horizon, self.target_slice]
        return outputs

    def predict(self, history: Tensor, horizon: int | None = None) -> Tensor:
        self.eval()
        with torch.no_grad():
            return self.forward(history)
