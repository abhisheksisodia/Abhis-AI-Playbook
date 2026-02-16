"""Datastore abstractions."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

from ..config import GoogleDriveConfig, StorageConfig
from ..schemas import ItemPayload, NewsletterDraft, SummaryPayload
from ..utils.logger import get_logger
from ..utils.text import slugify
from .google_drive import GoogleDriveClient

logger = get_logger("storage.datastore")


@dataclass
class StorageArtifact:
    uri: str
    label: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)


class BaseDatastore(ABC):
    @abstractmethod
    def save_items(self, items: Sequence[ItemPayload]) -> None:
        ...

    @abstractmethod
    def save_summaries(self, summaries: Sequence[SummaryPayload]) -> None:
        ...

    @abstractmethod
    def save_newsletter(self, draft: NewsletterDraft, markdown: str, beehiiv_html: str) -> StorageArtifact:
        ...

    @abstractmethod
    def save_quality_report(self, report: dict) -> StorageArtifact:
        ...

    @abstractmethod
    def save_flagged_items(self, items: Sequence[ItemPayload]) -> None:
        ...

    def load_reference_text(self, key: str) -> str:
        """Optional hook for pulling reference docs (strategy, tone, personality)."""
        return ""


class LocalJSONStore(BaseDatastore):
    def __init__(self, base_path: str = "data", run_slug: Optional[str] = None) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.run_slug = run_slug

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

    def save_flagged_items(self, items: Sequence[ItemPayload]) -> None:
        if not items:
            return
        path = self.base_path / "flagged_items.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump([item.to_dict() for item in items], handle, indent=2)
        logger.info("Saved %s flagged items to %s", len(items), path)

    def save_newsletter(self, draft: NewsletterDraft, markdown: str, beehiiv_html: str) -> StorageArtifact:
        issue_slug = f"issue-{draft.issue_number}-{slugify(draft.issue_date.strftime('%Y-%m-%d'))}"
        issue_dir = self.base_path / issue_slug
        issue_dir.mkdir(parents=True, exist_ok=True)

        payload_path = issue_dir / "newsletter.json"
        with payload_path.open("w", encoding="utf-8") as handle:
            json.dump(draft.to_dict(), handle, indent=2)

        markdown_path = issue_dir / "newsletter.md"
        html_path = issue_dir / "beehiiv.html"

        markdown_path.write_text(markdown, encoding="utf-8")
        html_path.write_text(beehiiv_html, encoding="utf-8")

        logger.info("Saved newsletter draft to %s", issue_dir)
        return StorageArtifact(
            uri=issue_dir.resolve().as_uri(),
            label=str(issue_dir),
            extra={
                "markdown_uri": markdown_path.resolve().as_uri(),
                "html_uri": html_path.resolve().as_uri(),
            },
        )

    def save_quality_report(self, report: dict) -> StorageArtifact:
        path = self.base_path / "quality_report.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        logger.info("Saved quality report to %s", path)
        return StorageArtifact(uri=path.resolve().as_uri(), label=str(path))


class GoogleDriveStore(BaseDatastore):
    def __init__(self, storage_config: StorageConfig, run_slug: str) -> None:
        gd_config = storage_config.google_drive
        if not gd_config:
            raise ValueError("Google Drive storage selected but google_drive config missing.")
        if not gd_config.base_folder_id:
            raise ValueError("google_drive.base_folder_id is required for Google Drive storage.")

        self.config: GoogleDriveConfig = gd_config
        self.run_slug = run_slug
        self.base_folder_id = gd_config.base_folder_id
        self.client = GoogleDriveClient(
            credentials_path=gd_config.credentials_path,
            credentials_env=gd_config.credentials_env,
        )
        self._run_folder_id: Optional[str] = None
        self._run_folder_link: Optional[str] = None

    def _ensure_run_folder(self) -> str:
        if self._run_folder_id:
            return self._run_folder_id
        folder = self.client.create_folder(self.run_slug, self.base_folder_id)
        self._run_folder_id = folder["id"]
        self._run_folder_link = folder.get("webViewLink") or f"https://drive.google.com/drive/folders/{folder['id']}"
        logger.info("Created Google Drive folder %s for run %s", self._run_folder_link, self.run_slug)
        return self._run_folder_id

    def _upload_json(self, filename: str, payload: Any) -> dict:
        folder_id = self._ensure_run_folder()
        data = json.dumps(payload, indent=2).encode("utf-8")
        return self.client.upload_file(filename, data, "application/json", folder_id)

    def _upload_text(self, filename: str, contents: str, mime_type: str) -> dict:
        folder_id = self._ensure_run_folder()
        return self.client.upload_file(filename, contents.encode("utf-8"), mime_type, folder_id)

    def save_items(self, items: Sequence[ItemPayload]) -> None:
        if not items:
            logger.warning("No items to save to Google Drive.")
            return
        created = self._upload_json("items.json", [item.to_dict() for item in items])
        logger.info("Uploaded items to Google Drive file %s", created.get("webViewLink"))

    def save_summaries(self, summaries: Sequence[SummaryPayload]) -> None:
        if not summaries:
            logger.warning("No summaries to save to Google Drive.")
            return
        created = self._upload_json("summaries.json", [summary.to_dict() for summary in summaries])
        logger.info("Uploaded summaries to Google Drive file %s", created.get("webViewLink"))

    def save_flagged_items(self, items: Sequence[ItemPayload]) -> None:
        if not items:
            return
        created = self._upload_json("flagged_items.json", [item.to_dict() for item in items])
        logger.info("Uploaded flagged items to Google Drive file %s", created.get("webViewLink"))

    def save_newsletter(self, draft: NewsletterDraft, markdown: str, beehiiv_html: str) -> StorageArtifact:
        self._ensure_run_folder()
        payload = self._upload_json("newsletter.json", draft.to_dict())
        markdown_file = self._upload_text("newsletter.md", markdown, "text/markdown")
        html_file = self._upload_text("beehiiv.html", beehiiv_html, "text/html")
        folder_uri = self._run_folder_link or f"https://drive.google.com/drive/folders/{self._run_folder_id}"
        logger.info("Uploaded newsletter assets to Google Drive folder %s", folder_uri)
        return StorageArtifact(
            uri=folder_uri,
            label=f"Google Drive folder for {self.run_slug}",
            extra={
                "payload_uri": payload.get("webViewLink", ""),
                "markdown_uri": markdown_file.get("webViewLink", ""),
                "html_uri": html_file.get("webViewLink", ""),
            },
        )

    def save_quality_report(self, report: dict) -> StorageArtifact:
        created = self._upload_json("quality_report.json", report)
        uri = created.get("webViewLink", "")
        logger.info("Uploaded quality report to Google Drive file %s", uri)
        return StorageArtifact(uri=uri or created.get("id", ""), label="Google Drive quality report")

    def load_reference_text(self, key: str) -> str:
        file_id = getattr(self.config.inputs, f"{key}_file_id", None)
        if not file_id:
            return ""
        logger.info("Fetching %s reference text from Google Drive file %s", key, file_id)
        return self.client.download_file(file_id)
