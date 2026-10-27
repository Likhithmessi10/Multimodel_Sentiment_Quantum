import feedparser
from time import mktime
from datetime import datetime

def _dt_from_entry(e):
    try:
        return datetime.fromtimestamp(mktime(e.published_parsed)).isoformat()
    except Exception:
        return None

def scrape_cnn(limit=None):
    """Scrape CNN via RSS.
Returns list of dicts: {source,title,link,published}
"""
    FEED = "http://rss.cnn.com/rss/edition.rss"
    feed = feedparser.parse(FEED)
    articles = []
    for e in feed.entries:
        summary = getattr(e, "summary", "") or getattr(e, "description", "")
        if summary:
            from bs4 import BeautifulSoup
            summary = BeautifulSoup(summary, "html.parser").get_text().strip()
            if len(summary) > 200:
                summary = summary[:197] + "..."
        else:
            summary = None

        articles.append({
            "source": "CNN",
            "title": e.title.strip(),
            "link": e.link.strip(),
            "published": _dt_from_entry(e),
            "summary": summary
        })
        if limit and len(articles) >= limit:
            break
    return articles
