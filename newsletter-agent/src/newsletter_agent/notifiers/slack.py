"""Slack notification helper."""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import requests

from ..schemas import SummaryPayload
from ..utils.logger import get_logger

logger = get_logger("notifiers.slack")


def send_digest(
    webhook_env: Optional[str],
    *,
    draft_url: str,
    top_picks: List[SummaryPayload],
    quality_report_url: str | None = None,
) -> None:
    if not webhook_env:
        logger.info("Skipping Slack notification; no webhook env key configured.")
        return

    webhook_url = os.getenv(webhook_env)
    if not webhook_url:
        logger.warning("Skipping Slack notification; %s not set.", webhook_env)
        return

    attachments: List[Dict] = []
    for summary in top_picks[:3]:
        attachments.append(
            {
                "title": summary.title,
                "title_link": summary.url,
                "text": f"*TL;DR*: {summary.tldr}\n*Why it matters*: {summary.why_it_matters}",
            }
        )

    message = {
        "text": f"📰 New newsletter draft ready: {draft_url}",
        "attachments": attachments,
    }
    if quality_report_url:
        message["text"] += f"\nQuality report: {quality_report_url}"

    response = requests.post(
        webhook_url, data=json.dumps(message), headers={"Content-Type": "application/json"}, timeout=10
    )
    if response.status_code >= 400:
        logger.error("Slack notification failed: %s - %s", response.status_code, response.text)
    else:
        logger.info("Slack notification sent.")
