"""Deep summary generation for high scoring items."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable, List

from ..config import Settings
from ..schemas import (
    ItemPayload,
    SeoMetadata,
    SocialCopy,
    SummaryPayload,
    TimestampHighlight,
)
from ..utils.llm import LLMClient
from ..utils.logger import get_logger
from ..utils.text import truncate_words

logger = get_logger("pipeline.summaries")


SUMMARY_SYSTEM_PROMPT = """
You are the lead analyst for Abhi's AI Playbook. Produce structured, operator-focused summaries that match the newsletter's playbook style (practical, educational, approachable).
Respond in JSON only.
"""

SUMMARY_USER_PROMPT = """
Content Title: {title}
Source Type: {type}
Source URL: {url}
Source Score: {score}
Audience: Business leaders & builders (beginner to intermediate) implementing AI solutions.

Content Body (truncated to 1200 words max):
\"\"\"
{excerpt}
\"\"\" 

Produce a JSON payload with:
{{
  "tldr": "≤25 words summarizing the core value proposition",
  "why_it_matters": "≤60 words explaining the significance for operators",
  "actionable_bullets": ["Use ...", "Implement ...", "Avoid ..."],
  "risks": ["Note ...", "Watch ..."],
  "quote_or_metric": "Key quote or number with attribution",
  "timestamps": [{{"time": "MM:SS", "description": "string"}}],   // optional for blog posts
  "social": {{
    "tweet": "≤280 characters, hook + value + CTA",
    "linkedin": "2-4 lines, professional tone"
  }},
  "seo": {{
    "title": "50-60 characters",
    "meta_description": "150-160 characters"
  }}
}}
"""


def _build_prompt(item: ItemPayload) -> str:
    excerpt = truncate_words(item.raw_text, 1200)
    return SUMMARY_USER_PROMPT.format(
        title=item.title,
        type=item.type,
        url=item.url,
        score=f"{item.score:.1f}",
        excerpt=excerpt,
    )


def _timestamps_from_json(raw_timestamps) -> List[TimestampHighlight]:
    highlights: List[TimestampHighlight] = []
    if not raw_timestamps:
        return highlights
    for ts in raw_timestamps:
        time_value = ts.get("time")
        description = ts.get("description")
        if time_value and description:
            highlights.append(TimestampHighlight(time=time_value, description=description))
    return highlights


def _parse_summary(item: ItemPayload, response_text: str) -> SummaryPayload:
    data = json.loads(response_text)
    tldr = data.get("tldr", "")
    why_it_matters = data.get("why_it_matters", "")
    bullets = data.get("actionable_bullets", []) or []
    risks = data.get("risks", []) or []
    quote = data.get("quote_or_metric", "")
    timestamps = _timestamps_from_json(data.get("timestamps", []))
    social_data = data.get("social") or {}
    seo_data = data.get("seo") or {}

    social_copy = None
    if social_data:
        social_copy = SocialCopy(
            tweet=social_data.get("tweet", ""),
            linkedin=social_data.get("linkedin", ""),
        )

    seo_meta = None
    if seo_data:
        seo_meta = SeoMetadata(
            title=seo_data.get("title", ""),
            meta_description=seo_data.get("meta_description", ""),
        )

    return SummaryPayload(
        item_id=item.id,
        title=item.title,
        url=item.url,
        tldr=tldr,
        why_it_matters=why_it_matters,
        bullets=bullets,
        risks=risks,
        quote_or_metric=quote,
        timestamps=timestamps,
        social=social_copy,
        seo=seo_meta,
        generated_at=datetime.utcnow(),
    )


def generate_summaries(
    items: Iterable[ItemPayload], settings: Settings, *, top_k: int | None = None
) -> List[SummaryPayload]:
    client = LLMClient(
        provider=settings.llm.provider,
        model=settings.llm.model,
        api_key_env=settings.llm.api_key_env,
    )
    sorted_items = sorted(items, key=lambda item: item.score, reverse=True)
    limit = top_k or settings.summarizer.get("top_k", 10)
    selected = sorted_items[:limit]

    summaries: List[SummaryPayload] = []
    for item in selected:
        prompt = _build_prompt(item)
        response = client.safe_complete(
            SUMMARY_SYSTEM_PROMPT.strip(),
            prompt.strip(),
            temperature=settings.llm.temperature,
            max_output_tokens=1500,
        )
        try:
            summary = _parse_summary(item, response.content)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error("Failed to parse summary for %s: %s", item.id, exc)
            continue

        summaries.append(summary)

    logger.info("Generated %s summaries.", len(summaries))
    return summaries
