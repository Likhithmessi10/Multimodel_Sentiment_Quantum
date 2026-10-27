"""
run_pipeline.py - Master Pipeline Execution Script
Executes the end-to-end sentiment analysis pipeline:
1. Data loading and validation
2. Text preprocessing and train/val/test splitting
3. Vectorizer & Tokenizer fitting
4. Classical ML training (Logistic Regression, Naive Bayes)
5. Deep Learning training (Bidirectional LSTM)
6. Comprehensive test set evaluation & visualization generation
"""

import os
import sys
import time
import argparse
import logging

from src.data_loader import ensure_dataset_available
from src.preprocessing import SentimentPreprocessor
from src.train_ml import ClassicalMLTrainer
from src.train_lstm import LSTMTrainer
from src.evaluate import ModelEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_full_pipeline(skip_lstm: bool = False):
    total_start = time.time()
    logger.info("================================================================")
    logger.info("STARTING END-TO-END SENTIMENT ANALYSIS PIPELINE")
    logger.info("================================================================")

    # Step 1: Ensure dataset
    logger.info("\n--- STEP 1: Dataset Verification ---")
    dataset_path = ensure_dataset_available()
    logger.info(f"Verified dataset at: {dataset_path}")

    # Step 2: Preprocessing
    logger.info("\n--- STEP 2: Text Preprocessing & Vectorization ---")
    preprocessor = SentimentPreprocessor()
    preprocessor.run()

    # Step 3: Classical ML Models
    logger.info("\n--- STEP 3: Training Classical ML Classifiers ---")
    ml_trainer = ClassicalMLTrainer()
    ml_trainer.train_all()

    # Step 4: LSTM Deep Learning Model
    if not skip_lstm:
        logger.info("\n--- STEP 4: Training Bidirectional LSTM Deep Learning Model ---")
        lstm_trainer = LSTMTrainer()
        lstm_trainer.train()
    else:
        logger.info("\n--- STEP 4: Skipped LSTM training per flag ---")

    # Step 5: Test Set Evaluation & Comparison
    logger.info("\n--- STEP 5: Benchmarking All Models on Test Split ---")
    evaluator = ModelEvaluator()
    df_comparison = evaluator.run_benchmark()

    elapsed = time.time() - total_start
    logger.info("\n================================================================")
    logger.info(f"PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f}s")
    logger.info("================================================================")
    print("\nModel Comparison Summary on 7,500 Unseen Test Reviews:")
    print(df_comparison.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Sentiment Analysis Pipeline")
    parser.add_argument("--skip-lstm", action="store_true", help="Skip LSTM training if already trained")
    args = parser.parse_args()

    run_full_pipeline(skip_lstm=args.skip_lstm)
