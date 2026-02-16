"""Quality gate checks for newsletter outputs."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Dict, List

import httpx

from ..schemas import NewsletterDraft, SummaryPayload
from ..utils.logger import get_logger
logger = get_logger("pipeline.quality")


def _check_lengths(summary: SummaryPayload) -> Dict[str, bool]:
    return {
        "tldr_length": len(summary.tldr.split()) <= 25,
        "why_it_matters_length": len(summary.why_it_matters.split()) <= 60,
        "tweet_length": len(summary.social.tweet) <= 280 if summary.social else True,
    }


def _validate_links(summaries: List[SummaryPayload], quick_hits: List[Dict[str, str]]) -> Dict[str, bool]:
    status: Dict[str, bool] = {}
    urls = [summary.url for summary in summaries] + [item["url"] for item in quick_hits]

    for url in urls:
        try:
            response = httpx.head(url, timeout=10, follow_redirects=True)
            if response.status_code >= 400 or response.status_code == 405:
                response = httpx.get(url, timeout=10, follow_redirects=True)
            status[url] = 200 <= response.status_code < 400
        except Exception:
            status[url] = False
    return status


def _generate_summary_report(summaries: List[SummaryPayload]) -> List[Dict]:
    report: List[Dict] = []
    for summary in summaries:
        lengths = _check_lengths(summary)
        report.append(
            {
                "item_id": summary.item_id,
                "title": summary.title,
                "length_checks": lengths,
                "risks_present": bool(summary.risks),
                "actionable_bullet_count": len(summary.bullets),
            }
        )
    return report


def run_quality_gates(
    draft: NewsletterDraft,
    summaries: List[SummaryPayload],
    quick_hits: List[Dict[str, str]],
) -> Dict:
    """Run quality validations and produce a report."""
    length_checks = _generate_summary_report(summaries)
    link_results = _validate_links(summaries, quick_hits)

    report = {
        "length_checks": length_checks,
        "link_validation": link_results,
        "cta_present": bool(draft.cta.text and draft.cta.subscribe_url),
        "metadata": draft.metadata,
    }
    logger.info("Quality gates generated.")
    return report


def export_quality_report(report: Dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
