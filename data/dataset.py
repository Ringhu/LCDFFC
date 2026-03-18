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
    """

    def __init__(
        self,
        data: np.ndarray,
        history_len: int = 24,
        horizon: int = 24,
        target_cols: list[int] | None = None,
        mean: np.ndarray | None = None,
        std: np.ndarray | None = None,
    ):
        # Normalize
        if mean is None:
            mean = data.mean(axis=0)
        if std is None:
            std = data.std(axis=0)
            std[std < 1e-8] = 1.0  # avoid division by zero for constant features

        self.mean = mean
        self.std = std
        normalized = (data - mean) / std
        self.data = torch.tensor(normalized, dtype=torch.float32)
        self.history_len = history_len
        self.horizon = horizon
        self.target_cols = target_cols

    def __len__(self) -> int:
        return len(self.data) - self.history_len - self.horizon + 1

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        history = self.data[idx : idx + self.history_len]
        future = self.data[idx + self.history_len : idx + self.history_len + self.horizon]
        if self.target_cols is not None:
            future = future[:, self.target_cols]
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
    ) -> "CityLearnDataset":
        """Load dataset from NPZ file with train/val/test split.

        Args:
            data_path: Path to forecast_data.npz.
            split: One of "train", "val", "test".
            history_len: Number of past timesteps.
            horizon: Number of future timesteps.
            target_cols: Column indices to predict.
            train_ratio: Fraction of data for training.
            val_ratio: Fraction of data for validation.
            norm_stats_path: Path to save/load normalization stats.

        Returns:
            CityLearnDataset instance for the requested split.
        """
        loaded = np.load(data_path, allow_pickle=True)
        data = loaded["data"].astype(np.float32)
        columns = loaded["columns"]
        T = len(data)

        # Chronological split
        train_end = int(T * train_ratio)
        val_end = int(T * (train_ratio + val_ratio))

        if split == "train":
            split_data = data[:train_end]
        elif split == "val":
            split_data = data[train_end:val_end]
        elif split == "test":
            split_data = data[val_end:]
        else:
            raise ValueError(f"Unknown split: {split}")

        # Compute normalization from training data only
        train_data = data[:train_end]
        mean = train_data.mean(axis=0)
        std = train_data.std(axis=0)
        std[std < 1e-8] = 1.0

        # Save/load norm stats
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
        )

    @property
    def num_features(self) -> int:
        return self.data.shape[1]

    @property
    def num_targets(self) -> int:
        if self.target_cols is not None:
            return len(self.target_cols)
        return self.data.shape[1]
