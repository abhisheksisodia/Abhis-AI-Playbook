# Abhi's AI Playbook — Newsletter Agent

End-to-end automation for discovering, scoring, summarising, and drafting Abhi’s AI Playbook. The workflow mirrors Ben’s AI newsletter agency methodology and now runs **entirely inside n8n**—no external runtime required (the Python toolkit remains available for optional CLI runs).

## Key Capabilities
- **Automated discovery** of configurable YouTube channels and engineering/AI blogs (RSS/HTML parsing + transcript fallback).
- **LLM scoring engine** that ranks content against audience fit, practicality, originality, freshness, and brand safety, complete with rationales.
- **Deep structured summaries** (TL;DR, Why It Matters, actionable steps, risks, social copy, SEO metadata, timestamps).
- **Reference-style assembly** that mimics target newsletters while weaving in brand strategy, tone, and personal context.
- **Quality gates & notifications** for length limits, link validation, CTA presence, Beehiiv status, and Slack digests.
- **Archive-ready payloads** for Airtable/Notion/Postgres, plus optional Beehiiv draft publishing.

## Repository Layout
```
├── README.md
├── system-prompt.txt                    # Master system prompt that informed the build
├── docs/
│   ├── architecture.md                  # Architecture reference (n8n-first + optional Python toolkit)
│   ├── orchestration.md                 # Node-by-node n8n guidance
│   └── operations.md                    # Setup, daily ops, troubleshooting
├── src/newsletter_agent/                # Optional Python toolkit (CLI, data contracts, prompt templates)
└── workflows/
    └── n8n-newsletter-workflow.json     # Pure n8n implementation of the full pipeline
```

## Quickstart (n8n Pipeline)
1. **Import the workflow**
   - Upload `workflows/n8n-newsletter-workflow.json` to your n8n instance.
   - Attach credentials for YouTube (`YOUTUBE_API_KEY`), Anthropic/OpenAI, Slack, and (optionally) Beehiiv.

2. **Configure defaults**
   - `Run Metadata` sets default channels, feeds, scoring thresholds, LLM provider/model, notification channels, and Beehiiv publication ID. Update the arrays or override via webhook payload.
   - Provide strategy/tone/personality text via the webhook request body or by inserting upstream nodes (Google Drive/Notion fetch → Function → `Run Metadata`).

3. **Test via webhook**
   - POST to the `Manual Trigger` endpoint with a JSON body:
     ```json
     {
       "issue_number": 42,
       "issue_date": "2024-07-07",
       "lookback_days": 3,
       "strategy_text": "...",
       "tone_text": "...",
       "personality_text": "..."
     }
     ```
   - Confirm:
     - `Slack Flagged Review` posts borderline items (scores 50–59).
     - `Slack Digest` announces the draft.
     - Beehiiv draft is created when credentials are present (otherwise the workflow reports it skipped).

4. **Schedule**
   - Enable the `Weekly Schedule` node (defaults to Sunday 06:00 UTC) once manual runs look good.

5. **Archive (optional)**
   - Replace the disabled “Archive to DB (configure)” node with Airtable/Notion/Postgres connectors. Use `{{$json.archive}}` to persist discoveries, summaries, quality report, markdown, and Beehiiv payload per run.

## Optional CLI Workflow
The Python toolkit mirrors the same prompts and data contracts for teams that prefer code-first automation or need local testing.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export YOUTUBE_API_KEY=...
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY
python -m newsletter_agent.cli run --issue-number 42 --issue-date 2024-07-07
```

Outputs are written to `data/` (items, summaries, draft markdown/HTML, quality report, flagged items).

### Google Drive Storage (optional)
- Set `storage.backend: gdrive` in `config/default_config.yaml` (or your custom config) and provide:
  - `storage.google_drive.base_folder_id` — parent folder for run artifacts.
  - Service-account credentials via `storage.google_drive.credentials_path` or the env var referenced by `credentials_env` (defaults to `GOOGLE_SERVICE_ACCOUNT_JSON`).
  - Optional `storage.google_drive.inputs` file IDs for Strategy, Tone, and Personality docs; the CLI auto-downloads them when local paths aren’t provided.
- When enabled, the CLI uploads items, summaries, flagged items, assembled drafts (JSON/Markdown/HTML), and the quality report directly to Google Drive and shares folder/file links in Slack/email digests.

## Extensibility
- **Sources** — Update `Run Metadata` or pass new JSON payloads to add/remove YouTube channels and blog feeds (tags are preserved for analytics).
- **Notifications** — Attach additional nodes (Teams, Email, Telegram) after `Quality & Outputs` using the provided Slack payload as a template.
- **Storage** — Use the archive payload to upsert records into Airtable/Notion/Postgres for historical analytics.
- **LLM provider/model** — Toggle via env vars (`LLM_PROVIDER`, `LLM_MODEL`) or webhook payload fields; Anthropic and OpenAI are supported out-of-the-box.
- **Prompt experimentation** — Prompts live inside the relevant Function nodes (`Score & Rank`, `Generate Summaries`, `Assemble Draft`). Copy them into Langfuse/PromptMetheus for A/B testing.

## Troubleshooting
- **No discoveries** — Validate `YOUTUBE_API_KEY`, channel IDs, and feed URLs; adjust `lookback_days`.
- **LLM JSON errors** — Reduce temperature or raise `max_tokens` in the Function node; inspect the execution log to see the offending item.
- **Slack messages missing** — Ensure Slack credentials/channel env vars are set for `Slack Flagged Review`, `Slack Digest`, and `No Draft Alert`.
- **Beehiiv draft skipped** — Confirm `BEEHIIV_API_KEY`, publication ID, and that `assembly.beehiiv_html` is non-empty.
- **Link validation fails** — Some sites block `HEAD`; the workflow already falls back to `GET`, but you can tweak timeouts in `Quality & Outputs`.

## Next Steps
1. Connect the archive payload to your CRM/BI tool for historical trend analysis.
2. Add Langfuse/PromptMetheus hooks to track scoring/summarisation prompt performance.
3. Layer factual verification or RAG lookups before publishing.
4. Extend the workflow with branded image generation (Midjourney/Runway) using the reference imagery you collected during onboarding.
