"""Relevance and quality scoring pipeline."""

from __future__ import annotations

import json
from typing import Iterable, List, Tuple

from ..config import Settings
from ..schemas import ItemPayload, ScoreBreakdown
from ..utils.llm import LLMClient
from ..utils.logger import get_logger
from ..utils.text import truncate_words

logger = get_logger("pipeline.scoring")

SCORE_SYSTEM_PROMPT = """
You are an editorial quality evaluator for an AI newsletter targeting business leaders, builders, engineers, and product managers considering AI adoption. Score the provided content using the required rubric and return strict JSON."""

SCORE_USER_PROMPT = """
Content Title: {title}
Source Type: {type}
Source Name: {source}
Publish Date: {published}

Content Excerpt (first 500 words max):
\"\"\"
{excerpt}
\"\"\"

Score the content 0-100 using the following weights:
- Audience fit (30%): Alignment with business leader/builder needs, practical over theoretical.
- Practicality (25%): Provides actionable steps, frameworks, or real-world examples.
- Originality (20%): Offers novel insights or unique perspectives.
- Freshness (15%): Timely and relevant to current AI landscape.
- Brand safety (10%): Professional tone, avoids hype/clickbait.

Respond with JSON:
{{
  "score": float,
  "rationale": "2-3 sentences",
  "score_breakdown": {{
    "audience_fit": float,
    "practicality": float,
    "originality": float,
    "freshness": float,
    "brand_safety": float
  }}
}}
"""


def _build_prompt(item: ItemPayload) -> str:
    excerpt = truncate_words(item.raw_text, 500)
    return SCORE_USER_PROMPT.format(
        title=item.title,
        type=item.type,
        source=item.source,
        published=item.published_at.strftime("%Y-%m-%d") if item.published_at else "Unknown",
        excerpt=excerpt,
    )


def _parse_response(item: ItemPayload, response_text: str) -> ItemPayload:
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from scoring prompt for {item.id}: {exc}") from exc

    breakdown = data.get("score_breakdown", {})
    item.score = float(data.get("score", 0))
    item.score_breakdown = ScoreBreakdown(
        audience_fit=float(breakdown.get("audience_fit", 0)),
        practicality=float(breakdown.get("practicality", 0)),
        originality=float(breakdown.get("originality", 0)),
        freshness=float(breakdown.get("freshness", 0)),
        brand_safety=float(breakdown.get("brand_safety", 0)),
    )
    item.rationale = data.get("rationale", "")
    return item


def score_items(
    items: Iterable[ItemPayload], settings: Settings
) -> Tuple[List[ItemPayload], List[ItemPayload]]:
    client = LLMClient(
        provider=settings.llm.provider,
        model=settings.llm.model,
        api_key_env=settings.llm.api_key_env,
    )

    passed: List[ItemPayload] = []
    flagged: List[ItemPayload] = []

    for item in items:
        prompt = _build_prompt(item)
        response = client.safe_complete(
            SCORE_SYSTEM_PROMPT.strip(),
            prompt.strip(),
            temperature=settings.llm.temperature,
        )
        try:
            updated = _parse_response(item, response.content)
        except ValueError as exc:
            logger.error("Failed to parse scoring output for %s: %s", item.id, exc)
            continue

        if updated.score >= settings.scoring.min_auto_publish_score:
            passed.append(updated)
        elif updated.score >= settings.scoring.manual_review_floor:
            flagged.append(updated)
        else:
            logger.info("Dropping %s with score %.2f", updated.title, updated.score)

    logger.info(
        "Scoring complete: %s passed, %s flagged, %s total.",
        len(passed),
        len(flagged),
        len(passed) + len(flagged),
    )
    return passed, flagged
