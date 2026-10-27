"""
train_lstm.py - PyTorch Bidirectional LSTM Sentiment Classifier Training
Includes dataset loading, model architecture definition, early stopping,
evaluation on validation set, checkpointing, and training curve visualization.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from src.data_loader import load_config
from src.preprocessing import TextTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "config.yaml"
)


class SentimentLSTM(nn.Module):
    """
    Bidirectional LSTM neural network for text sentiment classification.
    Consists of an Embedding layer, Bidirectional LSTM, Global Pooling / Dense layers,
    and a single logit output unit.
    """

    def __init__(
        self,
        vocab_size: int = 15000,
        embedding_dim: int = 128,
        hidden_dim: int = 128,
        num_layers: int = 1,
        bidirectional: bool = True,
        dropout: float = 0.3,
        padding_idx: int = 0,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1

        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embedding_dim,
            padding_idx=padding_idx
        )

        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            bidirectional=bidirectional,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        fc_in_dim = hidden_dim * self.num_directions
        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(fc_in_dim, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        Args:
            x: Tensor of token indices with shape (batch_size, seq_len)
        Returns:
            logits: Unnormalized logit output with shape (batch_size, 1)
        """
        # (batch_size, seq_len, embed_dim)
        embedded = self.dropout(self.embedding(x))

        # lstm_out: (batch_size, seq_len, hidden_dim * num_directions)
        # h_n: (num_layers * num_directions, batch_size, hidden_dim)
        _, (h_n, _) = self.lstm(embedded)

        if self.bidirectional:
            # Concatenate final forward and backward hidden states
            # h_n[-2] is the last layer's forward state, h_n[-1] is backward state
            feat = torch.cat((h_n[-2, :, :], h_n[-1, :, :]), dim=1)
        else:
            feat = h_n[-1, :, :]

        feat = self.dropout(feat)
        feat = self.relu(self.fc1(feat))
        feat = self.dropout(feat)
        logits = self.fc2(feat)
        return logits

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Return sigmoid probability [0, 1] for positive class."""
        with torch.no_grad():
            logits = self.forward(x)
            return torch.sigmoid(logits)


class LSTMTrainer:
    """Orchestrates PyTorch LSTM dataset loading, training, validation, early stopping, and artifact saving."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config = load_config(config_path)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.processed_dir = os.path.join(self.base_dir, self.config["dataset"]["processed_dir"])
        self.models_dir = os.path.join(self.base_dir, self.config["paths"]["models_dir"])
        self.figures_dir = os.path.join(self.base_dir, self.config["paths"]["figures_dir"])
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.figures_dir, exist_ok=True)

        self.lstm_cfg = self.config["models"]["lstm"]
        self.seed = self.lstm_cfg.get("random_state", 42)
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)

        # Set PyTorch CPU threading
        self.device = torch.device("cpu")
        threads = min(8, os.cpu_count() or 4)
        torch.set_num_threads(threads)
        logger.info(f"Target compute device: {self.device} (using {threads} CPU threads)")

        # Load Tokenizer
        tokenizer_path = os.path.join(self.models_dir, "tokenizer.joblib")
        if not os.path.exists(tokenizer_path):
            raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}. Run preprocessing first.")
        self.tokenizer: TextTokenizer = joblib.load(tokenizer_path)

    def prepare_data_loaders(self) -> Tuple[DataLoader, DataLoader]:
        """Load processed CSV files, convert to token sequences, and wrap in PyTorch DataLoaders."""
        train_path = os.path.join(self.processed_dir, "train.csv")
        val_path = os.path.join(self.processed_dir, "val.csv")

        logger.info(f"Loading training data from {train_path}...")
        train_df = pd.read_csv(train_path)
        val_df = pd.read_csv(val_path)

        max_train = self.lstm_cfg.get("max_train_samples")
        if max_train and max_train < len(train_df):
            logger.info(f"Subsampling {max_train} stratified training examples for high-speed CPU training...")
            train_df = train_df.groupby("label", group_keys=False).apply(
                lambda x: x.sample(n=max_train // 2, random_state=self.seed)
            ).reset_index(drop=True)

        max_val = self.lstm_cfg.get("max_val_samples")
        if max_val and max_val < len(val_df):
            val_df = val_df.groupby("label", group_keys=False).apply(
                lambda x: x.sample(n=max_val // 2, random_state=self.seed)
            ).reset_index(drop=True)

        train_texts = train_df["cleaned_review"].fillna("").tolist()
        val_texts = val_df["cleaned_review"].fillna("").tolist()

        train_labels = train_df["label"].values.astype(np.float32)
        val_labels = val_df["label"].values.astype(np.float32)

        logger.info(f"Transforming {len(train_texts)} train and {len(val_texts)} val texts into integer token matrices...")
        X_train = self.tokenizer.transform(train_texts)
        X_val = self.tokenizer.transform(val_texts)

        train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.long), torch.tensor(train_labels))
        val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.long), torch.tensor(val_labels))

        batch_size = self.lstm_cfg["batch_size"]
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        logger.info(f"DataLoaders ready: Train batches = {len(train_loader)}, Val batches = {len(val_loader)}")
        return train_loader, val_loader

    def evaluate_model(self, model: nn.Module, data_loader: DataLoader, criterion: nn.Module) -> Dict[str, float]:
        """Evaluate model on a DataLoader and compute loss and performance metrics."""
        model.eval()
        total_loss = 0.0
        all_preds = []
        all_probs = []
        all_targets = []

        with torch.no_grad():
            for x_batch, y_batch in data_loader:
                x_batch = x_batch.to(self.device)
                y_batch = y_batch.to(self.device).unsqueeze(1)

                logits = model(x_batch)
                loss = criterion(logits, y_batch)
                total_loss += loss.item() * len(y_batch)

                probs = torch.sigmoid(logits).cpu().numpy().flatten()
                preds = (probs >= 0.5).astype(int)

                all_probs.extend(probs)
                all_preds.extend(preds)
                all_targets.extend(y_batch.cpu().numpy().flatten().astype(int))

        avg_loss = total_loss / len(all_targets)
        acc = accuracy_score(all_targets, all_preds)
        prec = precision_score(all_targets, all_preds, zero_division=0)
        rec = recall_score(all_targets, all_preds, zero_division=0)
        f1 = f1_score(all_targets, all_preds, zero_division=0)
        roc_auc = roc_auc_score(all_targets, all_probs)

        return {
            "loss": float(avg_loss),
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "roc_auc": float(roc_auc)
        }

    def train(self) -> Dict[str, Any]:
        """Execute full training loop with early stopping, model checkpointing, and history logging."""
        train_loader, val_loader = self.prepare_data_loaders()

        vocab_size = min(len(self.tokenizer.word2idx), self.lstm_cfg["vocab_size"])
        model = SentimentLSTM(
            vocab_size=vocab_size,
            embedding_dim=self.lstm_cfg["embedding_dim"],
            hidden_dim=self.lstm_cfg["hidden_dim"],
            num_layers=self.lstm_cfg["num_layers"],
            bidirectional=self.lstm_cfg["bidirectional"],
            dropout=self.lstm_cfg["dropout"],
            padding_idx=self.tokenizer.pad_idx
        ).to(self.device)

        logger.info(f"Instantiated SentimentLSTM model with {sum(p.numel() for p in model.parameters() if p.requires_grad):,} trainable parameters.")

        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=self.lstm_cfg["learning_rate"],
            weight_decay=self.lstm_cfg.get("weight_decay", 1e-5)
        )

        max_epochs = self.lstm_cfg.get("max_epochs", 6)
        patience = self.lstm_cfg.get("patience", 2)

        history = {
            "train_loss": [],
            "train_acc": [],
            "val_loss": [],
            "val_acc": [],
            "val_f1": [],
            "val_roc_auc": []
        }

        best_val_loss = float("inf")
        best_val_metrics = {}
        epochs_no_improve = 0
        best_model_state = None

        logger.info(f"Starting LSTM training for up to {max_epochs} epochs with patience {patience}...")
        start_time = time.time()

        for epoch in range(1, max_epochs + 1):
            epoch_start = time.time()
            model.train()
            train_loss_total = 0.0
            train_correct = 0
            train_total = 0

            for x_batch, y_batch in train_loader:
                x_batch = x_batch.to(self.device)
                y_batch = y_batch.to(self.device).unsqueeze(1)

                optimizer.zero_grad()
                logits = model(x_batch)
                loss = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()

                train_loss_total += loss.item() * len(y_batch)
                preds = (torch.sigmoid(logits) >= 0.5).float()
                train_correct += (preds == y_batch).sum().item()
                train_total += len(y_batch)

            train_loss = train_loss_total / train_total
            train_acc = train_correct / train_total

            val_metrics = self.evaluate_model(model, val_loader, criterion)
            val_loss = val_metrics["loss"]
            val_acc = val_metrics["accuracy"]
            val_f1 = val_metrics["f1"]
            val_roc = val_metrics["roc_auc"]

            history["train_loss"].append(train_loss)
            history["train_acc"].append(train_acc)
            history["val_loss"].append(val_loss)
            history["val_acc"].append(val_acc)
            history["val_f1"].append(val_f1)
            history["val_roc_auc"].append(val_roc)

            epoch_time = time.time() - epoch_start
            logger.info(
                f"Epoch [{epoch:02d}/{max_epochs:02d}] ({epoch_time:.1f}s) - "
                f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc*100:.2f}% | "
                f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc*100:.2f}%, Val F1: {val_f1:.4f}, Val AUC: {val_roc:.4f}"
            )

            # Check early stopping on validation loss
            if val_loss < best_val_loss - 1e-4:
                best_val_loss = val_loss
                best_val_metrics = val_metrics
                epochs_no_improve = 0
                best_model_state = model.state_dict().copy()
                logger.info(f"  -> Validation loss improved to {val_loss:.4f}. Saved best model checkpoint.")
            else:
                epochs_no_improve += 1
                logger.info(f"  -> No improvement in val loss for {epochs_no_improve}/{patience} consecutive epochs.")
                if epochs_no_improve >= patience:
                    logger.info("  -> Early stopping triggered.")
                    break

        total_training_time = time.time() - start_time
        logger.info(f"Training completed in {total_training_time:.2f}s.")

        # Save best model checkpoint
        checkpoint_path = os.path.join(self.models_dir, "lstm_model.pt")
        save_payload = {
            "state_dict": best_model_state if best_model_state is not None else model.state_dict(),
            "model_config": {
                "vocab_size": vocab_size,
                "embedding_dim": self.lstm_cfg["embedding_dim"],
                "hidden_dim": self.lstm_cfg["hidden_dim"],
                "num_layers": self.lstm_cfg["num_layers"],
                "bidirectional": self.lstm_cfg["bidirectional"],
                "dropout": self.lstm_cfg["dropout"],
                "padding_idx": self.tokenizer.pad_idx,
            },
            "best_val_metrics": best_val_metrics,
            "training_time_sec": total_training_time
        }
        torch.save(save_payload, checkpoint_path)
        logger.info(f"Best LSTM model saved successfully to {checkpoint_path}")

        # Save training history JSON
        history_path = os.path.join(self.models_dir, "lstm_training_history.json")
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        logger.info(f"Training history saved to {history_path}")

        # Plot training curves
        self.plot_training_history(history)

        return best_val_metrics

    def plot_training_history(self, history: Dict[str, list]):
        """Render and save loss and accuracy convergence plots across epochs."""
        epochs = list(range(1, len(history["train_loss"]) + 1))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

        # Loss Plot
        ax1.plot(epochs, history["train_loss"], "o-", color="#1f77b4", label="Train Loss", linewidth=2)
        ax1.plot(epochs, history["val_loss"], "s--", color="#ff7f0e", label="Validation Loss", linewidth=2)
        ax1.set_title("LSTM Loss Convergence Across Epochs", fontsize=13, fontweight="bold")
        ax1.set_xlabel("Epoch", fontsize=11)
        ax1.set_ylabel("Binary Cross-Entropy Loss", fontsize=11)
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.legend(loc="upper right", frameon=True)

        # Accuracy Plot
        ax2.plot(epochs, [a * 100 for a in history["train_acc"]], "o-", color="#2ca02c", label="Train Accuracy", linewidth=2)
        ax2.plot(epochs, [a * 100 for a in history["val_acc"]], "s--", color="#d62728", label="Validation Accuracy", linewidth=2)
        ax2.set_title("LSTM Accuracy Convergence Across Epochs", fontsize=13, fontweight="bold")
        ax2.set_xlabel("Epoch", fontsize=11)
        ax2.set_ylabel("Accuracy (%)", fontsize=11)
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend(loc="lower right", frameon=True)

        plt.tight_layout()
        plot_path = os.path.join(self.figures_dir, "lstm_training_history.png")
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"LSTM training curve plot saved to {plot_path}")


def main():
    trainer = LSTMTrainer()
    val_metrics = trainer.train()
    print("\n--- LSTM Training Finished Successfully ---")
    print(f"Validation Metrics: {json.dumps(val_metrics, indent=2)}")


if __name__ == "__main__":
    main()
