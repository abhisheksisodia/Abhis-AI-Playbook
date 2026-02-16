"""Email notification stub."""

from __future__ import annotations

from typing import List

from ..schemas import SummaryPayload
from ..utils.logger import get_logger

logger = get_logger("notifiers.email")


def send_email_digest(
    recipients: List[str],
    *,
    draft_url: str,
    top_picks: List[SummaryPayload],
) -> None:
    if not recipients:
        logger.info("No email recipients configured; skipping email digest.")
        return

    # Plug in SendGrid/Postmark here.
    logger.info(
        "Email digest would be sent to %s with draft %s.",
        ",".join(recipients),
        draft_url,
    )
