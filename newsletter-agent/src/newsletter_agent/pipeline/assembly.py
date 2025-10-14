"""Newsletter assembly and formatting."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config import Settings
from ..schemas import CTA, NewsletterDraft, PlaybookTip, SummaryPayload
from ..utils.llm import LLMClient
from ..utils.logger import get_logger

logger = get_logger("pipeline.assembly")


ASSEMBLY_SYSTEM_PROMPT = """
You are the head writer for Abhi's AI Playbook. Compose a production-ready newsletter draft that mirrors the supplied reference style. Keep the tone practical, approachable, and focused on operator value.
Respond with strict JSON only.
"""


def _load_reference_style(ref_path: Optional[str]) -> str:
    if not ref_path:
        return ""
    path = Path(ref_path)
    if path.is_dir():
        texts: List[str] = []
        for file in sorted(path.glob("*.md")):
            texts.append(file.read_text(encoding="utf-8"))
        return "\n\n".join(texts)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _summaries_to_text(summaries: List[SummaryPayload]) -> str:
    lines: List[str] = []
    for idx, summary in enumerate(summaries, start=1):
        bullets = "\n".join(f"- {bullet}" for bullet in summary.bullets)
        risks = "\n".join(f"- {risk}" for risk in summary.risks)
        timestamps = "\n".join(
            f"- {highlight.time} → {highlight.description}" for highlight in summary.timestamps
        )
        lines.append(
            f"""## Pick {idx}: {summary.title}
URL: {summary.url}
TLDR: {summary.tldr}
Why It Matters: {summary.why_it_matters}
Actionable Takeaways:
{bullets}
Risks:
{risks or '- None noted'}
Quote/Metric: {summary.quote_or_metric}
Timestamps:
{timestamps or '- n/a'}
Social Tweet: {summary.social.tweet if summary.social else ''}
Social LinkedIn: {summary.social.linkedin if summary.social else ''}
SEO Title: {summary.seo.title if summary.seo else ''}
SEO Meta: {summary.seo.meta_description if summary.seo else ''}
"""
        )
    return "\n".join(lines)


def assemble_newsletter(
    summaries: List[SummaryPayload],
    settings: Settings,
    *,
    quick_hits: List[Dict[str, str]],
    strategy_report: str,
    tone_report: str,
    personality_notes: str,
    issue_number: int,
    issue_date: datetime,
) -> Tuple[NewsletterDraft, str, str]:
    client = LLMClient(
        provider=settings.llm.provider,
        model=settings.llm.model,
        api_key_env=settings.llm.api_key_env,
    )

    reference_style = _load_reference_style(settings.assembly.get("reference_style_path"))
    top_pick_text = _summaries_to_text(summaries[:3])
    quick_hits_text = "\n".join(
        f"- {item['title']} ({item['url']}): {item['tldr']}"
        for item in quick_hits
    )

    user_prompt = f"""
Strategy Report:
{strategy_report}

Tone of Voice Report:
{tone_report}

Personal Context Notes:
{personality_notes}

Reference Newsletters:
{reference_style[:8000]}

Top Picks (structured data):
{top_pick_text}

Quick Hits:
{quick_hits_text}

Instructions:
- Hook ≤80 words, mimic reference opening style.
- Use provided summaries for Top 3 picks; do not invent facts.
- Generate Playbook Tip (3-5 step checklist) derived from Pick 1.
- CTA must include subscribe + consulting offer, match reference CTA style.
- Provide Markdown body and Beehiiv-compatible HTML (keep inline styles minimal).

Return JSON:
{{
  "hook": "string",
  "top_picks": ["reworded summary for pick 1", "pick 2", "pick 3"],
  "playbook_tip": {{
    "title": "string",
    "description": "≤50 words",
    "checklist": ["step 1", "step 2", "step 3"]
  }},
  "cta": {{
    "text": "string",
    "subscribe_url": "string",
    "consulting_url": "string"
  }},
  "markdown": "full markdown draft",
  "beehiiv_html": "beehiiv-friendly html or json blocks",
  "quality_notes": "checks performed"
}}
"""

    response = client.safe_complete(
        ASSEMBLY_SYSTEM_PROMPT.strip(),
        user_prompt.strip(),
        temperature=settings.llm.temperature,
        max_output_tokens=2000,
    )

    data = json.loads(response.content)
    playbook_tip_data = data.get("playbook_tip", {})
    cta_data = data.get("cta", {})

    playbook_tip = PlaybookTip(
        title=playbook_tip_data.get("title", ""),
        description=playbook_tip_data.get("description", ""),
        checklist=playbook_tip_data.get("checklist", []),
    )
    cta = CTA(
        text=cta_data.get("text", ""),
        subscribe_url=cta_data.get("subscribe_url", ""),
        consulting_url=cta_data.get("consulting_url", ""),
    )

    draft = NewsletterDraft(
        issue_number=issue_number,
        issue_date=issue_date,
        hook=data.get("hook", ""),
        top_picks=summaries[:3],
        quick_hits=quick_hits,
        playbook_tip=playbook_tip,
        cta=cta,
        metadata={
            "total_items_discovered": 0,
            "items_scored_above_threshold": len(summaries),
            "sources_checked": len(settings.sources.youtube_channels)
            + len(settings.sources.blog_feeds),
            "generation_time_seconds": 0,
        },
    )

    markdown = data.get("markdown", "")
    beehiiv_html = data.get("beehiiv_html", "")

    return draft, markdown, beehiiv_html
