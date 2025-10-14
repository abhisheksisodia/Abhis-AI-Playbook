"""Command-line interface for running the newsletter pipeline."""

from __future__ import annotations

import json
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
from .storage.datastore import LocalJSONStore
from .utils.logger import get_logger, setup_logger
from .utils.text import truncate_words

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


def _save_flagged(items: list[ItemPayload], store: LocalJSONStore) -> None:
    if not items:
        return
    path = store.base_path / "flagged_items.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump([item.to_dict() for item in items], handle, indent=2)
    get_logger("cli").info("Flagged items saved to %s", path)


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
    store = LocalJSONStore(settings.storage.path)

    # Stage 1 & 2: Discovery
    youtube_items = youtube_discovery.discover(settings)
    blog_items = blog_discovery.discover(settings)
    all_items = youtube_items + blog_items
    normalized_items = normalize.normalize_items(all_items)
    store.save_items(normalized_items)

    # Stage 3: Scoring
    passed_items, flagged_items = scoring.score_items(normalized_items, settings)
    _save_flagged(flagged_items, store)

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

    strategy_report = _read_optional_file(strategy_path)
    tone_report = _read_optional_file(tone_path)
    personality_notes = _read_optional_file(personality_path)

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

    draft_dir = store.save_newsletter(draft, markdown, beehiiv_html)

    # Stage 6: Quality Gates
    quality_report = quality.run_quality_gates(draft, summary_payloads, quick_hits)
    quality_path = store.save_quality_report(quality_report)

    # Stage 7: Notifications
    draft_url = f"file://{draft_dir / 'newsletter.md'}"
    quality_url = f"file://{quality_path}"

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
    rprint(f"Draft saved to: {draft_dir}")
    rprint(f"Quality report: {quality_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
