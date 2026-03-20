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
from models.factory import build_forecaster


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def train(
    data_path: str,
    config: dict,
    target_cols: list[int],
    device: str = "cuda",
    seed: int = 42,
    checkpoint_suffix: str = "",
    max_epochs: int | None = None,
):
    torch.manual_seed(seed)
    np.random.seed(seed)

    model_cfg = config["model"]
    train_cfg = config["training"]
    model_type = str(model_cfg.get("type", "gru")).lower()

    history_len = model_cfg.get("history_len", 24)
    horizon = model_cfg["horizon"]

    train_ds = CityLearnDataset.from_file(data_path, split="train", history_len=history_len, horizon=horizon, target_cols=target_cols)
    val_ds = CityLearnDataset.from_file(data_path, split="val", history_len=history_len, horizon=horizon, target_cols=target_cols)
    test_ds = CityLearnDataset.from_file(data_path, split="test", history_len=history_len, horizon=horizon, target_cols=target_cols)

    train_loader = DataLoader(train_ds, batch_size=train_cfg["batch_size"], shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=train_cfg["batch_size"], shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=train_cfg["batch_size"], shuffle=False)

    print(f"Model: {model_type}")
    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")
    print(f"Input dim: {train_ds.num_features}, Output dim: {train_ds.num_targets}")

    model = build_forecaster(model_cfg, input_dim=train_ds.num_features, output_dim=train_ds.num_targets).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=train_cfg["learning_rate"],
        weight_decay=train_cfg.get("weight_decay", 0),
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)
    loss_fn = nn.MSELoss()

    epochs = train_cfg["epochs"] if max_epochs is None else min(int(max_epochs), int(train_cfg["epochs"]))
    patience = train_cfg.get("early_stopping_patience", 10)
    ckpt_dir = Path(config.get("checkpoint_dir", "artifacts/checkpoints"))
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_name = f"{model_type}_mse_best{checkpoint_suffix}.pt"

    best_val_loss = float("inf")
    wait = 0
    train_losses, val_losses = [], []

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for history, target in train_loader:
            history, target = history.to(device), target.to(device)
            pred = model(history)
            loss = loss_fn(pred, target)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item() * history.size(0)
        train_loss = epoch_loss / len(train_ds)
        train_losses.append(train_loss)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for history, target in val_loader:
                history, target = history.to(device), target.to(device)
                pred = model(history)
                val_loss += loss_fn(pred, target).item() * history.size(0)
        val_loss /= len(val_ds)
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

    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for history, target in test_loader:
            history = history.to(device)
            pred = model(history)
            all_preds.append(pred.cpu().numpy())
            all_targets.append(target.numpy())

    preds = np.concatenate(all_preds)
    targets = np.concatenate(all_targets)

    test_metrics = {}
    target_names = [f"target_{i}" for i in range(preds.shape[2])]
    for i, name in enumerate(target_names):
        mse = float(np.mean((preds[:, :, i] - targets[:, :, i]) ** 2))
        mae = float(np.mean(np.abs(preds[:, :, i] - targets[:, :, i])))
        test_metrics[name] = {"mse": mse, "mae": mae}
    test_metrics["overall_mse"] = float(np.mean((preds - targets) ** 2))
    test_metrics["overall_mae"] = float(np.mean(np.abs(preds - targets)))
    test_metrics["model_type"] = model_type

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    suffix = checkpoint_suffix
    with open(reports_dir / f"{model_type}_test_metrics{suffix}.json", "w") as f:
        json.dump(test_metrics, f, indent=2)

    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    ax.plot(train_losses, label="Train")
    ax.plot(val_losses, label="Val")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.set_title(f"{model_type.upper()} Training Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(reports_dir / f"{model_type}_training_curve{suffix}.png", dpi=150)
    plt.close()

    fig, ax = plt.subplots(1, 1, figsize=(12, 4))
    n_show = min(200, len(preds))
    ax.plot(targets[:n_show, 0, 0], label="Actual", alpha=0.8)
    ax.plot(preds[:n_show, 0, 0], label="Predicted", alpha=0.8)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Value (normalized)")
    ax.set_title(f"{model_type.upper()} Forecast: 1-step-ahead (first target)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(reports_dir / f"{model_type}_pred_vs_actual{suffix}.png", dpi=150)
    plt.close()

    print(f"\nCheckpoint saved: {ckpt_dir / ckpt_name}")
    print(f"Metrics saved: {reports_dir / f'{model_type}_test_metrics{suffix}.json'}")
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
    args = parser.parse_args()

    config = load_config(args.config)
    target_cols = [4, 5, 6]
    train(args.data_path, config, target_cols, args.device, args.seed, args.suffix, args.max_epochs)


if __name__ == "__main__":
    main()
