import feedparser
from time import mktime
from datetime import datetime

def _dt_from_entry(e):
    try:
        return datetime.fromtimestamp(mktime(e.published_parsed)).isoformat()
    except Exception:
        return None

def scrape_aljazeera(limit=None):
    """Scrape Al Jazeera via RSS.
Returns list of dicts: {source,title,link,published}
"""
    FEED = "https://www.aljazeera.com/xml/rss/all.xml"
    feed = feedparser.parse(FEED)
    articles = []
    for e in feed.entries:
        title = getattr(e, "title", "").strip()
        link = getattr(e, "link", "").strip()
        summary = getattr(e, "summary", "") or getattr(e, "description", "")
        if summary:
            from bs4 import BeautifulSoup
            summary = BeautifulSoup(summary, "html.parser").get_text().strip()
            if len(summary) > 200:
                summary = summary[:197] + "..."
        else:
            summary = None

        articles.append({
            "source": "Al Jazeera",
            "title": title,
            "link": link,
            "published": _dt_from_entry(e),
            "summary": summary
        })
        if limit and len(articles) >= limit:
            break
    return articles
