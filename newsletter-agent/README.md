# Abhi's AI Playbook — Newsletter Agent

End-to-end automation for discovering, scoring, summarizing, and drafting the Abhi's AI Playbook newsletter. The system mirrors Ben's AI newsletter agency workflow and is designed to cut manual curation time by 80%+ while protecting editorial quality and voice.

## Key Capabilities
- **Automated discovery** of YouTube channels and engineering/AI blogs with configurable lookback windows.
- **LLM scoring pipeline** that ranks content for audience fit, practicality, originality, freshness, and brand safety.
- **Deep structured summaries** with TL;DRs, why-it-matters, actionable takeaways, risks, social copy, SEO metadata, and timestamps.
- **Newsletter assembly** that mimics reference newsletter tone and structure while generating Markdown + Beehiiv-ready HTML drafts.
- **Quality gates & notifications** covering length limits, link validation, CTA presence, and Slack/email digests.
- **Pluggable storage** (local JSON by default, ready for Airtable/Notion/DB integrations) with archival of items, summaries, drafts, and quality reports.

## Project Layout
```
├── README.md
├── requirements.txt
├── system-prompt.txt
├── config/
│   └── default_config.yaml      # Non-technical configuration for sources, scoring, LLM, storage, notifications
├── docs/
│   ├── architecture.md          # System architecture overview and component map
│   └── orchestration.md         # N8N workflow guidance & human-in-the-loop checkpoints
├── src/newsletter_agent/
│   ├── cli.py                   # Typer CLI orchestrator
│   ├── config.py                # YAML settings loader
│   ├── schemas.py               # Data contracts (Item, Summary, Newsletter)
│   ├── discovery/               # YouTube + blog discovery modules
│   ├── pipeline/                # Normalize, scoring, summaries, assembly, quality gates
│   ├── storage/                 # Local JSON datastore (extensible)
│   ├── notifiers/               # Slack + email notifications
│   └── utils/                   # Logging, text helpers, LLM client abstraction
└── workflows/
    └── n8n-newsletter-workflow.json  # Visual workflow blueprint for production automation
```

## Quickstart
1. **Install dependencies**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Set environment variables**
   ```bash
   export YOUTUBE_API_KEY=...
   export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY if switching providers
   export NEWSLETTER_SLACK_WEBHOOK=... # optional, for Slack notifications
   ```
3. **Update configuration**
   - Edit `config/default_config.yaml` to adjust sources, scoring thresholds, LLM provider/model, notification recipients, and Beehiiv settings.
   - Optionally copy this file to `~/.newsletter-agent-config.yaml` for machine-wide defaults.

4. **Prepare strategy assets**
   - Generate/upload:
     - Newsletter Strategy Report (company positioning, ICP, value pillars).
     - Writing Framework / Tone of Voice report (style, language patterns).
     - Personality context notes (personal stories, professional background).
   - Store them as Markdown or text files to pass into the `cli.py` run.

5. **Run the pipeline**
   ```bash
   python -m newsletter_agent.cli run \
     --issue-number 1 \
     --issue-date 2024-07-07 \
     --strategy docs/strategy-report.md \
     --tone docs/writing-framework.md \
     --personality docs/persona-notes.md
   ```

6. **Review outputs**
   - `data/items.json` — normalized discovery items with metadata.
   - `data/summaries.json` — deep summaries for top picks.
   - `data/issue-<num>-<date>/newsletter.md` — Markdown draft.
   - `data/issue-<num>-<date>/beehiiv.html` — Beehiiv-ready HTML.
   - `data/quality_report.json` — quality gate results.
   - `data/flagged_items.json` — items requiring manual review (scores 50–59).

## Orchestration Options
- **N8N (recommended)** — Import `workflows/n8n-newsletter-workflow.json` to get a ready-to-configure pipeline with schedule trigger, manual approval nodes, and stage-specific sub-workflows.
- **CLI / Cron** — Use `python -m newsletter_agent.cli run ...` in CI/CD, cron, or Prefect/Temporal if you prefer code-based orchestration.

## Extensibility
- **Sources** — Add/remove YouTube channels and blog feeds via `config/default_config.yaml` or an external sheet synced into the config loader.
- **Storage** — Swap `LocalJSONStore` for Airtable, Postgres, or Notion by adding a new class implementing `BaseDatastore`.
- **Notifications** — Extend `src/newsletter_agent/notifiers` with additional channels (e.g., Telegram, Teams).
- **LLM Provider** — Toggle between Anthropic and OpenAI by changing the `llm` block in config and exporting the appropriate API key environment variable.
- **Prompt Experimentation** — The prompt templates in `pipeline/scoring.py`, `pipeline/summaries.py`, and `pipeline/assembly.py` are centralized; connect them to Langfuse/PromptMetheus for versioning and A/B testing.

## Troubleshooting
- **Missing API keys** — The CLI will raise explicit errors if required keys (YouTube, LLM, Beehiiv) are absent. Confirm they are exported in the shell or the hosting platform’s secret manager.
- **LLM JSON parsing issues** — Outputs are validated; failures are logged with the offending item ID. Adjust temperature or refine prompts if hallucinations occur.
- **Discovery gaps** — Increase `sources.schedule.lookback_days` or inspect channel/feed IDs. For blogs without RSS, integrate a scraper and register it in `discovery/`.
- **Link validation errors** — `quality.py` performs `HEAD` requests; some sites block them. Modify `_validate_links` to fall back to `GET` if required.

## Next Steps
1. Connect the N8N workflow to production credentials and set schedule/manual triggers.
2. Wire up Beehiiv API calls inside `assembly` or a dedicated delivery module.
3. Add persistence adapters for Airtable/Notion and integrate Langfuse prompt analytics.
4. Expand the quality gate suite with factual verification via retrieval or source quoting.
