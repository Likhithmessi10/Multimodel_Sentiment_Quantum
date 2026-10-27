"""
scraper.py - Dynamic Multi-Source Real-Time News Scraper & Data Cleaning Engine.

Fetches breaking news headlines across multiple top-tier global RSS feeds:
- BBC News (World / Top Stories)
- CNN News (Top News)
- Al Jazeera (News Feed)
- TechCrunch (Technology)
- NPR News (World / General)

Features:
- Robust multi-threaded / concurrent network fetching with per-source timeout handling
- Automated HTML tag sanitization, entity unescaping, and duplicate suppression
- Dynamic background refresh scheduler to continuously stream new headlines
"""

import re
import html
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import requests
import feedparser
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsScraper")

RSS_FEEDS = {
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    "CNN": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "NPR News": "https://feeds.npr.org/1001/rss.xml"
}

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def clean_headline_text(raw_text: str) -> str:
    """Sanitize raw headline text, stripping HTML, special symbols, and excess whitespace."""
    if not raw_text:
        return ""
    # Strip HTML tags
    soup = BeautifulSoup(raw_text, "html.parser")
    cleaned = soup.get_text(separator=" ")
    # Unescape HTML entities (&amp;, &#39;, etc.)
    cleaned = html.unescape(cleaned)
    # Remove URL links embedded inside headline
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def infer_category(title: str) -> str:
    """Assign broad topic categories using robust whole-word regex matching."""
    t_lower = title.lower()
    tech_kw = [r"\btech\b", r"\bai\b", r"\bsoftware\b", r"\bcyber\b", r"\brobot\b", r"\bgoogle\b", r"\bapple\b", r"\bmicrosoft\b", r"\bchip\b"]
    politics_kw = [r"\bpolitics\b", r"\belection\b", r"\bpresident\b", r"\blaw\b", r"\bparliament\b", r"\bcongress\b", r"\bvote\b", r"\bsenate\b"]
    world_kw = [r"\bwar\b", r"\bmilitary\b", r"\bstrike\b", r"\bconflict\b", r"\bpeace\b", r"\btreaty\b", r"\bgaza\b", r"\bukraine\b", r"\bworld\b"]
    business_kw = [r"\bmarket\b", r"\beconomy\b", r"\bstock\b", r"\bbank\b", r"\binflation\b", r"\bprofit\b", r"\bgrowth\b", r"\bbusiness\b"]

    if any(re.search(p, t_lower) for p in tech_kw):
        return "Technology"
    elif any(re.search(p, t_lower) for p in politics_kw):
        return "Politics"
    elif any(re.search(p, t_lower) for p in world_kw):
        return "World"
    elif any(re.search(p, t_lower) for p in business_kw):
        return "Business"
    return "General"


def fetch_source_feed(source_name: str, feed_url: str, timeout: int = 8) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed safely with strict timeout protection."""
    articles = []
    try:
        resp = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"[-] Source {source_name} returned status code {resp.status_code}")
            return []
        
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:25]:
            raw_title = entry.get("title", "")
            title = clean_headline_text(raw_title)
            if not title or len(title) < 10:
                continue

            link = entry.get("link", "")
            published_parsed = entry.get("published_parsed")
            if published_parsed:
                pub_dt = datetime(*published_parsed[:6])
                published_str = pub_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                published_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            summary = clean_headline_text(entry.get("summary", ""))

            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary[:250] if summary else "",
                "link": link,
                "published": published_str,
                "category": infer_category(title),
                "timestamp": time.time()
            })
        logger.info(f"[+] Successfully fetched {len(articles)} articles from {source_name}.")
    except Exception as e:
        logger.error(f"[-] Network/parser error fetching {source_name}: {e}")
    return articles


class DynamicNewsAggregator:
    """
    Thread-safe dynamic news aggregator that polls multiple sources concurrently 
    and maintains an in-memory deduplicated cache of real-time headlines.
    """
    def __init__(self, refresh_interval_seconds: int = 120):
        self.refresh_interval = refresh_interval_seconds
        self.cache: List[Dict[str, Any]] = []
        self.seen_links = set()
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_refresh_time: Optional[str] = None

    def refresh_now(self) -> List[Dict[str, Any]]:
        """Perform an immediate refresh of all sources."""
        all_new_articles = []
        threads = []
        results = []

        def worker(s_name, s_url):
            arts = fetch_source_feed(s_name, s_url)
            results.extend(arts)

        for s_name, s_url in RSS_FEEDS.items():
            t = threading.Thread(target=worker, args=(s_name, s_url), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        with self.lock:
            new_unique = 0
            for art in results:
                identifier = art["link"] or art["title"]
                if identifier not in self.seen_links:
                    self.seen_links.add(identifier)
                    self.cache.insert(0, art)
                    all_new_articles.append(art)
                    new_unique += 1

            # Cap cache size to latest 300 articles
            if len(self.cache) > 300:
                self.cache = self.cache[:300]

            self.last_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"[+] Aggregator refreshed: {new_unique} new articles added. Cache holds {len(self.cache)}.")
        return list(self.cache)

    def get_articles(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the latest cached articles safely."""
        with self.lock:
            if not self.cache:
                # First run initialization
                pass
            return list(self.cache[:limit])

    def start_background_loop(self):
        """Start dynamic background polling thread."""
        if self._thread and self._thread.is_alive():
            return

        def loop():
            logger.info("[*] Starting dynamic news background polling loop...")
            while not self._stop_event.is_set():
                try:
                    self.refresh_now()
                except Exception as e:
                    logger.error(f"[-] Error in background news loop: {e}")
                self._stop_event.wait(self.refresh_interval)

        self._stop_event.clear()
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop_background_loop(self):
        """Stop background polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)


# Global singleton instance for easy import across modules
global_aggregator = DynamicNewsAggregator(refresh_interval_seconds=180)


if __name__ == "__main__":
    print("[*] Testing dynamic scraper module...")
    arts = global_aggregator.refresh_now()
    print(f"[+] Fetched {len(arts)} total articles.")
    for i, a in enumerate(arts[:5]):
        print(f" {i+1}. [{a['source']}] ({a['category']}) {a['title'][:80]}...")
