"""
scraper.py - Dynamic Multi-Source Real-Time News Scraper & Data Cleaning Engine.

Fetches breaking, live news headlines across top-tier, high-frequency global RSS feeds:
- Google News (Top Stories / World / Business / Technology)
- BBC News (World / Business)
- Al Jazeera (Live News Feed)
- TechCrunch (Technology & AI)
- New York Times (World)
- NPR News (Top Stories)

Features:
- High-frequency live polling with strict freshness filtering (removes stale articles older than 48-72h)
- Strict chronological sorting (newest breaking articles always at the top)
- Dynamic relative time computation (e.g. '12m ago', '2h ago')
- Thread-safe concurrent multi-feed fetching with per-source timeouts
- Automated HTML sanitization, entity unescaping, and duplicate suppression
"""

import re
import html
import time
import calendar
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import requests
import feedparser
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsScraper")

# High-frequency, active, live-updating RSS feeds (No stale or abandoned feeds)
RSS_FEEDS = {
    "Google News Top": "https://news.google.com/rss",
    "Google News Business": "https://news.google.com/rss/headlines/section/topic/BUSINESS",
    "Google News Tech": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
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
    # Unescape HTML entities (&amp;, &#39;, &quot;, etc.)
    cleaned = html.unescape(cleaned)
    # Remove URL links embedded inside headline
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove trailing source attribution patterns (e.g., "- Reuters", "- BBC News", "- The Verge")
    cleaned = re.sub(r"\s+-\s+[A-Za-z0-9\s\.\&]+$", "", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def format_relative_time(epoch_time: float) -> str:
    """Convert an epoch timestamp into a human-friendly relative time string."""
    diff = max(0, time.time() - epoch_time)
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        mins = int(diff // 60)
        return f"{mins}m ago"
    elif diff < 86400:
        hrs = int(diff // 3600)
        return f"{hrs}h ago"
    else:
        days = int(diff // 86400)
        return f"{days}d ago"


def infer_category(title: str, feed_name: str = "") -> str:
    """Assign broad topic categories using robust whole-word regex matching."""
    t_lower = title.lower()
    f_lower = feed_name.lower()

    if "business" in f_lower or "market" in f_lower:
        default_cat = "Business"
    elif "tech" in f_lower:
        default_cat = "Technology"
    else:
        default_cat = "General"

    tech_kw = [r"\btech\b", r"\bai\b", r"\bsoftware\b", r"\bcyber\b", r"\brobot\b", r"\bgoogle\b", r"\bapple\b", r"\bmicrosoft\b", r"\bchip\b", r"\bcloud\b", r"\bsemiconductor\b", r"\bquantum\b"]
    politics_kw = [r"\bpolitics\b", r"\belection\b", r"\bpresident\b", r"\blaw\b", r"\bparliament\b", r"\bcongress\b", r"\bvote\b", r"\bsenate\b", r"\bcabinet\b", r"\bminister\b"]
    world_kw = [r"\bwar\b", r"\bmilitary\b", r"\bstrike\b", r"\bconflict\b", r"\bpeace\b", r"\btreaty\b", r"\bgaza\b", r"\bukraine\b", r"\bworld\b", r"\bisrael\b", r"\blebanon\b", r"\bchina\b"]
    business_kw = [r"\bmarket\b", r"\beconomy\b", r"\bstock\b", r"\bbank\b", r"\binflation\b", r"\bprofit\b", r"\bgrowth\b", r"\bbusiness\b", r"\brevenue\b", r"\bfed\b", r"\brate\b", r"\bearnings\b", r"\bshares\b"]

    if any(re.search(p, t_lower) for p in business_kw):
        return "Business"
    elif any(re.search(p, t_lower) for p in tech_kw):
        return "Technology"
    elif any(re.search(p, t_lower) for p in world_kw):
        return "World"
    elif any(re.search(p, t_lower) for p in politics_kw):
        return "Politics"
    return default_cat


def fetch_source_feed(source_name: str, feed_url: str, timeout: int = 7, max_age_hours: int = 72) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed safely with strict freshness filtering."""
    articles = []
    now = time.time()
    max_age_seconds = max_age_hours * 3600

    try:
        resp = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"[-] Source {source_name} returned status code {resp.status_code}")
            return []

        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:35]:
            raw_title = entry.get("title", "")
            title = clean_headline_text(raw_title)
            if not title or len(title) < 10:
                continue

            link = entry.get("link", "")

            # Parse accurate publication timestamp
            published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if published_parsed:
                epoch_time = float(calendar.timegm(published_parsed))
                pub_dt = datetime.utcfromtimestamp(epoch_time)
                published_str = pub_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                epoch_time = now
                published_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # STRICT FRESHNESS FILTER: Discard any stale headlines older than max_age_hours
            if (now - epoch_time) > max_age_seconds:
                continue

            summary = clean_headline_text(entry.get("summary", ""))

            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary[:220] if summary else "",
                "link": link,
                "published": published_str,
                "epoch_time": epoch_time,
                "relative_time": format_relative_time(epoch_time),
                "category": infer_category(title, source_name),
                "timestamp": now
            })
        logger.info(f"[+] Successfully fetched {len(articles)} fresh articles from {source_name}.")
    except Exception as e:
        logger.error(f"[-] Network/parser error fetching {source_name}: {e}")
    return articles


class DynamicNewsAggregator:
    """
    Thread-safe dynamic news aggregator that polls live sources concurrently,
    filters out stale articles, and maintains a chronologically ordered (newest first)
    in-memory cache of breaking headlines.
    """
    def __init__(self, refresh_interval_seconds: int = 120):
        self.refresh_interval = refresh_interval_seconds
        self.cache: List[Dict[str, Any]] = []
        self.seen_identifiers = set()
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_refresh_time: Optional[str] = None

    def refresh_now(self, force_clear: bool = False, max_age_hours: int = 72, *args, **kwargs) -> List[Dict[str, Any]]:
        """Perform an immediate refresh of all live sources with strict chronological sorting."""
        threads = []
        collected_articles = []

        def worker(s_name, s_url):
            arts = fetch_source_feed(s_name, s_url, timeout=7, max_age_hours=max_age_hours)
            collected_articles.extend(arts)

        for s_name, s_url in RSS_FEEDS.items():
            t = threading.Thread(target=worker, args=(s_name, s_url), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=8)

        with self.lock:
            if force_clear:
                self.cache = []
                self.seen_identifiers = set()

            # Merge and deduplicate by title or link
            article_map = {a["link"] or a["title"]: a for a in self.cache}
            now = time.time()
            max_age_seconds = max_age_hours * 3600

            for art in collected_articles:
                key = art["link"] or art["title"]
                # Update with latest relative time
                art["relative_time"] = format_relative_time(art.get("epoch_time", now))
                article_map[key] = art

            # Filter out any articles that have become older than max_age_hours
            fresh_list = [
                a for a in article_map.values()
                if (now - a.get("epoch_time", now)) <= max_age_seconds
            ]

            # STRICT CHRONOLOGICAL SORTING: Newest breaking headlines FIRST
            fresh_list.sort(key=lambda x: x.get("epoch_time", 0), reverse=True)

            self.cache = fresh_list[:350]
            self.last_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"[+] Aggregator refreshed: {len(self.cache)} fresh, chronological articles active in cache.")
        return list(self.cache)

    def get_articles(self, limit: int = 100, max_age_hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return the latest cached articles safely (strictly newest first)."""
        with self.lock:
            now = time.time()
            # Refresh relative time dynamically for display
            for a in self.cache:
                a["relative_time"] = format_relative_time(a.get("epoch_time", now))

            if max_age_hours is not None:
                max_sec = max_age_hours * 3600
                filtered = [a for a in self.cache if (now - a.get("epoch_time", now)) <= max_sec]
                return list(filtered[:limit])

            return list(self.cache[:limit])

    def start_background_loop(self):
        """Start dynamic background polling thread."""
        if self._thread and self._thread.is_alive():
            return

        def loop():
            logger.info("[*] Starting dynamic news background polling loop...")
            while not self._stop_event.is_set():
                try:
                    self.refresh_now(force_clear=False, max_age_hours=72)
                except Exception as e:
                    logger.error(f"[-] Error in background news loop: {e}")
                self._stop_event.wait(self.refresh_interval)

        self._stop_event.clear()
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

        # Perform initial fetch synchronously if cache is empty
        if not self.cache:
            self.refresh_now(force_clear=True, max_age_hours=72)

    def stop_background_loop(self):
        """Stop background polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)


# Global singleton instance for easy import across modules
global_aggregator = DynamicNewsAggregator(refresh_interval_seconds=180)


if __name__ == "__main__":
    print("[*] Testing upgraded dynamic real-time scraper...")
    arts = global_aggregator.refresh_now(force_clear=True, max_age_hours=48)
    print(f"[+] Fetched {len(arts)} total fresh articles.")
    for i, a in enumerate(arts[:10]):
        print(f" {i+1}. [{a['source']}] ({a['relative_time']}) {a['title'][:75]}...")
