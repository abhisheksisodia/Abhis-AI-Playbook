# Operations Playbook

This guide documents setup, day-to-day operations, source management, and troubleshooting for the Abhi's AI Playbook newsletter system.

## 1. Initial Setup

1. **Provision credentials**
   - YouTube Data API key (`YOUTUBE_API_KEY`)
   - LLM provider key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
   - Beehiiv API key (`BEEHIIV_API_KEY`) & publication ID
   - Slack Incoming Webhook (`NEWSLETTER_SLACK_WEBHOOK`)
   - Optional: Airtable/Notion/Postgres credentials for persistence

2. **Configure sources**
   - Edit `config/default_config.yaml` (or override at `~/.newsletter-agent-config.yaml`) with YouTube channels and blog feeds.
   - Each source supports `tags` used for downstream filtering and analytics.
   - For non-RSS blogs, add custom scrapers (see §4.3).

3. **Prepare reference assets**
   - Store the following in a shared drive or repo:
     - Newsletter Strategy Report (Markdown/PDF)
     - Writing Framework / Tone of Voice report
     - Personality background notes (stories, anecdotes)
     - 3–5 reference newsletter examples (Markdown/PDF)
     - Reference brand imagery (for future design automation)

4. **Install runtime**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## 2. Operational Runbook

1. **Trigger**
   - N8N cron trigger (default Sunday 06:00 UTC) or manual webhook call.
   - Local testing: `python -m newsletter_agent.cli run --issue-number 42 --issue-date 2024-07-07`.

2. **Monitor**
   - CLI logs stream in the terminal or capture via your orchestrator (N8N/Prefect).
   - Slack digest posts to #newsletter-alerts with draft + quality summary.
   - Flagged borderline items appear in `data/flagged_items.json` and Slack thread for approval.

3. **Review**
   - Open `data/issue-xx-YYYY-MM-DD/newsletter.md` for the Markdown draft.
   - Inspect `data/quality_report.json` for any failed checks.
   - Apply editorial tweaks and publish from Beehiiv draft.

4. **Archive**
   - JSON outputs stored in `data/` for auditability.
   - Optional: push to Airtable/Notion using datastore adapters.

## 3. Source Management

1. **Add / remove sources**
   - Update `config/default_config.yaml` and commit.
   - For business-facing configuration, sync a Google Sheet and modify `sources.manual_sources_sheet` to automate ingestion.

2. **Tagging strategy**
   - Use tags to categorize content by pillar (e.g., `frameworks`, `builder`, `case-study`).
   - Downstream analytics can filter on tags to balance content mix.

3. **Handling paywalled or unstable feeds**
   - Use the `manual` discovery method to ingest curated links.
   - Configure an additional N8N branch that watches a “Manual Insights” Google Sheet and appends entries into the pipeline.

4. **Scraping non-RSS blogs**
   - Implement a custom fetcher in `src/newsletter_agent/discovery/` (e.g., `custom_blog.py`).
   - Register the scraper in the CLI by importing it in `cli.py` and merging results with other sources.

## 4. Prompt & Model Optimization

1. **Prompt storage**
   - Scoring, summary, and assembly prompts live in `pipeline/scoring.py`, `pipeline/summaries.py`, and `pipeline/assembly.py`.
   - Version prompts using Git or a prompt management tool (Langfuse/PromptMetheus).

2. **Experimentation workflow**
   - Use Langfuse/PromptMetheus to toggle context variables (strategy, tone, references) and track impact.
   - Maintain color-coded context variables (green = LLM generated, blue = user provided).

3. **Model selection**
   - Default: Claude 3.5 Sonnet for writing-heavy tasks.
   - Alternative: `gpt-4o` for lower latency or `gpt-4.1` for coding-style reasoning.
   - Adjust via `llm.provider` and `llm.model` in the config.

## 5. Troubleshooting

| Symptom | Likely Cause | Resolution |
| --- | --- | --- |
| No YouTube results | Expired API key, wrong channel ID | Verify `YOUTUBE_API_KEY`; confirm channel ID via YouTube Studio |
| LLM JSON parsing errors | Hallucination / truncated response | Reduce temperature, increase `max_output_tokens`, add `json` tool call for OpenAI |
| Slack digest missing | `NEWSLETTER_SLACK_WEBHOOK` not set | Export webhook env var or disable Slack notifier |
| Beehiiv draft creation fails | Missing publication ID or API key | Double-check credentials in N8N or `.env`; verify API scope |
| Link validation false negatives | Sites block HEAD requests | Modify `_validate_links` in `quality.py` to fallback to GET |

## 6. Enhancements Roadmap

- Add factual verification by sampling quotes and cross-checking via retrieval (SerpAPI/Bing Search).
- Integrate Whisper Flow for voice-to-text manual insights and append to discovery stage.
- Implement Airtable datastore adapter for collaborative review workflows.
- Generate branded hero images via RUNWAY or Midjourney API, guided by reference imagery.
- Extend Quick Hits section with automated TL;DR generation per item (mini summarization pass).
