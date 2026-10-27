"""
evaluate.py - Benchmark and compare all trained sentiment analysis models.
Evaluates Logistic Regression, Multinomial Naive Bayes, and Bidirectional LSTM on the held-out test split.
Generates comprehensive performance metrics, ROC curves, confusion matrices, and comparison tables.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, roc_curve, precision_recall_curve
)

from src.data_loader import load_config
from src.preprocessing import TextTokenizer
from src.train_lstm import SentimentLSTM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "config.yaml"
)


class ModelEvaluator:
    """Evaluates and compares all trained models on the held-out test set."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config = load_config(config_path)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.processed_dir = os.path.join(self.base_dir, self.config["dataset"]["processed_dir"])
        self.models_dir = os.path.join(self.base_dir, self.config["paths"]["models_dir"])
        self.metrics_dir = os.path.join(self.base_dir, self.config["paths"]["metrics_dir"])
        self.figures_dir = os.path.join(self.base_dir, self.config["paths"]["figures_dir"])

        os.makedirs(self.metrics_dir, exist_ok=True)
        os.makedirs(self.figures_dir, exist_ok=True)

        # Load test data
        test_path = os.path.join(self.processed_dir, "test.csv")
        logger.info(f"Loading test set from {test_path}...")
        self.test_df = pd.read_csv(test_path)
        self.test_texts = self.test_df["cleaned_review"].fillna("").tolist()
        self.y_true = self.test_df["label"].values.astype(int)
        logger.info(f"Test set loaded: {len(self.y_true)} samples (Positive: {np.sum(self.y_true == 1)}, Negative: {np.sum(self.y_true == 0)})")

        # Load TF-IDF Vectorizer
        tfidf_path = os.path.join(self.models_dir, "tfidf_vectorizer.joblib")
        logger.info(f"Loading TF-IDF vectorizer from {tfidf_path}...")
        self.tfidf = joblib.load(tfidf_path)
        self.X_test_tfidf = self.tfidf.transform(self.test_texts)

        # Load Tokenizer
        tokenizer_path = os.path.join(self.models_dir, "tokenizer.joblib")
        logger.info(f"Loading tokenizer from {tokenizer_path}...")
        self.tokenizer = joblib.load(tokenizer_path)
        self.X_test_seq = self.tokenizer.transform(self.test_texts)

    def evaluate_logistic_regression(self) -> Tuple[Dict[str, float], np.ndarray, np.ndarray]:
        """Evaluate trained Logistic Regression model."""
        model_path = os.path.join(self.models_dir, "logistic_regression.joblib")
        logger.info(f"Evaluating Logistic Regression from {model_path}...")
        model = joblib.load(model_path)

        y_prob = model.predict_proba(self.X_test_tfidf)[:, 1]
        y_pred = model.predict(self.X_test_tfidf)

        metrics = self._compute_metrics(self.y_true, y_pred, y_prob, "Logistic Regression")
        return metrics, y_pred, y_prob

    def evaluate_naive_bayes(self) -> Tuple[Dict[str, float], np.ndarray, np.ndarray]:
        """Evaluate trained Multinomial Naive Bayes model."""
        model_path = os.path.join(self.models_dir, "naive_bayes.joblib")
        logger.info(f"Evaluating Multinomial Naive Bayes from {model_path}...")
        model = joblib.load(model_path)

        y_prob = model.predict_proba(self.X_test_tfidf)[:, 1]
        y_pred = model.predict(self.X_test_tfidf)

        metrics = self._compute_metrics(self.y_true, y_pred, y_prob, "Multinomial Naive Bayes")
        return metrics, y_pred, y_prob

    def evaluate_lstm(self) -> Tuple[Dict[str, float], np.ndarray, np.ndarray]:
        """Evaluate trained PyTorch Bidirectional LSTM model."""
        checkpoint_path = os.path.join(self.models_dir, "lstm_model.pt")
        logger.info(f"Evaluating Bidirectional LSTM from {checkpoint_path}...")
        checkpoint = torch.load(checkpoint_path, map_location=torch.device("cpu"), weights_only=False)

        cfg = checkpoint["model_config"]
        model = SentimentLSTM(
            vocab_size=cfg["vocab_size"],
            embedding_dim=cfg["embedding_dim"],
            hidden_dim=cfg["hidden_dim"],
            num_layers=cfg["num_layers"],
            bidirectional=cfg["bidirectional"],
            dropout=cfg["dropout"],
            padding_idx=cfg["padding_idx"]
        )
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()

        # Batch inference
        batch_size = 128
        y_probs = []
        with torch.no_grad():
            for i in range(0, len(self.X_test_seq), batch_size):
                batch_x = torch.tensor(self.X_test_seq[i:i + batch_size], dtype=torch.long)
                probs = model.predict_proba(batch_x).cpu().numpy().flatten()
                y_probs.extend(probs)

        y_prob = np.array(y_probs)
        y_pred = (y_prob >= 0.5).astype(int)

        metrics = self._compute_metrics(self.y_true, y_pred, y_prob, "Bidirectional LSTM")
        return metrics, y_pred, y_prob

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray, model_name: str) -> Dict[str, Any]:
        """Calculate standardized classification evaluation metrics."""
        acc = accuracy_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_true, y_prob)
        cm = confusion_matrix(y_true, y_pred).tolist()

        logger.info(
            f"[{model_name}] Accuracy: {acc*100:.2f}%, Precision: {prec*100:.2f}%, "
            f"Recall: {rec*100:.2f}%, F1: {f1:.4f}, ROC-AUC: {roc_auc:.4f}"
        )

        return {
            "model_name": model_name,
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
            "confusion_matrix": cm,
            "test_samples": len(y_true)
        }

    def run_benchmark(self) -> pd.DataFrame:
        """Run complete benchmark on all 3 models, save tables, and generate figures."""
        logger.info("Executing comprehensive model benchmark...")

        lr_metrics, lr_pred, lr_prob = self.evaluate_logistic_regression()
        nb_metrics, nb_pred, nb_prob = self.evaluate_naive_bayes()
        lstm_metrics, lstm_pred, lstm_prob = self.evaluate_lstm()

        all_metrics = [lr_metrics, nb_metrics, lstm_metrics]

        # Save metrics JSON
        metrics_json_path = os.path.join(self.metrics_dir, "evaluation_metrics.json")
        with open(metrics_json_path, "w", encoding="utf-8") as f:
            json.dump(all_metrics, f, indent=2)
        logger.info(f"Evaluation metrics JSON saved to {metrics_json_path}")

        # Build comparison DataFrame
        comparison_rows = []
        for m in all_metrics:
            comparison_rows.append({
                "Model": m["model_name"],
                "Accuracy (%)": round(m["accuracy"] * 100, 2),
                "Precision (%)": round(m["precision"] * 100, 2),
                "Recall (%)": round(m["recall"] * 100, 2),
                "F1 Score": round(m["f1_score"], 4),
                "ROC-AUC": round(m["roc_auc"], 4)
            })

        df_comparison = pd.DataFrame(comparison_rows)
        csv_path = os.path.join(self.metrics_dir, "model_comparison.csv")
        df_comparison.to_csv(csv_path, index=False)
        logger.info(f"Model comparison table saved to {csv_path}")

        # Generate Visualizations
        self.plot_roc_curves(
            {
                "Logistic Regression": lr_prob,
                "Multinomial Naive Bayes": nb_prob,
                "Bidirectional LSTM": lstm_prob
            }
        )

        self.plot_confusion_matrices(
            {
                "Logistic Regression": np.array(lr_metrics["confusion_matrix"]),
                "Multinomial Naive Bayes": np.array(nb_metrics["confusion_matrix"]),
                "Bidirectional LSTM": np.array(lstm_metrics["confusion_matrix"])
            }
        )

        self.plot_metric_comparison(df_comparison)

        return df_comparison

    def plot_roc_curves(self, probs_dict: Dict[str, np.ndarray]):
        """Plot receiver operating characteristic (ROC) curves for all 3 models."""
        plt.figure(figsize=(8, 6))
        colors = {"Logistic Regression": "#1f77b4", "Multinomial Naive Bayes": "#ff7f0e", "Bidirectional LSTM": "#2ca02c"}

        for name, probs in probs_dict.items():
            fpr, tpr, _ = roc_curve(self.y_true, probs)
            auc = roc_auc_score(self.y_true, probs)
            plt.plot(fpr, tpr, label=f"{name} (AUC = {auc:.4f})", color=colors.get(name, "black"), linewidth=2)

        plt.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Chance (AUC = 0.5000)")
        plt.title("ROC Curves Comparison Across Models", fontsize=14, fontweight="bold")
        plt.xlabel("False Positive Rate", fontsize=12)
        plt.ylabel("True Positive Rate", fontsize=12)
        plt.legend(loc="lower right", frameon=True, fontsize=10)
        plt.grid(True, linestyle="--", alpha=0.5)

        fig_path = os.path.join(self.figures_dir, "roc_curves.png")
        plt.savefig(fig_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved ROC curves plot to {fig_path}")

    def plot_confusion_matrices(self, cm_dict: Dict[str, np.ndarray]):
        """Plot side-by-side confusion matrices for all 3 models."""
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

        for ax, (name, cm) in zip(axes, cm_dict.items()):
            im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
            ax.set_title(name, fontsize=12, fontweight="bold")
            tick_marks = [0, 1]
            ax.set_xticks(tick_marks)
            ax.set_xticklabels(["Negative", "Positive"])
            ax.set_yticks(tick_marks)
            ax.set_yticklabels(["Negative", "Positive"])
            ax.set_ylabel("True Label")
            ax.set_xlabel("Predicted Label")

            thresh = cm.max() / 2.0
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    ax.text(
                        j, i, f"{cm[i, j]:,}",
                        ha="center", va="center",
                        color="white" if cm[i, j] > thresh else "black",
                        fontweight="bold"
                    )

        plt.tight_layout()
        fig_path = os.path.join(self.figures_dir, "confusion_matrices.png")
        plt.savefig(fig_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved confusion matrices plot to {fig_path}")

    def plot_metric_comparison(self, df_comp: pd.DataFrame):
        """Plot bar chart comparing core metrics across the three models."""
        metrics_to_plot = ["Accuracy (%)", "Precision (%)", "Recall (%)"]
        x = np.arange(len(df_comp))
        width = 0.25

        fig, ax = plt.subplots(figsize=(9, 5))
        for i, metric in enumerate(metrics_to_plot):
            ax.bar(x + (i - 1) * width, df_comp[metric], width, label=metric)

        ax.set_ylabel("Score (%)", fontsize=12)
        ax.set_title("Performance Metrics Comparison Across Models", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(df_comp["Model"], fontsize=11)
        ax.set_ylim(70, 100)
        ax.legend(loc="lower right")
        ax.grid(axis="y", linestyle="--", alpha=0.5)

        fig_path = os.path.join(self.figures_dir, "model_comparison.png")
        plt.savefig(fig_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved model comparison plot to {fig_path}")


def main():
    evaluator = ModelEvaluator()
    df_comparison = evaluator.run_benchmark()
    print("\n================ FINAL TEST BENCHMARK RESULTS ================")
    print(df_comparison.to_string(index=False))
    print("==============================================================\n")


if __name__ == "__main__":
    main()
