"""
Training module for classical machine learning models:
1. Logistic Regression with TF-IDF features
2. Multinomial Naive Bayes with TF-IDF features
"""
from typing import Dict, Any, Tuple
import os
import time
import json
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score

from src.data_loader import load_config, DEFAULT_CONFIG_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class MLTrainer:
    """Trains and serializes Logistic Regression and Multinomial Naive Bayes models."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config = load_config(config_path)
        self.processed_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.config["dataset"]["processed_dir"]
        )
        self.models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.config["paths"]["models_dir"]
        )
        os.makedirs(self.models_dir, exist_ok=True)

        self.lr_config = self.config["models"]["logistic_regression"]
        self.nb_config = self.config["models"]["naive_bayes"]

    def train_models(self) -> Dict[str, Any]:
        """Load data, vectorize text, and train both classical models."""
        logger.info("Loading processed train and validation datasets...")
        train_df = pd.read_csv(os.path.join(self.processed_dir, "train.csv"))
        val_df = pd.read_csv(os.path.join(self.processed_dir, "val.csv"))

        tfidf_path = os.path.join(self.models_dir, "tfidf_vectorizer.joblib")
        if not os.path.exists(tfidf_path):
            raise FileNotFoundError(f"TF-IDF vectorizer not found at {tfidf_path}. Run preprocessing first.")

        tfidf = joblib.load(tfidf_path)
        logger.info("Transforming texts into TF-IDF feature matrices...")
        X_train = tfidf.transform(train_df["cleaned_review"])
        X_val = tfidf.transform(val_df["cleaned_review"])
        y_train = train_df["label"].values
        y_val = val_df["label"].values

        training_results = {}

        # -------------------------------------------------------------
        # 1. Train Logistic Regression
        # -------------------------------------------------------------
        logger.info("Training Logistic Regression classifier...")
        lr_start = time.time()
        lr_model = LogisticRegression(
            C=self.lr_config.get("C", 1.0),
            max_iter=self.lr_config.get("max_iter", 1000),
            solver=self.lr_config.get("solver", "lbfgs"),
            random_state=self.lr_config.get("random_state", 42)
        )
        lr_model.fit(X_train, y_train)
        lr_time = time.time() - lr_start

        # Validation evaluation
        lr_val_preds = lr_model.predict(X_val)
        lr_val_probs = lr_model.predict_proba(X_val)[:, 1]
        lr_acc = accuracy_score(y_val, lr_val_preds)
        lr_auc = roc_auc_score(y_val, lr_val_probs)
        lr_f1 = f1_score(y_val, lr_val_preds)

        joblib.dump(lr_model, os.path.join(self.models_dir, "logistic_regression.joblib"))
        logger.info(f"Logistic Regression trained in {lr_time:.2f}s | Val Acc: {lr_acc:.4f} | Val ROC-AUC: {lr_auc:.4f} | Val F1: {lr_f1:.4f}")

        training_results["logistic_regression"] = {
            "training_time_sec": round(lr_time, 2),
            "val_accuracy": round(float(lr_acc), 4),
            "val_roc_auc": round(float(lr_auc), 4),
            "val_f1": round(float(lr_f1), 4)
        }

        # -------------------------------------------------------------
        # 2. Train Multinomial Naive Bayes
        # -------------------------------------------------------------
        logger.info("Training Multinomial Naive Bayes classifier...")
        nb_start = time.time()
        nb_model = MultinomialNB(
            alpha=self.nb_config.get("alpha", 1.0),
            fit_prior=self.nb_config.get("fit_prior", True)
        )
        nb_model.fit(X_train, y_train)
        nb_time = time.time() - nb_start

        # Validation evaluation
        nb_val_preds = nb_model.predict(X_val)
        nb_val_probs = nb_model.predict_proba(X_val)[:, 1]
        nb_acc = accuracy_score(y_val, nb_val_preds)
        nb_auc = roc_auc_score(y_val, nb_val_probs)
        nb_f1 = f1_score(y_val, nb_val_preds)

        joblib.dump(nb_model, os.path.join(self.models_dir, "naive_bayes.joblib"))
        logger.info(f"Multinomial Naive Bayes trained in {nb_time:.2f}s | Val Acc: {nb_acc:.4f} | Val ROC-AUC: {nb_auc:.4f} | Val F1: {nb_f1:.4f}")

        training_results["naive_bayes"] = {
            "training_time_sec": round(nb_time, 2),
            "val_accuracy": round(float(nb_acc), 4),
            "val_roc_auc": round(float(nb_auc), 4),
            "val_f1": round(float(nb_f1), 4)
        }

        return training_results

if __name__ == "__main__":
    trainer = MLTrainer()
    res = trainer.train_models()
    print("Classical ML Training Complete:", res)
