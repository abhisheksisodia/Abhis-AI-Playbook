"""Text utility helpers."""

from __future__ import annotations

import re
from typing import Iterable, List


WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "..."


def strip_boilerplate(lines: Iterable[str]) -> str:
    cleaned: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(
            stripped.lower().startswith(prefix)
            for prefix in ("subscribe", "copyright", "cookies")
        ):
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)


def slugify(value: str) -> str:
    try:
        from slugify import slugify as sf

        return sf(value)
    except Exception:
        return re.sub(r"[^\w]+", "-", value.lower()).strip("-")
