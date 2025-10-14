# System Architecture Overview

This document outlines the architecture for the automated newsletter curation system that powers “Abhi's AI Playbook.” The design mirrors Ben’s AI newsletter agency workflow while adding implementation guidance for a production deployment.

## High-Level Workflow

1. **Onboarding & Strategy Layer**
   - Collect brand, audience, and personal context inputs.
   - Generate the Newsletter Strategy Report and Writing Framework Report via LLM prompts.
   - Store approved strategy assets in the datastore for downstream reuse.

2. **Idea & Insight Layer**
   - Accept insights via manual input, link repurposing, or automated discovery.
   - Normalize all idea artefacts into a consistent schema tagged with origin metadata.

3. **Pipeline Execution (Seven Stages)**
   1. **Discover** — Fetch new items from configured YouTube channels and engineering/AI blogs (RSS/api/web scraping). Persist raw assets.
   2. **Normalize & Deduplicate** — Standardize fields, clean text, and remove duplicates using similarity heuristics.
   3. **Relevance/Quality Scoring** — Score each item using the LLM scoring prompt; enforce pass/flag thresholds.
   4. **Deep Summaries** — Generate summary objects for the top K items (TL;DR, Why It Matters, actionable bullets, risks, social copy, SEO metadata, timestamps).
   5. **Newsletter Assembly** — Compose newsletter drafts (Markdown + Beehiiv JSON) that mimic the reference style using strategy + tone reports.
   6. **Quality Gates** — Run factuality, citation, tone, plagiarism, link validation, and length checks with an auditable report.
   7. **Publish/Notify/Archive** — Push drafts to Beehiiv (or Google Docs), notify via Slack/Email, and archive structured data in the datastore.

4. **Human-in-the-loop Checkpoints**
   - Onboarding approval of strategy reports.
   - Manual review queue for borderline scored items (50–59).
   - Final editorial review before distribution.

## Component Breakdown

- **`src/newsletter_agent/config.py`** — Loads YAML/ENV configuration for sources, scoring thresholds, scheduling, LLM providers, and storage credentials. Supports non-technical overrides via config files or Google Sheets sync.
- **`src/newsletter_agent/schemas.py`** — Dataclasses that implement the Item, Summary, and Newsletter Draft contracts to guarantee type-safe payloads.
- **Discovery (`src/newsletter_agent/discovery/`)**
  - `youtube.py` — YouTube Data API client for channel polling + transcript retrieval (YouTube Transcript API fallback).
  - `blogs.py` — RSS ingestion and boilerplate stripping (readability).
  - `manual.py` — Hooks for manual idea ingestion (CLI/web form).
- **Pipeline (`src/newsletter_agent/pipeline/`)**
  - `normalize.py` — Cleaning, deduplication, and text extraction.
  - `scoring.py` — LLM scoring orchestrator with prompt templates and adjustable weightings.
  - `summaries.py` — Deep summary generation with structured outputs.
  - `assembly.py` — Newsletter composer (Markdown + Beehiiv JSON) applying strategy and tone assets.
  - `quality.py` — Quality gate orchestrator generating detailed reports.
- **Storage (`src/newsletter_agent/storage/`)**
  - `datastore.py` — Abstract persistence layer (Airtable/Notion/Postgres/SQLite).
  - `filesystem.py` — Local JSON persistence for development/testing.
- **Notifiers (`src/newsletter_agent/notifiers/`)**
  - `slack.py`, `email.py`, `webhooks.py` — Notification senders with templates.
- **Utilities (`src/newsletter_agent/utils/`)**
  - Prompt rendering, similarity scoring, timestamp helpers, logging.

## Orchestration

- **Primary:** `workflows/n8n-newsletter-workflow.json` (visual N8N design with trigger/schedule, approval nodes, and modular sub-workflows for each stage).
- **Alternative:** Python-based orchestrator (`src/newsletter_agent/cli.py`) using Prefect-like state machine for local runs and testing.
- Scheduling defaults to weekly Sundays at 06:00 UTC with support for manual webhook triggers.

## Data Persistence

- Local development uses `data/` folder with versioned JSON exports of items, summaries, newsletters, and quality reports.
- Production recommends Airtable or Postgres to provide queryable history, with connectors abstracted behind the storage layer.

## Security & Configuration Management

- Secrets (API keys, webhook tokens) pulled from environment variables or `.env` managed by Doppler/1Password.
- Configurable sources and thresholds live in `config/default_config.yaml` and optional Google Sheet integration (CSV sync task).

## Observability

- Structured logging with correlation IDs per run.
- Quality gate reports stored alongside newsletter drafts.
- Optional Langfuse/PromptMetheus integration hooks for prompt A/B tracking.

## Next Steps

1. Implement the modular pipeline components described above.
2. Populate N8N workflow JSON using node templates provided in `docs/orchestration.md`.
3. Connect storage and notifier adapters to the organization’s infrastructure.
