"""Train a forecasting backbone selected by config."""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import yaml
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.dataset import CityLearnDataset
from models import (
    build_event_window_weights,
    build_manual_horizon_weights,
    compute_mixed_weighted_loss,
)
from models.factory import build_forecaster

TARGET_COLS = [4, 5, 6]


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def _load_split_raw_targets(data_path: str, split: str, target_cols: list[int]) -> np.ndarray:
    loaded = np.load(data_path, allow_pickle=True)
    data = loaded["data"].astype(np.float32)
    train_end = int(len(data) * 0.7)
    val_end = int(len(data) * 0.85)
    if split == "train":
        split_data = data[:train_end]
    elif split == "val":
        split_data = data[train_end:val_end]
    elif split == "test":
        split_data = data[val_end:]
    else:
        raise ValueError(f"Unknown split: {split}")
    return split_data[:, target_cols]


def _load_weight_metadata(labels_path: str | None) -> tuple[np.ndarray | None, dict | None]:
    if not labels_path:
        return None, None
    label_path = Path(labels_path)
    if not label_path.exists():
        return None, None
    loaded = np.load(label_path)
    metadata_path = label_path.with_suffix(".json")
    metadata = None
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
    future_start_indices = loaded["future_start_indices"] if "future_start_indices" in loaded else None
    return future_start_indices, metadata


def _validate_weight_alignment(
    dataset: CityLearnDataset,
    labels_path: str,
    weights: np.ndarray,
    split: str,
) -> None:
    future_start_indices, metadata = _load_weight_metadata(labels_path)
    if len(weights) != len(dataset):
        raise ValueError(
            f"Weight length mismatch for split={split}: labels={len(weights)} dataset={len(dataset)}"
        )
    if future_start_indices is not None:
        expected = dataset.future_start_indices[: len(weights)]
        if not np.array_equal(future_start_indices.astype(np.int64), expected.astype(np.int64)):
            raise ValueError(f"future_start_indices mismatch for split={split}")
    if metadata is not None:
        if metadata.get("split") != split:
            raise ValueError(f"Label metadata split mismatch: {metadata.get('split')} vs {split}")
        if int(metadata.get("history_len", dataset.history_len)) != int(dataset.history_len):
            raise ValueError("Label metadata history_len mismatch")
        if int(metadata.get("horizon", dataset.horizon)) != int(dataset.horizon):
            raise ValueError("Label metadata horizon mismatch")


def _build_split_weights(
    loss_mode: str,
    labels_path: str | None,
    dataset: CityLearnDataset,
    split: str,
    data_path: str,
    target_cols: list[int],
    front_steps: int,
    front_weight: float,
    event_boost: float,
) -> np.ndarray | None:
    mode = loss_mode.lower()
    horizon = dataset.horizon
    num_targets = dataset.num_targets

    if mode == "uniform":
        return None

    if mode == "csft":
        if not labels_path:
            raise ValueError("labels_path is required for loss_mode=csft")
        label_path = Path(labels_path)
        if not label_path.exists():
            raise ValueError(f"Missing CSFT labels for split={split}: {label_path}")
        loaded = np.load(label_path)
        weights = loaded["sensitivity"].astype(np.float32)
        _validate_weight_alignment(dataset, str(label_path), weights, split)
        return weights

    if mode == "manual_horizon":
        base = build_manual_horizon_weights(
            horizon=horizon,
            num_targets=num_targets,
            front_steps=front_steps,
            front_weight=front_weight,
        )
        return np.repeat(base[None, ...], len(dataset), axis=0).astype(np.float32)

    if mode == "event_window":
        train_targets = _load_split_raw_targets(data_path, split="train", target_cols=target_cols)
        load = train_targets[:, 1]
        solar = train_targets[:, 2]
        net_load = load - solar
        price_threshold = float(np.quantile(train_targets[:, 0], 0.9))
        net_load_threshold = float(np.quantile(net_load, 0.9))
        weights = np.zeros((len(dataset), horizon, num_targets), dtype=np.float32)
        for idx in range(len(dataset)):
            sample = dataset[idx]
            target = sample[1]
            future_raw = target.numpy() * dataset.std[target_cols] + dataset.mean[target_cols]
            weights[idx] = build_event_window_weights(
                future_raw,
                price_threshold=price_threshold,
                net_load_threshold=net_load_threshold,
                boost=event_boost,
            )
        return weights

    raise ValueError(f"Unsupported loss_mode: {loss_mode}")


def _evaluate_model(model, loader, device, loss_mode: str, labels: np.ndarray | None, alpha: float, loss_type: str):
    model.eval()
    total_loss = 0.0
    total_count = 0
    all_preds, all_targets = [], []
    with torch.no_grad():
        for batch in loader:
            if len(batch) == 3:
                history, target, sample_idx = batch
            else:
                history, target = batch
                sample_idx = None
            history, target = history.to(device), target.to(device)
            pred = model(history)
            if loss_mode == "uniform":
                weight_tensor = torch.ones_like(target)
                loss, _ = compute_mixed_weighted_loss(
                    pred,
                    target,
                    weight_tensor,
                    alpha=1.0,
                    loss_type=loss_type,
                )
            else:
                if sample_idx is None or labels is None:
                    raise ValueError("Indexed dataset and labels are required for weighted evaluation")
                weight_tensor = torch.tensor(labels[sample_idx.cpu().numpy()], dtype=torch.float32, device=device)
                loss, _ = compute_mixed_weighted_loss(
                    pred,
                    target,
                    weight_tensor,
                    alpha=alpha,
                    loss_type=loss_type,
                )
            total_loss += loss.item() * history.size(0)
            total_count += history.size(0)
            all_preds.append(pred.cpu().numpy())
            all_targets.append(target.cpu().numpy())
    return total_loss / max(total_count, 1), np.concatenate(all_preds), np.concatenate(all_targets)


def train(
    data_path: str,
    config: dict,
    target_cols: list[int],
    device: str = "cuda",
    seed: int = 42,
    checkpoint_suffix: str = "",
    max_epochs: int | None = None,
    loss_mode: str = "uniform",
    labels_path: str | None = None,
    alpha: float = 0.5,
    loss_type: str = "huber",
    front_steps: int = 6,
    front_weight: float = 3.0,
    event_boost: float = 3.0,
):
    torch.manual_seed(seed)
    np.random.seed(seed)

    model_cfg = config["model"]
    train_cfg = config["training"]
    model_type = str(model_cfg.get("type", "gru")).lower()

    history_len = model_cfg.get("history_len", 24)
    horizon = model_cfg["horizon"]
    use_index = loss_mode.lower() != "uniform"

    train_ds = CityLearnDataset.from_file(
        data_path,
        split="train",
        history_len=history_len,
        horizon=horizon,
        target_cols=target_cols,
        return_index=use_index,
    )
    val_ds = CityLearnDataset.from_file(
        data_path,
        split="val",
        history_len=history_len,
        horizon=horizon,
        target_cols=target_cols,
        return_index=use_index,
    )
    test_ds = CityLearnDataset.from_file(
        data_path,
        split="test",
        history_len=history_len,
        horizon=horizon,
        target_cols=target_cols,
        return_index=use_index,
    )

    train_loader = DataLoader(train_ds, batch_size=train_cfg["batch_size"], shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=train_cfg["batch_size"], shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=train_cfg["batch_size"], shuffle=False)

    print(f"Model: {model_type} | loss_mode: {loss_mode}")
    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")
    print(f"Input dim: {train_ds.num_features}, Output dim: {train_ds.num_targets}")

    model = build_forecaster(model_cfg, input_dim=train_ds.num_features, output_dim=train_ds.num_targets).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=train_cfg["learning_rate"],
        weight_decay=train_cfg.get("weight_decay", 0),
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)

    train_weights = _build_split_weights(
        loss_mode=loss_mode,
        labels_path=labels_path,
        dataset=train_ds,
        split="train",
        data_path=data_path,
        target_cols=target_cols,
        front_steps=front_steps,
        front_weight=front_weight,
        event_boost=event_boost,
    )
    val_labels_path = labels_path
    test_labels_path = labels_path
    if labels_path and loss_mode.lower() == "csft" and "_train" in labels_path:
        val_labels_path = labels_path.replace("_train", "_val")
        test_labels_path = labels_path.replace("_train", "_test")
    val_weights = _build_split_weights(
        loss_mode=loss_mode,
        labels_path=val_labels_path,
        dataset=val_ds,
        split="val",
        data_path=data_path,
        target_cols=target_cols,
        front_steps=front_steps,
        front_weight=front_weight,
        event_boost=event_boost,
    )
    test_weights = _build_split_weights(
        loss_mode=loss_mode,
        labels_path=test_labels_path,
        dataset=test_ds,
        split="test",
        data_path=data_path,
        target_cols=target_cols,
        front_steps=front_steps,
        front_weight=front_weight,
        event_boost=event_boost,
    )

    epochs = train_cfg["epochs"] if max_epochs is None else min(int(max_epochs), int(train_cfg["epochs"]))
    patience = train_cfg.get("early_stopping_patience", 10)
    ckpt_dir = Path(config.get("checkpoint_dir", "artifacts/checkpoints"))
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_name = f"{model_type}_{loss_mode}_best{checkpoint_suffix}.pt"

    best_val_loss = float("inf")
    wait = 0
    train_losses, val_losses = [], []

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for batch in train_loader:
            if len(batch) == 3:
                history, target, sample_idx = batch
            else:
                history, target = batch
                sample_idx = None
            history, target = history.to(device), target.to(device)
            pred = model(history)
            if loss_mode.lower() == "uniform":
                weight_tensor = torch.ones_like(target)
                loss, _ = compute_mixed_weighted_loss(
                    pred,
                    target,
                    weight_tensor,
                    alpha=1.0,
                    loss_type=loss_type,
                )
            else:
                if sample_idx is None or train_weights is None:
                    raise ValueError("Indexed dataset and train weights are required for weighted training")
                weight_tensor = torch.tensor(train_weights[sample_idx.cpu().numpy()], dtype=torch.float32, device=device)
                loss, _ = compute_mixed_weighted_loss(
                    pred,
                    target,
                    weight_tensor,
                    alpha=alpha,
                    loss_type=loss_type,
                )
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item() * history.size(0)
        train_loss = epoch_loss / len(train_ds)
        train_losses.append(train_loss)

        val_loss, _, _ = _evaluate_model(model, val_loader, device, loss_mode.lower(), val_weights, alpha, loss_type)
        val_losses.append(val_loss)
        scheduler.step(val_loss)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1:3d}/{epochs} | Train: {train_loss:.6f} | Val: {val_loss:.6f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            wait = 0
            torch.save(model.state_dict(), ckpt_dir / ckpt_name)
        else:
            wait += 1
            if wait >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break

    model.load_state_dict(torch.load(ckpt_dir / ckpt_name, weights_only=True))
    print(f"\nBest val loss: {best_val_loss:.6f}")

    test_loss, preds, targets = _evaluate_model(model, test_loader, device, loss_mode.lower(), test_weights, alpha, loss_type)

    test_metrics = {"test_loss": float(test_loss)}
    target_names = [f"target_{i}" for i in range(preds.shape[2])]
    for i, name in enumerate(target_names):
        mse = float(np.mean((preds[:, :, i] - targets[:, :, i]) ** 2))
        mae = float(np.mean(np.abs(preds[:, :, i] - targets[:, :, i])))
        test_metrics[name] = {"mse": mse, "mae": mae}
    test_metrics["overall_mse"] = float(np.mean((preds - targets) ** 2))
    test_metrics["overall_mae"] = float(np.mean(np.abs(preds - targets)))
    test_metrics["model_type"] = model_type
    test_metrics["loss_mode"] = loss_mode
    test_metrics["alpha"] = float(alpha)
    test_metrics["loss_type"] = loss_type

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    suffix = checkpoint_suffix
    with open(reports_dir / f"{model_type}_{loss_mode}_test_metrics{suffix}.json", "w") as f:
        json.dump(test_metrics, f, indent=2)

    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    ax.plot(train_losses, label="Train")
    ax.plot(val_losses, label="Val")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title(f"{model_type.upper()} Training Curve ({loss_mode})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(reports_dir / f"{model_type}_{loss_mode}_training_curve{suffix}.png", dpi=150)
    plt.close()

    fig, ax = plt.subplots(1, 1, figsize=(12, 4))
    n_show = min(200, len(preds))
    ax.plot(targets[:n_show, 0, 0], label="Actual", alpha=0.8)
    ax.plot(preds[:n_show, 0, 0], label="Predicted", alpha=0.8)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Value (normalized)")
    ax.set_title(f"{model_type.upper()} Forecast: 1-step-ahead ({loss_mode})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(reports_dir / f"{model_type}_{loss_mode}_pred_vs_actual{suffix}.png", dpi=150)
    plt.close()

    print(f"\nCheckpoint saved: {ckpt_dir / ckpt_name}")
    print(f"Metrics saved: {reports_dir / f'{model_type}_{loss_mode}_test_metrics{suffix}.json'}")
    print(f"Plots saved: {reports_dir}/")
    return model, test_metrics


def main():
    parser = argparse.ArgumentParser(description="Train a forecasting backbone")
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--data_path", type=str, default="artifacts/forecast_data.npz")
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--suffix", type=str, default="")
    parser.add_argument("--max_epochs", type=int, default=None)
    parser.add_argument(
        "--loss_mode",
        type=str,
        default="uniform",
        choices=["uniform", "manual_horizon", "event_window", "csft"],
    )
    parser.add_argument("--labels_path", type=str, default=None)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--loss_type", type=str, default="huber", choices=["mse", "mae", "huber"])
    parser.add_argument("--front_steps", type=int, default=6)
    parser.add_argument("--front_weight", type=float, default=3.0)
    parser.add_argument("--event_boost", type=float, default=3.0)
    args = parser.parse_args()

    config = load_config(args.config)
    train(
        args.data_path,
        config,
        TARGET_COLS,
        args.device,
        args.seed,
        args.suffix,
        args.max_epochs,
        args.loss_mode,
        args.labels_path,
        args.alpha,
        args.loss_type,
        args.front_steps,
        args.front_weight,
        args.event_boost,
    )


if __name__ == "__main__":
    main()
