"""Command-line interface for running the newsletter pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from .config import Settings, load_config
from .discovery import blogs as blog_discovery
from .discovery import youtube as youtube_discovery
from .notifiers import email as email_notifier
from .notifiers import slack as slack_notifier
from .pipeline import assembly, normalize, quality, scoring, summaries
from .schemas import ItemPayload, SummaryPayload
from .storage import BaseDatastore, GoogleDriveStore, LocalJSONStore, StorageArtifact
from .utils.logger import get_logger, setup_logger
from .utils.text import slugify, truncate_words

app = typer.Typer(help="Abhi's AI Playbook Newsletter Agent")


def _read_optional_file(path: Optional[Path]) -> str:
    if not path:
        return ""
    if not path.exists():
        raise typer.BadParameter(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def _build_quick_hits(items: list[ItemPayload], limit: int = 6) -> list[dict]:
    quick_hits = []
    for item in items[:limit]:
        quick_hits.append(
            {
                "title": item.title,
                "url": item.url,
                "tldr": truncate_words(item.raw_text, 25),
            }
        )
    return quick_hits


def _init_datastore(settings: Settings, run_slug: str) -> BaseDatastore:
    backend = (settings.storage.backend or "local").lower()
    if backend == "local":
        return LocalJSONStore(settings.storage.path, run_slug=run_slug)
    if backend in {"gdrive", "google_drive"}:
        return GoogleDriveStore(settings.storage, run_slug=run_slug)
    raise typer.BadParameter(f"Unsupported storage backend: {backend}")


def _load_reference_text(store: BaseDatastore, path: Optional[Path], key: str) -> str:
    if path:
        return _read_optional_file(path)
    return store.load_reference_text(key)


def _format_artifact_display(artifact: StorageArtifact) -> str:
    return artifact.label or artifact.uri


@app.command()
def run(
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to config YAML."
    ),
    strategy_path: Optional[Path] = typer.Option(
        None, help="Path to Newsletter Strategy Report."
    ),
    tone_path: Optional[Path] = typer.Option(
        None, help="Path to Tone of Voice / Writing Framework report."
    ),
    personality_path: Optional[Path] = typer.Option(
        None, help="Path to newsletter personality / personal context notes."
    ),
    issue_number: int = typer.Option(..., help="Newsletter issue number."),
    issue_date: datetime = typer.Option(
        datetime.utcnow(), help="Issue date (YYYY-MM-DD)."
    ),
) -> None:
    """Run the full discovery-to-draft pipeline."""
    setup_logger()
    logger = get_logger("cli")

    settings: Settings = load_config(config_path)
    issue_slug = f"issue-{issue_number}-{slugify(issue_date.strftime('%Y-%m-%d'))}"
    store = _init_datastore(settings, run_slug=issue_slug)

    # Stage 1 & 2: Discovery
    youtube_items = youtube_discovery.discover(settings)
    blog_items = blog_discovery.discover(settings)
    all_items = youtube_items + blog_items
    normalized_items = normalize.normalize_items(all_items)
    store.save_items(normalized_items)

    # Stage 3: Scoring
    passed_items, flagged_items = scoring.score_items(normalized_items, settings)
    store.save_flagged_items(flagged_items)

    if not passed_items:
        logger.warning("No items passed scoring thresholds. Exiting.")
        raise typer.Exit(code=0)

    # Stage 4: Summaries
    summary_payloads = summaries.generate_summaries(passed_items, settings)
    store.save_summaries(summary_payloads)

    if len(summary_payloads) < 3:
        logger.warning("Fewer than 3 summaries generated; newsletter may be short.")

    # Stage 5: Assembly
    quick_hits_source = passed_items[3:] if len(passed_items) > 3 else []
    quick_hits = _build_quick_hits(quick_hits_source)

    strategy_report = _load_reference_text(store, strategy_path, "strategy")
    tone_report = _load_reference_text(store, tone_path, "tone")
    personality_notes = _load_reference_text(store, personality_path, "personality")

    draft, markdown, beehiiv_html = assembly.assemble_newsletter(
        summary_payloads,
        settings,
        quick_hits=quick_hits,
        strategy_report=strategy_report,
        tone_report=tone_report,
        personality_notes=personality_notes,
        issue_number=issue_number,
        issue_date=issue_date,
    )

    draft_artifact = store.save_newsletter(draft, markdown, beehiiv_html)

    # Stage 6: Quality Gates
    quality_report = quality.run_quality_gates(draft, summary_payloads, quick_hits)
    quality_artifact = store.save_quality_report(quality_report)

    # Stage 7: Notifications
    draft_url = draft_artifact.extra.get("markdown_uri", draft_artifact.uri)
    quality_url = quality_artifact.uri

    slack_notifier.send_digest(
        settings.notifications.slack_webhook_env,
        draft_url=draft_url,
        top_picks=summary_payloads,
        quality_report_url=quality_url,
    )
    email_notifier.send_email_digest(
        settings.notifications.recipients or [],
        draft_url=draft_url,
        top_picks=summary_payloads,
    )

    rprint("[green]Newsletter pipeline complete.[/green]")
    rprint(f"Draft saved to: {_format_artifact_display(draft_artifact)}")
    rprint(f"Quality report: {_format_artifact_display(quality_artifact)}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
