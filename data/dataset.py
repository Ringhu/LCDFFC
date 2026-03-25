"""Sliding-window dataset for time-series forecasting."""

from pathlib import Path
from typing import Tuple

import numpy as np
import torch
from torch.utils.data import Dataset


class CityLearnDataset(Dataset):
    """Sliding window dataset that produces (history, future_target) pairs.

    Args:
        data: Array of shape (T, num_features).
        history_len: Number of past timesteps as input.
        horizon: Number of future timesteps to predict.
        target_cols: Indices of columns to predict. If None, predict all.
        mean: Feature means for z-score normalization. If None, computed from data.
        std: Feature stds for z-score normalization. If None, computed from data.
        return_index: If True, also return the local dataset sample index.
        split_offset: Global start offset of the split within the full time series.
    """

    def __init__(
        self,
        data: np.ndarray,
        history_len: int = 24,
        horizon: int = 24,
        target_cols: list[int] | None = None,
        mean: np.ndarray | None = None,
        std: np.ndarray | None = None,
        return_index: bool = False,
        split_offset: int = 0,
    ):
        if mean is None:
            mean = data.mean(axis=0)
        if std is None:
            std = data.std(axis=0)
            std[std < 1e-8] = 1.0

        self.mean = mean
        self.std = std
        normalized = (data - mean) / std
        self.data = torch.tensor(normalized, dtype=torch.float32)
        self.history_len = history_len
        self.horizon = horizon
        self.target_cols = target_cols
        self.return_index = return_index
        self.split_offset = int(split_offset)

    def __len__(self) -> int:
        return len(self.data) - self.history_len - self.horizon + 1

    def future_start_index(self, idx: int) -> int:
        return self.split_offset + int(idx) + self.history_len

    @property
    def future_start_indices(self) -> np.ndarray:
        return np.arange(len(self), dtype=np.int64) + self.split_offset + self.history_len

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor] | Tuple[torch.Tensor, torch.Tensor, int]:
        history = self.data[idx : idx + self.history_len]
        future = self.data[idx + self.history_len : idx + self.history_len + self.horizon]
        if self.target_cols is not None:
            future = future[:, self.target_cols]
        if self.return_index:
            return history, future, idx
        return history, future

    @classmethod
    def from_file(
        cls,
        data_path: str = "artifacts/forecast_data.npz",
        split: str = "train",
        history_len: int = 24,
        horizon: int = 24,
        target_cols: list[int] | None = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        norm_stats_path: str | None = "artifacts/norm_stats.npz",
        return_index: bool = False,
    ) -> "CityLearnDataset":
        loaded = np.load(data_path, allow_pickle=True)
        data = loaded["data"].astype(np.float32)
        columns = loaded["columns"]
        T = len(data)

        train_end = int(T * train_ratio)
        val_end = int(T * (train_ratio + val_ratio))

        if split == "train":
            split_data = data[:train_end]
            split_offset = 0
        elif split == "val":
            split_data = data[train_end:val_end]
            split_offset = train_end
        elif split == "test":
            split_data = data[val_end:]
            split_offset = val_end
        else:
            raise ValueError(f"Unknown split: {split}")

        train_data = data[:train_end]
        mean = train_data.mean(axis=0)
        std = train_data.std(axis=0)
        std[std < 1e-8] = 1.0

        if norm_stats_path:
            norm_path = Path(norm_stats_path)
            if split == "train":
                norm_path.parent.mkdir(parents=True, exist_ok=True)
                np.savez(norm_path, mean=mean, std=std, columns=columns)
            elif norm_path.exists():
                stats = np.load(norm_path)
                mean = stats["mean"]
                std = stats["std"]

        return cls(
            data=split_data,
            history_len=history_len,
            horizon=horizon,
            target_cols=target_cols,
            mean=mean,
            std=std,
            return_index=return_index,
            split_offset=split_offset,
        )

    @property
    def num_features(self) -> int:
        return self.data.shape[1]

    @property
    def num_targets(self) -> int:
        if self.target_cols is not None:
            return len(self.target_cols)
        return self.data.shape[1]
