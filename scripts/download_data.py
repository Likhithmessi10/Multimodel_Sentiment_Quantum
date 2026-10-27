"""
Automated downloader for the public IMDb 50,000 Movie Reviews Sentiment Dataset.
"""
import os
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_URLS = [
    "https://raw.githubusercontent.com/Ankit152/IMDB-sentiment-analysis/master/IMDB-Dataset.csv",
    "https://raw.githubusercontent.com/RasikaBhadre/IMDB-Sentiment-Analysis/master/IMDB%20Dataset.csv",
    "https://github.com/laxmimerit/All-CSV-ML-Data-Files-Download/raw/master/IMDB-Dataset.csv"
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "imdb_dataset.csv")

def download_imdb():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 10000000:
        logger.info(f"IMDb dataset already exists at: {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE)} bytes)")
        return OUTPUT_FILE

    for url in DATA_URLS:
        try:
            logger.info(f"Downloading IMDb dataset from: {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(OUTPUT_FILE, "wb") as f_out:
                f_out.write(resp.read())
            size = os.path.getsize(OUTPUT_FILE)
            if size > 1000000:
                logger.info(f"Successfully downloaded IMDb dataset ({size} bytes) to {OUTPUT_FILE}")
                return OUTPUT_FILE
        except Exception as e:
            logger.warning(f"Download failed from {url}: {e}. Trying next mirror...")

    raise RuntimeError("Failed to download IMDb dataset from all mirrors.")

if __name__ == "__main__":
    download_imdb()
