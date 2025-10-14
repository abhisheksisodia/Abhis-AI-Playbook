"""Configuration loader for the newsletter agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULT_CONFIG_PATH = Path("config/default_config.yaml")


@dataclass
class SourceConfig:
    youtube_channels: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    blog_feeds: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    manual_sources_sheet: Optional[str] = None


@dataclass
class ScoringConfig:
    min_auto_publish_score: float = 60.0
    manual_review_floor: float = 50.0
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "audience_fit": 0.30,
            "practicality": 0.25,
            "originality": 0.20,
            "freshness": 0.15,
            "brand_safety": 0.10,
        }
    )


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20240620"
    max_retries: int = 3
    temperature: float = 0.2
    api_key_env: str = "ANTHROPIC_API_KEY"


@dataclass
class ScheduleConfig:
    cron: str = "0 6 * * 0"  # Sunday 06:00 UTC
    lookback_days: int = 7


@dataclass
class StorageConfig:
    backend: str = "local"
    path: str = "data"
    airtable_base_id: Optional[str] = None
    airtable_api_key_env: str = "AIRTABLE_API_KEY"


@dataclass
class NotificationConfig:
    slack_webhook_env: Optional[str] = None
    email_service: Optional[str] = None
    recipients: Optional[list[str]] = None


@dataclass
class Settings:
    sources: SourceConfig
    scoring: ScoringConfig
    llm: LLMConfig
    schedule: ScheduleConfig
    storage: StorageConfig
    notifications: NotificationConfig
    summarizer: Dict[str, Any] = field(default_factory=dict)
    assembly: Dict[str, Any] = field(default_factory=dict)


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config(path: Optional[Path] = None) -> Settings:
    """Load YAML configuration and map onto Settings dataclasses."""
    config_path = path or Path(
        Path.home() / ".newsletter-agent-config.yaml"
        if Path(Path.home() / ".newsletter-agent-config.yaml").exists()
        else DEFAULT_CONFIG_PATH
    )
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {config_path}. "
            "Create config/default_config.yaml or set NEWSLETTER_CONFIG_PATH."
        )

    raw = _load_yaml(config_path)

    sources = SourceConfig(**raw.get("sources", {}))
    scoring = ScoringConfig(**raw.get("scoring", {}))
    llm = LLMConfig(**raw.get("llm", {}))
    schedule = ScheduleConfig(**raw.get("schedule", {}))
    storage = StorageConfig(**raw.get("storage", {}))
    notifications = NotificationConfig(**raw.get("notifications", {}))

    return Settings(
        sources=sources,
        scoring=scoring,
        llm=llm,
        schedule=schedule,
        storage=storage,
        notifications=notifications,
        summarizer=raw.get("summarizer", {}),
        assembly=raw.get("assembly", {}),
    )
