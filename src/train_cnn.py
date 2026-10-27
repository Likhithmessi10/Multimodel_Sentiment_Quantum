"""
train_cnn.py - PyTorch 1D-CNN (TextCNN) Sentiment Classifier Training
Multi-scale 1D Convolutional Neural Network (Kim 2014) for text sentiment classification.
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.data_loader import load_config
from src.preprocessing import TextTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "config.yaml"
)


class TextCNN(nn.Module):
    """
    1D-Convolutional Neural Network for Text Sentiment Classification (Kim 2014).
    Uses multi-scale convolutional kernels (sizes 2, 3, 4, 5) followed by max-over-time pooling.
    """
    def __init__(
        self,
        vocab_size: int = 15000,
        embedding_dim: int = 128,
        num_filters: int = 64,
        filter_sizes: list = [2, 3, 4, 5],
        dropout: float = 0.4,
        padding_idx: int = 0
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.num_filters = num_filters
        self.filter_sizes = filter_sizes
        
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=padding_idx)
        self.convs = nn.ModuleList([
            nn.Conv1d(in_channels=embedding_dim, out_channels=num_filters, kernel_size=fs)
            for fs in filter_sizes
        ])
        self.dropout = nn.Dropout(dropout)
        total_filters = num_filters * len(filter_sizes)
        self.fc1 = nn.Linear(total_filters, 64)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch_size, seq_len)
        embedded = self.embedding(x)  # (batch_size, seq_len, embed_dim)
        embedded = embedded.permute(0, 2, 1)  # (batch_size, embed_dim, seq_len)
        
        pooled_outputs = []
        for conv in self.convs:
            # conv: (batch_size, num_filters, seq_len - filter_size + 1)
            c = F.relu(conv(embedded))
            # max-over-time pooling: (batch_size, num_filters)
            p = F.max_pool1d(c, kernel_size=c.shape[2]).squeeze(2)
            pooled_outputs.append(p)
            
        cat = torch.cat(pooled_outputs, dim=1)  # (batch_size, total_filters)
        h = self.dropout(F.relu(self.fc1(cat)))
        logits = self.fc2(h)
        return logits


class TextCNNTrainer:
    """Handles end-to-end training and checkpointing for TextCNN."""
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config = load_config(config_path)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.processed_dir = os.path.join(self.base_dir, self.config["dataset"]["processed_dir"])
        self.models_dir = os.path.join(self.base_dir, self.config["paths"]["models_dir"])
        os.makedirs(self.models_dir, exist_ok=True)

        self.device = torch.device("cpu")
        self.tokenizer = None

    def train(self, epochs: int = 5, batch_size: int = 128, lr: float = 1e-3) -> Dict[str, Any]:
        logger.info("Loading processed datasets...")
        train_df = pd.read_csv(os.path.join(self.processed_dir, "train.csv"))
        val_df = pd.read_csv(os.path.join(self.processed_dir, "val.csv"))

        tokenizer_path = os.path.join(self.models_dir, "tokenizer.joblib")
        if not os.path.exists(tokenizer_path):
            raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}")
        self.tokenizer = joblib.load(tokenizer_path)

        logger.info("Transforming texts into token sequences...")
        X_train = self.tokenizer.transform(train_df["cleaned_review"].tolist())
        y_train = train_df["label"].values.astype(np.float32)

        X_val = self.tokenizer.transform(val_df["cleaned_review"].tolist())
        y_val = val_df["label"].values.astype(np.float32)

        train_ds = TensorDataset(torch.tensor(X_train, dtype=torch.long), torch.tensor(y_train, dtype=torch.float32).unsqueeze(1))
        val_ds = TensorDataset(torch.tensor(X_val, dtype=torch.long), torch.tensor(y_val, dtype=torch.float32).unsqueeze(1))

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        model = TextCNN(
            vocab_size=self.tokenizer.max_vocab_size,
            embedding_dim=128,
            num_filters=64,
            filter_sizes=[2, 3, 4, 5],
            dropout=0.4,
            padding_idx=self.tokenizer.pad_idx
        ).to(self.device)

        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)

        logger.info(f"Starting TextCNN training ({epochs} epochs, {len(train_loader)} batches/epoch)...")
        best_val_acc = 0.0
        best_metrics = {}

        for epoch in range(1, epochs + 1):
            model.train()
            train_loss = 0.0
            t0 = time.time()

            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                logits = model(batch_x)
                loss = criterion(logits, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            train_loss /= len(train_loader)

            # Evaluate on validation
            model.eval()
            val_preds, val_targets = [], []
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x = batch_x.to(self.device)
                    logits = model(batch_x)
                    probs = torch.sigmoid(logits).cpu().numpy()
                    val_preds.extend(probs)
                    val_targets.extend(batch_y.numpy())

            val_preds = np.array(val_preds).flatten()
            val_targets = np.array(val_targets).flatten()
            val_binary = (val_preds >= 0.5).astype(int)

            val_acc = accuracy_score(val_targets, val_binary)
            val_f1 = f1_score(val_targets, val_binary)
            val_auc = roc_auc_score(val_targets, val_preds)

            elapsed = round(time.time() - t0, 1)
            logger.info(f"Epoch {epoch}/{epochs} ({elapsed}s) - Loss: {train_loss:.4f} | Val Acc: {val_acc*100:.2f}% | Val F1: {val_f1:.4f} | Val AUC: {val_auc:.4f}")

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_metrics = {
                    "accuracy": float(val_acc),
                    "f1_score": float(val_f1),
                    "roc_auc": float(val_auc),
                    "epoch": epoch
                }
                # Save model
                save_path = os.path.join(self.models_dir, "text_cnn.pt")
                torch.save(model.state_dict(), save_path)
                logger.info(f"[+] Saved new best TextCNN checkpoint to {save_path}")

        logger.info(f"[+] TextCNN training complete! Best Val Acc: {best_val_acc*100:.2f}%")
        return best_metrics


if __name__ == "__main__":
    trainer = TextCNNTrainer()
    metrics = trainer.train(epochs=4, batch_size=128)
    print("Final TextCNN Metrics:", metrics)
