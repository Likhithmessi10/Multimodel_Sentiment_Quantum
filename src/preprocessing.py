"""
Text preprocessing, tokenization, vocabulary generation, and feature extraction module.
Provides clean text sanitization, TF-IDF vectorization, sequence padding for LSTM,
and stratified train/val/test splitting.
"""
from typing import Dict, Any, List, Tuple, Optional
import os
import re
import json
import logging
from collections import Counter
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer

from src.data_loader import load_config, IMDbDataLoader, DEFAULT_CONFIG_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Common English contraction mappings
CONTRACTION_MAP = {
    "won't": "will not",
    "can't": "cannot",
    "n't": " not",
    "'re": " are",
    "'s": " is",
    "'d": " would",
    "'ll": " will",
    "'t": " not",
    "'ve": " have",
    "'m": " am",
    "it's": "it is",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "wasn't": "was not",
    "weren't": "were not"
}

def clean_text(text: str) -> str:
    """Sanitizes raw review text by removing HTML tags, expanding contractions,

    stripping non-alphabetic noise, and normalizing whitespace.
    """
    if not isinstance(text, str):
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Lowercase
    text = text.lower()

    # Expand contractions
    for contraction, expansion in CONTRACTION_MAP.items():
        text = text.replace(contraction, expansion)

    # Remove URLs
    text = re.sub(r"http\S+|www\S+|https\S+", " ", text)

    # Remove non-alphabet characters (retain spaces and basic punctuation tokens)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


class TextTokenizer:
    """Vocabulary builder and integer sequence encoder for deep learning models."""

    def __init__(self, max_vocab_size: int = 15000, max_seq_len: int = 200):
        self.max_vocab_size = max_vocab_size
        self.max_seq_len = max_seq_len
        self.pad_token = "<PAD>"
        self.unk_token = "<UNK>"
        self.pad_idx = 0
        self.unk_idx = 1
        self.word2idx: Dict[str, int] = {self.pad_token: 0, self.unk_token: 1}
        self.idx2word: Dict[int, str] = {0: self.pad_token, 1: self.unk_token}

    def fit(self, texts: List[str]):
        """Build vocabulary from training corpus tokens."""
        logger.info(f"Building tokenizer vocabulary (max size: {self.max_vocab_size})...")
        counter = Counter()
        for text in texts:
            tokens = text.split()
            counter.update(tokens)

        # Most common words up to max_vocab_size - 2 (reserved for PAD and UNK)
        most_common = counter.most_common(self.max_vocab_size - 2)
        for idx, (word, _) in enumerate(most_common, start=2):
            self.word2idx[word] = idx
            self.idx2word[idx] = word

        logger.info(f"Vocabulary constructed: {len(self.word2idx)} unique tokens.")

    def text_to_sequence(self, text: str) -> List[int]:
        """Convert a single text string to a list of integer token IDs."""
        tokens = text.split()
        return [self.word2idx.get(w, self.unk_idx) for w in tokens]

    def pad_sequence(self, seq: List[int]) -> List[int]:
        """Truncate or pad sequence to max_seq_len."""
        if len(seq) >= self.max_seq_len:
            return seq[:self.max_seq_len]
        else:
            return seq + [self.pad_idx] * (self.max_seq_len - len(seq))

    def transform(self, texts: List[str]) -> np.ndarray:
        """Vectorize a list of texts into a 2D integer array of shape (N, max_seq_len)."""
        padded_seqs = [self.pad_sequence(self.text_to_sequence(t)) for t in texts]
        return np.array(padded_seqs, dtype=np.int64)


class SentimentPreprocessor:
    """Coordinates end-to-end dataset cleaning, splitting, vectorization, and serialization."""

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
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)

        self.train_size = self.config["dataset"]["train_size"]
        self.val_size = self.config["dataset"]["val_size"]
        self.test_size = self.config["dataset"]["test_size"]
        self.random_seed = self.config["dataset"]["random_seed"]

        self.max_vocab_size = self.config["preprocessing"]["max_vocab_size"]
        self.max_seq_len = self.config["preprocessing"]["max_seq_len"]
        self.tfidf_max_features = self.config["preprocessing"]["tfidf_max_features"]
        self.tfidf_ngram_range = tuple(self.config["preprocessing"]["tfidf_ngram_range"])

        self.tokenizer = TextTokenizer(max_vocab_size=self.max_vocab_size, max_seq_len=self.max_seq_len)
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=self.tfidf_max_features,
            ngram_range=self.tfidf_ngram_range,
            sublinear_tf=True
        )

    def process_and_split(self) -> Dict[str, Any]:
        """Loads raw IMDb reviews, cleans text, splits into train/val/test, and fits transformers."""
        loader = IMDbDataLoader()
        df = loader.load_raw_data()

        logger.info(f"Cleaning {len(df)} review texts...")
        df["cleaned_review"] = df["review"].apply(clean_text)

        # Filter out empty or whitespace-only records if any
        df = df[df["cleaned_review"].str.len() > 5].reset_index(drop=True)

        # Binary label encoding: positive = 1, negative = 0
        df["label"] = df["sentiment"].map({"positive": 1, "negative": 0}).astype(int)

        # Stratified train/val/test split
        # First split into train and temp (val + test)
        temp_ratio = self.val_size + self.test_size
        train_df, temp_df = train_test_split(
            df,
            test_size=temp_ratio,
            random_state=self.random_seed,
            stratify=df["label"]
        )

        # Split temp into val and test equally (0.15 / 0.30 = 0.5)
        val_df, test_df = train_test_split(
            temp_df,
            test_size=0.5,
            random_state=self.random_seed,
            stratify=temp_df["label"]
        )

        train_df = train_df.reset_index(drop=True)
        val_df = val_df.reset_index(drop=True)
        test_df = test_df.reset_index(drop=True)

        logger.info(
            f"Dataset Partitions -> Train: {len(train_df)} ({len(train_df)/len(df)*100:.1f}%), "
            f"Val: {len(val_df)} ({len(val_df)/len(df)*100:.1f}%), "
            f"Test: {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)"
        )

        # Save partitioned CSVs
        train_df.to_csv(os.path.join(self.processed_dir, "train.csv"), index=False)
        val_df.to_csv(os.path.join(self.processed_dir, "val.csv"), index=False)
        test_df.to_csv(os.path.join(self.processed_dir, "test.csv"), index=False)

        # 1. Fit TF-IDF Vectorizer strictly on train split
        logger.info("Fitting TF-IDF Vectorizer strictly on training data...")
        self.tfidf_vectorizer.fit(train_df["cleaned_review"])
        joblib.dump(self.tfidf_vectorizer, os.path.join(self.models_dir, "tfidf_vectorizer.joblib"))

        # 2. Fit Tokenizer strictly on train split
        logger.info("Fitting Deep Learning Tokenizer strictly on training data...")
        self.tokenizer.fit(train_df["cleaned_review"].tolist())
        joblib.dump(self.tokenizer, os.path.join(self.models_dir, "tokenizer.joblib"))

        metadata = {
            "total_samples": len(df),
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "train_pos": int((train_df["label"] == 1).sum()),
            "train_neg": int((train_df["label"] == 0).sum()),
            "val_pos": int((val_df["label"] == 1).sum()),
            "val_neg": int((val_df["label"] == 0).sum()),
            "test_pos": int((test_df["label"] == 1).sum()),
            "test_neg": int((test_df["label"] == 0).sum()),
            "max_vocab_size": len(self.tokenizer.word2idx),
            "max_seq_len": self.max_seq_len,
            "tfidf_features": len(self.tfidf_vectorizer.get_feature_names_out()),
            "random_seed": self.random_seed
        }

        with open(os.path.join(self.processed_dir, "dataset_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Preprocessing pipeline completed. Metadata saved to {self.processed_dir}")
        return metadata

if __name__ == "__main__":
    preprocessor = SentimentPreprocessor()
    meta = preprocessor.process_and_split()
    print("Preprocessing Metadata:", meta)
