# System Architecture Overview

This document outlines the architecture for the automated newsletter curation system that powers “Abhi's AI Playbook.” The design now ships as a **pure n8n workflow** (no external runtime required) that mirrors Ben’s agency process end-to-end, with an optional Python toolkit retained for teams that prefer code-driven orchestration.

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

## Primary Implementation: `workflows/n8n-newsletter-workflow.json`

The workflow is organised into modular n8n nodes that map directly to the seven stages:

| Stage | n8n Nodes | Notes |
| --- | --- | --- |
| Trigger & Context | `Weekly Schedule`, `Manual Trigger`, `Run Metadata` | Weekly cron + webhook input. `Run Metadata` normalises payloads and injects defaults (sources, scoring, LLM config, Beehiiv settings). |
| Discover | `Discover Content` | Fetches YouTube content (Data API + transcript endpoint) and blog posts (RSS→HTML). All logic lives in one Function node using `$httpRequest`, so no external runtime is required. |
| Normalize & Deduplicate | `Normalize & Deduplicate` | Cleans text, removes boilerplate, and handles URL/title dedupe with token overlap heuristics. |
| Score | `Score & Rank` | Calls Anthropic or OpenAI (selected in config) to produce structured scores + rationales. |
| Aggregate & Review | `Aggregate Results`, `Flagged Items?`, `Slack Flagged Review`, `Any Passed?` | Splits items into passed / flagged / dropped, posts manual-review alerts to Slack, and gates the downstream workflow if nothing passes the threshold. |
| Summaries | `Generate Summaries` | Generates deep structured summaries (TL;DR, Why It Matters, actionable bullets, social copy, SEO metadata). |
| Assembly | `Assemble Draft` | Compiles reference-style markdown + Beehiiv HTML using strategy, tone, personality context, and structured summaries. |
| Quality & Delivery | `Quality & Outputs`, `Beehiiv Draft`, `Slack Digest`, `Archive to DB (configure)` | Runs quality gates (length, link validation, counts), prepares Beehiiv payloads, conditionally pushes a draft via API, sends digest to Slack, and exposes an archive payload for Airtable/Notion/DB adapters. |
| Fallback Notification | `No Draft Alert` | Notifies editors when no content cleared the scoring threshold. |

Key design choices:

- **Single execution context** – every API call happens via n8n Function/HTTP nodes; there is no dependency on the Python CLI.
- **Config-first** – thresholds, sources, LLM provider/model, and notification channels are controlled through the metadata function (and can be overridden via webhook payload or env vars).
- **Graceful degradation** – the Beehiiv node checks credentials before writing, Slack alerts fire even if Beehiiv is skipped, and manual-review notifications flow regardless of draft success.
- **Archive hook** – the “Archive to DB (configure)” Set node is disabled by default and exists as a placeholder to connect Airtable, Notion, Postgres, etc., using the structured `archive` payload from `Quality & Outputs`.

Refer to `docs/orchestration.md` for node-by-node wiring guidance, required credentials, and scaling considerations.

## Optional Python Toolkit

The Python package under `src/newsletter_agent/` mirrors the same data contracts and prompt templates and can be used for:

- local testing or CLI-driven runs (`python -m newsletter_agent.cli run ...`);
- automated regression tests against fixed fixtures;
- building alternate orchestrations (e.g., Prefect/Temporal) if you migrate away from n8n in the future.

## Data Persistence & Configuration

- **n8n storage** – the workflow emits archive-ready JSON (`$json.archive`) containing items, summaries, quick hits, flagged content, quality report, markdown, and Beehiiv payloads.
- **Secrets** – provide API keys (YouTube, Anthropic/OpenAI, Beehiiv, Slack) via n8n credentials or environment variables referenced in the Function nodes.
- **Source management** – update the default channel/feed lists inside `Run Metadata` or supply overrides via webhook payload/Google Sheet before the run.

## Observability

- Quality reports and logs are bundled in the archive payload for downstream analysis.
- Slack notifications surface both successful drafts and review-required items.
- Extend with Langfuse/PromptMetheus by adding logging inside the scoring/summarisation Function nodes (placeholders called out in the code).

## Next Steps

1. Import `workflows/n8n-newsletter-workflow.json` into your n8n instance and configure credentials (YouTube Data API, Anthropic/OpenAI, Slack, Beehiiv).
2. Connect the optional archive node to Airtable/Notion/Postgres as your source of record.
3. Plug in your strategy, tone, and personality texts via the webhook payload or upstream nodes (Google Drive/Notion) so the assembly stage mirrors your brand voice.
