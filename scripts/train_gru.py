"""Train GRU forecaster with MSE loss.

Usage:
    python scripts/train_gru.py --config configs/forecast.yaml
    python scripts/train_gru.py --data_path artifacts/data_2022/forecast_data.npz
"""

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
from models.gru_forecaster import GRUForecaster


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
):
    torch.manual_seed(seed)
    np.random.seed(seed)

    model_cfg = config["model"]
    train_cfg = config["training"]

    # Data
    history_len = model_cfg.get("history_len", 24)
    horizon = model_cfg["horizon"]

    train_ds = CityLearnDataset.from_file(
        data_path, split="train", history_len=history_len,
        horizon=horizon, target_cols=target_cols,
    )
    val_ds = CityLearnDataset.from_file(
        data_path, split="val", history_len=history_len,
        horizon=horizon, target_cols=target_cols,
    )
    test_ds = CityLearnDataset.from_file(
        data_path, split="test", history_len=history_len,
        horizon=horizon, target_cols=target_cols,
    )

    train_loader = DataLoader(train_ds, batch_size=train_cfg["batch_size"], shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=train_cfg["batch_size"], shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=train_cfg["batch_size"], shuffle=False)

    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")
    print(f"Input dim: {train_ds.num_features}, Output dim: {train_ds.num_targets}")

    # Model
    model = GRUForecaster(
        input_dim=train_ds.num_features,
        hidden_dim=model_cfg["hidden_dim"],
        num_layers=model_cfg["num_layers"],
        output_dim=train_ds.num_targets,
        horizon=horizon,
        dropout=model_cfg.get("dropout", 0.1),
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=train_cfg["learning_rate"],
        weight_decay=train_cfg.get("weight_decay", 0),
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5,
    )
    loss_fn = nn.MSELoss()

    # Training
    epochs = train_cfg["epochs"]
    patience = train_cfg.get("early_stopping_patience", 10)
    ckpt_dir = Path(config.get("checkpoint_dir", "artifacts/checkpoints"))
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_name = f"gru_mse_best{checkpoint_suffix}.pt"

    best_val_loss = float("inf")
    wait = 0
    train_losses, val_losses = [], []

    for epoch in range(epochs):
        # Train
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

        # Validate
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

    # Load best model
    model.load_state_dict(torch.load(ckpt_dir / ckpt_name, weights_only=True))
    print(f"\nBest val loss: {best_val_loss:.6f}")

    # Test evaluation
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

    # Metrics per target column
    test_metrics = {}
    target_names = [f"target_{i}" for i in range(preds.shape[2])]
    for i, name in enumerate(target_names):
        mse = float(np.mean((preds[:, :, i] - targets[:, :, i]) ** 2))
        mae = float(np.mean(np.abs(preds[:, :, i] - targets[:, :, i])))
        test_metrics[name] = {"mse": mse, "mae": mae}
    test_metrics["overall_mse"] = float(np.mean((preds - targets) ** 2))
    test_metrics["overall_mae"] = float(np.mean(np.abs(preds - targets)))

    print("\nTest metrics:")
    for k, v in test_metrics.items():
        if isinstance(v, dict):
            print(f"  {k}: MSE={v['mse']:.6f}, MAE={v['mae']:.6f}")
        else:
            print(f"  {k}: {v:.6f}")

    # Save results
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    suffix = checkpoint_suffix
    with open(reports_dir / f"gru_mse_test_metrics{suffix}.json", "w") as f:
        json.dump(test_metrics, f, indent=2)

    # Training curve plot
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    ax.plot(train_losses, label="Train")
    ax.plot(val_losses, label="Val")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.set_title("GRU Training Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(reports_dir / f"gru_training_curve{suffix}.png", dpi=150)
    plt.close()

    # Prediction vs actual plot (first 200 test samples, first target)
    fig, ax = plt.subplots(1, 1, figsize=(12, 4))
    n_show = min(200, len(preds))
    ax.plot(targets[:n_show, 0, 0], label="Actual", alpha=0.8)
    ax.plot(preds[:n_show, 0, 0], label="Predicted", alpha=0.8)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Value (normalized)")
    ax.set_title("GRU Forecast: 1-step-ahead (first target)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(reports_dir / f"gru_pred_vs_actual{suffix}.png", dpi=150)
    plt.close()

    print(f"\nCheckpoint saved: {ckpt_dir / ckpt_name}")
    print(f"Metrics saved: {reports_dir / f'gru_mse_test_metrics{suffix}.json'}")
    print(f"Plots saved: {reports_dir}/")

    return model, test_metrics


def main():
    parser = argparse.ArgumentParser(description="Train GRU forecaster")
    parser.add_argument("--config", type=str, default="configs/forecast.yaml")
    parser.add_argument("--data_path", type=str, default="artifacts/data_2022/forecast_data.npz")
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--suffix", type=str, default="",
                        help="Suffix for checkpoint/report files (e.g., _seed0)")
    args = parser.parse_args()

    config = load_config(args.config)

    # Target columns: electricity_pricing(4), non_shiftable_load_avg(5), solar_generation_avg(6)
    target_cols = [4, 5, 6]

    train(args.data_path, config, target_cols, args.device, args.seed, args.suffix)


if __name__ == "__main__":
    main()
