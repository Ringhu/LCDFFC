"""Shared adapters for zero-shot foundation-model forecasting."""

from __future__ import annotations

import numpy as np
import torch


class BaseFoundationAdapter:
    name: str

    def __init__(self, device: str, horizon: int, context_length: int):
        self.device = device
        self.horizon = int(horizon)
        self.context_length = int(context_length)

    def forecast_univariate(self, history: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class Chronos2Adapter(BaseFoundationAdapter):
    name = "chronos2"

    def __init__(self, device: str, horizon: int, context_length: int):
        super().__init__(device, horizon, context_length)
        from chronos import Chronos2Pipeline

        dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
        self.pipeline = Chronos2Pipeline.from_pretrained(
            "amazon/chronos-2",
            device_map=device,
            dtype=dtype,
        )

    def forecast_univariate(self, history: np.ndarray) -> np.ndarray:
        context = np.asarray(history[-self.context_length :], dtype=np.float32)
        forecast = self.pipeline.predict([context], prediction_length=self.horizon, context_length=len(context))[0]
        return forecast[0, forecast.shape[1] // 2].detach().cpu().numpy().astype(np.float32)


class Moirai2Adapter(BaseFoundationAdapter):
    name = "moirai2"

    def __init__(self, device: str, horizon: int, context_length: int):
        super().__init__(device, horizon, context_length)
        from uni2ts.model.moirai2 import Moirai2Forecast
        from uni2ts.model.moirai2.module import Moirai2Module

        module = Moirai2Module.from_pretrained("Salesforce/moirai-2.0-R-small").to(device)
        self.model = Moirai2Forecast(
            prediction_length=horizon,
            target_dim=1,
            feat_dynamic_real_dim=0,
            past_feat_dynamic_real_dim=0,
            context_length=context_length,
            module=module,
        ).to(device)
        self.model.eval()

    def forecast_univariate(self, history: np.ndarray) -> np.ndarray:
        history = np.asarray(history, dtype=np.float32)
        context = np.zeros((self.context_length,), dtype=np.float32)
        observed = np.zeros((self.context_length, 1), dtype=bool)
        use = history[-self.context_length :]
        context[-len(use) :] = use
        observed[-len(use) :, 0] = True
        pad = np.ones((self.context_length,), dtype=bool)
        pad[-len(use) :] = False

        with torch.no_grad():
            out = self.model(
                past_target=torch.tensor(context, dtype=torch.float32, device=self.device).view(1, self.context_length, 1),
                past_observed_target=torch.tensor(observed, dtype=torch.bool, device=self.device).view(1, self.context_length, 1),
                past_is_pad=torch.tensor(pad, dtype=torch.bool, device=self.device).view(1, self.context_length),
            )
        return out[0, out.shape[1] // 2].detach().cpu().numpy().astype(np.float32)


class TimesFM25Adapter(BaseFoundationAdapter):
    name = "timesfm2.5"

    def __init__(self, device: str, horizon: int, context_length: int):
        super().__init__(device, horizon, context_length)
        from transformers.models.timesfm2_5.modeling_timesfm2_5 import TimesFm2_5ModelForPrediction

        self.model = TimesFm2_5ModelForPrediction.from_pretrained("google/timesfm-2.5-200m-transformers").to(device)
        self.model.eval()

    def forecast_univariate(self, history: np.ndarray) -> np.ndarray:
        history = np.asarray(history, dtype=np.float32)
        context = np.zeros((self.context_length,), dtype=np.float32)
        use = history[-self.context_length :]
        context[-len(use) :] = use
        with torch.no_grad():
            out = self.model(
                past_values=[torch.tensor(context, dtype=torch.float32, device=self.device)],
                forecast_context_len=self.context_length,
            )
        return out.mean_predictions[0, : self.horizon].detach().cpu().numpy().astype(np.float32)


class MomentAdapter(BaseFoundationAdapter):
    name = "moment"

    def __init__(self, device: str, horizon: int, context_length: int):
        super().__init__(device, horizon, context_length)
        from momentfm import MOMENTPipeline

        self.model = MOMENTPipeline.from_pretrained(
            "AutonLab/MOMENT-1-small",
            model_kwargs={"task_name": "forecasting", "forecast_horizon": horizon},
        )
        self.model.init()
        self.model = self.model.to(device)
        self.model.eval()

    def forecast_univariate(self, history: np.ndarray) -> np.ndarray:
        history = np.asarray(history, dtype=np.float32)
        context = np.zeros((self.context_length,), dtype=np.float32)
        mask = np.zeros((self.context_length,), dtype=np.int64)
        use = history[-self.context_length :]
        context[-len(use) :] = use
        mask[-len(use) :] = 1
        with torch.no_grad():
            out = self.model.forecast(
                x_enc=torch.tensor(context, dtype=torch.float32, device=self.device).view(1, 1, self.context_length),
                input_mask=torch.tensor(mask, dtype=torch.long, device=self.device).view(1, self.context_length),
            )
        return out.forecast[0, 0].detach().cpu().numpy().astype(np.float32)


def build_adapter(name: str, device: str, horizon: int, context_length: int):
    key = name.lower()
    if key == "chronos2":
        return Chronos2Adapter(device, horizon, context_length)
    if key == "moirai2":
        return Moirai2Adapter(device, horizon, context_length)
    if key in {"timesfm", "timesfm2.5"}:
        return TimesFM25Adapter(device, horizon, context_length)
    if key == "moment":
        return MomentAdapter(device, horizon, context_length)
    raise ValueError(f"Unsupported foundation model: {name}")
