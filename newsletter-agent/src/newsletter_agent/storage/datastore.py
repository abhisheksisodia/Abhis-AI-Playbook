"""Datastore abstractions."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List, Sequence

from ..schemas import ItemPayload, NewsletterDraft, SummaryPayload
from ..utils.logger import get_logger
from ..utils.text import slugify

logger = get_logger("storage.datastore")


class BaseDatastore(ABC):
    @abstractmethod
    def save_items(self, items: Sequence[ItemPayload]) -> None:
        ...

    @abstractmethod
    def save_summaries(self, summaries: Sequence[SummaryPayload]) -> None:
        ...

    @abstractmethod
    def save_newsletter(self, draft: NewsletterDraft, markdown: str, beehiiv_html: str) -> Path:
        ...

    @abstractmethod
    def save_quality_report(self, report: dict) -> Path:
        ...


class LocalJSONStore(BaseDatastore):
    def __init__(self, base_path: str = "data") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _write_json(self, name: str, payload: Iterable[dict]) -> Path:
        path = self.base_path / name
        with path.open("w", encoding="utf-8") as handle:
            json.dump(list(payload), handle, indent=2)
        return path

    def save_items(self, items: Sequence[ItemPayload]) -> None:
        path = self._write_json(
            "items.json",
            (item.to_dict() for item in items),
        )
        logger.info("Saved %s items to %s", len(items), path)

    def save_summaries(self, summaries: Sequence[SummaryPayload]) -> None:
        path = self._write_json(
            "summaries.json",
            (summary.to_dict() for summary in summaries),
        )
        logger.info("Saved %s summaries to %s", len(summaries), path)

    def save_newsletter(self, draft: NewsletterDraft, markdown: str, beehiiv_html: str) -> Path:
        issue_slug = f"issue-{draft.issue_number}-{slugify(draft.issue_date.strftime('%Y-%m-%d'))}"
        issue_dir = self.base_path / issue_slug
        issue_dir.mkdir(parents=True, exist_ok=True)

        payload_path = issue_dir / "newsletter.json"
        with payload_path.open("w", encoding="utf-8") as handle:
            json.dump(draft.to_dict(), handle, indent=2)

        (issue_dir / "newsletter.md").write_text(markdown, encoding="utf-8")
        (issue_dir / "beehiiv.html").write_text(beehiiv_html, encoding="utf-8")

        logger.info("Saved newsletter draft to %s", issue_dir)
        return issue_dir

    def save_quality_report(self, report: dict) -> Path:
        path = self.base_path / "quality_report.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        logger.info("Saved quality report to %s", path)
        return path
