"""Lightweight Google Drive client helpers."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any, Optional, Sequence

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseDownload

from ..utils.logger import get_logger

logger = get_logger("storage.google_drive")

DEFAULT_SCOPES = ("https://www.googleapis.com/auth/drive.file",)


def _read_json_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_credentials_env(value: str) -> Optional[dict]:
    # If the env var points to a file path use it, otherwise treat it as JSON.
    candidate_path = Path(value).expanduser()
    if candidate_path.exists():
        return _read_json_file(candidate_path)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        logger.error("Unable to parse Google Drive credentials from environment.")
        return None


class GoogleDriveClient:
    """Thin wrapper on top of the Drive v3 API for uploads/downloads."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        credentials_env: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
    ) -> None:
        info = self._load_credentials(credentials_path, credentials_env)
        scopes = tuple(scopes or DEFAULT_SCOPES)
        creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def _load_credentials(self, credentials_path: Optional[str], credentials_env: Optional[str]) -> dict:
        if credentials_path:
            path = Path(credentials_path).expanduser()
            if not path.exists():
                raise FileNotFoundError(f"Google Drive credentials file not found at {path}")
            logger.debug("Loading Google Drive credentials from %s", path)
            return _read_json_file(path)

        env_candidates = []
        if credentials_env:
            env_value = os.getenv(credentials_env)
            if env_value:
                env_candidates.append(env_value)

        default_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if default_path:
            env_candidates.append(default_path)

        for candidate in env_candidates:
            parsed = _parse_credentials_env(candidate)
            if parsed:
                logger.debug("Loaded Google Drive credentials from environment.")
                return parsed

        raise ValueError(
            "Google Drive credentials are required. "
            "Set storage.google_drive.credentials_path or the credentials_env value."
        )

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> dict:
        metadata: dict[str, Any] = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            metadata["parents"] = [parent_id]
        return (
            self.service.files()
            .create(body=metadata, fields="id,name,webViewLink", supportsAllDrives=True)
            .execute()
        )

    def upload_file(self, name: str, data: bytes, mime_type: str, parent_id: Optional[str] = None) -> dict:
        media = MediaInMemoryUpload(data, mimetype=mime_type, resumable=False)
        metadata: dict[str, Any] = {"name": name}
        if parent_id:
            metadata["parents"] = [parent_id]
        return (
            self.service.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id,name,webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )

    def download_file(self, file_id: str) -> str:
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return buffer.read().decode("utf-8")
