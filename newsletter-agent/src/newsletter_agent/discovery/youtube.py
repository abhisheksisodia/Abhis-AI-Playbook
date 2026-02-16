"""YouTube discovery utilities."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

from ..config import Settings
from ..schemas import ItemPayload
from ..utils.logger import get_logger
from ..utils.text import normalize_whitespace

logger = get_logger("discovery.youtube")

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"


def _published_after(lookback_days: int) -> str:
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    return since.isoformat()


def _parse_published_at(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.utcnow()


def _fetch_transcript(video_id: str) -> str:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        return "\n".join(chunk["text"] for chunk in transcript)
    except (TranscriptsDisabled, Exception):
        return ""


def _resolve_channel_id(channel_ref: str, api_key: str) -> Optional[str]:
    """Resolve a channel id from a channel id, @handle, or channel URL."""
    if channel_ref.startswith("UC"):
        return channel_ref

    normalized = channel_ref.strip()
    if "youtube.com" in normalized:
        normalized = normalized.rstrip("/").split("/")[-1]

    query = normalized[1:] if normalized.startswith("@") else normalized
    if not query:
        return None

    response = requests.get(
        f"{YOUTUBE_API_URL}/search",
        params={
            "key": api_key,
            "part": "snippet",
            "type": "channel",
            "maxResults": 1,
            "q": query,
        },
        timeout=30,
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    if not items:
        return None

    return items[0].get("snippet", {}).get("channelId")


def _fetch_channel_videos(
    channel_id: str, api_key: str, lookback_days: int, max_results: int = 25
) -> List[Dict]:
    params = {
        "key": api_key,
        "channelId": channel_id,
        "part": "id,snippet",
        "order": "date",
        "maxResults": max_results,
        "type": "video",
        "publishedAfter": _published_after(lookback_days),
    }
    response = requests.get(f"{YOUTUBE_API_URL}/search", params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("items", [])


def discover(settings: Settings, lookback_days: int | None = None) -> List[ItemPayload]:
    """Discover new YouTube videos for configured channels."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("Skipping YouTube discovery; YOUTUBE_API_KEY not set.")
        return []

    lookback = lookback_days or settings.schedule.lookback_days

    items: List[ItemPayload] = []
    for name, cfg in settings.sources.youtube_channels.items():
        tags = cfg.get("tags", [])
        channel_ref = cfg.get("channel_id") or cfg.get("channel") or cfg.get("handle") or cfg.get("url")
        if not channel_ref:
            logger.warning("Skipping YouTube source %s; missing channel_id/channel/handle/url.", name)
            continue

        try:
            channel_id = _resolve_channel_id(channel_ref, api_key)
            if not channel_id:
                logger.warning("Could not resolve channel id for %s (%s)", name, channel_ref)
                continue
            videos = _fetch_channel_videos(channel_id, api_key, lookback)
        except Exception as exc:
            logger.error("Failed to fetch videos for %s: %s", name, exc)
            continue

        for video in videos:
            snippet = video.get("snippet", {})
            video_id = video["id"]["videoId"]
            title = normalize_whitespace(snippet.get("title", ""))
            description = normalize_whitespace(snippet.get("description", ""))
            published_at = _parse_published_at(snippet.get("publishedAt", ""))
            transcript = _fetch_transcript(video_id)
            raw_text = transcript or description

            item = ItemPayload(
                id=f"youtube:{video_id}",
                title=title,
                url=f"https://www.youtube.com/watch?v={video_id}",
                source=name,
                author=snippet.get("channelTitle"),
                type="youtube",
                published_at=published_at,
                discovered_at=datetime.utcnow(),
                raw_text=raw_text,
                metadata={"tags": ",".join(tags), "description": description},
            )
            items.append(item)

    logger.info("Discovered %s YouTube items.", len(items))
    return items
