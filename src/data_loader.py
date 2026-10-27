"""
Data loader and dataset summary utilities for IMDb Sentiment Dataset.
"""
from typing import Dict, Any, Optional
import os
import yaml
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config.yaml"
)

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load configuration YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config

class IMDbDataLoader:
    """Loads and inspects the IMDb movie reviews dataset."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config = load_config(config_path)
        self.raw_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.config["dataset"]["raw_path"]
        )
        self.text_col = self.config["dataset"]["text_col"]
        self.label_col = self.config["dataset"]["label_col"]

    def load_raw_data(self) -> pd.DataFrame:
        """Load raw IMDb CSV into a DataFrame."""
        if not os.path.exists(self.raw_path):
            raise FileNotFoundError(
                f"Raw dataset not found at {self.raw_path}. Run scripts/download_data.py first."
            )
        df = pd.read_csv(self.raw_path)
        logger.info(f"Loaded raw IMDb dataset: {len(df)} rows, columns: {df.columns.tolist()}")
        return df

    def get_dataset_statistics(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Compute statistical summary of raw review texts and label distributions."""
        if df is None:
            df = self.load_raw_data()

        label_counts = df[self.label_col].value_counts().to_dict()
        word_counts = df[self.text_col].astype(str).apply(lambda x: len(x.split()))

        stats = {
            "total_samples": len(df),
            "label_distribution": label_counts,
            "mean_word_count": round(float(word_counts.mean()), 2),
            "median_word_count": int(word_counts.median()),
            "min_word_count": int(word_counts.min()),
            "max_word_count": int(word_counts.max()),
            "std_word_count": round(float(word_counts.std()), 2)
        }
        return stats
