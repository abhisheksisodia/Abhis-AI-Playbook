"""Blog discovery utilities via RSS/Atom feeds."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import feedparser
import requests
from bs4 import BeautifulSoup

from ..config import Settings
from ..schemas import ItemPayload
from ..utils.logger import get_logger
from ..utils.text import normalize_whitespace, strip_boilerplate

logger = get_logger("discovery.blogs")


def _fetch_article_body(url: str) -> str:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch article body for %s: %s", url, exc)
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    article = soup.find("article") or soup.body
    if not article:
        return ""

    texts = [normalize_whitespace(p.get_text(separator=" ")) for p in article.find_all("p")]
    return strip_boilerplate(texts)


def discover(settings: Settings, lookback_days: int | None = None) -> List[ItemPayload]:
    lookback = lookback_days or settings.schedule.lookback_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback)

    items: List[ItemPayload] = []
    for name, cfg in settings.sources.blog_feeds.items():
        feed_url = cfg["url"]
        tags = cfg.get("tags", [])
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            published_dt = (
                datetime(*published_parsed[:6], tzinfo=timezone.utc)
                if published_parsed
                else datetime.utcnow()
            )
            if published_dt < cutoff:
                continue

            url = entry.link
            title = normalize_whitespace(entry.title)
            summary = normalize_whitespace(entry.get("summary", ""))
            raw_text = _fetch_article_body(url) or summary

            item = ItemPayload(
                id=f"blog:{url}",
                title=title,
                url=url,
                source=name,
                author=entry.get("author"),
                type="blog",
                published_at=published_dt,
                discovered_at=datetime.utcnow(),
                raw_text=raw_text,
                metadata={"tags": ",".join(tags)},
            )
            items.append(item)

        logger.info("Discovered %s blog posts for %s", len(items), name)

    return items
