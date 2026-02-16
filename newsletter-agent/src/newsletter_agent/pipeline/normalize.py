"""Normalize and deduplicate discovered items."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from rapidfuzz import fuzz

from ..schemas import ItemPayload
from ..utils.logger import get_logger
from ..utils.text import normalize_whitespace

logger = get_logger("pipeline.normalize")


def _deduplicate(
    items: Iterable[ItemPayload], title_threshold: float = 85.0
) -> List[ItemPayload]:
    deduped: List[ItemPayload] = []
    seen_urls: set[str] = set()
    seen_titles: List[Tuple[str, ItemPayload]] = []

    for item in items:
        if item.url in seen_urls:
            continue
        normalized_title = normalize_whitespace(item.title.lower())
        duplicate = False
        for existing_title, existing_item in seen_titles:
            similarity = fuzz.token_sort_ratio(normalized_title, existing_title)
            if similarity >= title_threshold:
                logger.debug(
                    "Dropping near-duplicate: %s ~ %s (score=%.2f)",
                    item.title,
                    existing_item.title,
                    similarity,
                )
                duplicate = True
                break
        if duplicate:
            continue

        seen_urls.add(item.url)
        seen_titles.append((normalized_title, item))
        deduped.append(item)

    return deduped


def normalize_items(items: Iterable[ItemPayload]) -> List[ItemPayload]:
    """Apply standardization and deduplication."""
    normalized: List[ItemPayload] = []
    for item in items:
        item.title = normalize_whitespace(item.title)
        item.raw_text = normalize_whitespace(item.raw_text)
        normalized.append(item)

    deduped = _deduplicate(normalized)
    logger.info("Normalized %s items (deduped to %s).", len(normalized), len(deduped))
    return deduped
