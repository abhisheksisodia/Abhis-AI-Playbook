# Operations Playbook

This guide covers setup, day-to-day operations, source management, and troubleshooting for the n8n-first Abhi's AI Playbook newsletter system.

## 1. Initial Setup

1. **Provision credentials**
   - YouTube Data API key (`YOUTUBE_API_KEY`)
   - LLM provider key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
   - Beehiiv API key (`BEEHIIV_API_KEY`) & publication ID
   - Slack OAuth/Webhook credentials for notifications
   - Optional: Airtable/Notion/Postgres credentials if you plan to archive structured data
   - Optional: Google Drive service-account JSON (if you want the CLI to read/write via Drive)

2. **Import the workflow**
   - Upload `workflows/n8n-newsletter-workflow.json` to n8n.
   - Assign the credentials above to the relevant nodes (`Discover Content`, `Score & Rank`, `Generate Summaries`, `Beehiiv Draft`, Slack nodes).

3. **Prepare reference assets**
   - Store your Strategy report, Tone of voice guide, and Personality notes somewhere accessible (Notion, Google Drive, Git). Either paste them directly into the webhook payload or add upstream nodes to fetch them before `Run Metadata`.
   - Keep 3–5 reference newsletters handy to iterate on prompts.

4. **Set defaults**
   - Update the channel/feed defaults inside the `Run Metadata` function if you want different starting sources.
   - Optionally define env vars on the n8n worker (e.g., `LLM_PROVIDER`, `LLM_MODEL`, `SLACK_NEWSLETTER_CHANNEL`, `DEFAULT_LOOKBACK_DAYS`).

## 2. Operational Runbook

1. **Trigger**
   - Scheduled: enable the `Weekly Schedule` node (defaults to Sunday 06:00 UTC).
   - Manual: POST to the `Manual Trigger` webhook with overrides (`lookback_days`, `strategy_text`, etc.) when you need an ad-hoc run.

2. **Monitor**
   - n8n execution logs show each stage; inspect Function node output for debug info.
   - `Slack Flagged Review` posts borderline items (scores 50–59) to the review channel.
  - `Slack Digest` posts draft status, top picks, and Beehiiv result to the newsletter channel.

3. **Review**
   - If Beehiiv credentials are present, open the draft via the link in Slack; otherwise, grab markdown/HTML from the `Quality & Outputs` node (or archive payload).
   - Check the quality report summary in Slack (length limits, link validation results).
   - Apply final edits and publish from Beehiiv once approved.

4. **Archive**
   - Enable the placeholder node `Archive to DB (configure)` and connect Airtable/Notion/Postgres (use `{{$json.archive}}`).
   - Store the full archive payload per run to keep sources, summaries, drafts, and quality checks queryable.

5. **Google Drive storage (CLI)**
   - Switch `storage.backend` to `gdrive` and set `storage.google_drive.base_folder_id` to the parent folder for issue folders.
   - Provide credentials via `storage.google_drive.credentials_path` or set the JSON in the env var referenced by `credentials_env` (defaults to `GOOGLE_SERVICE_ACCOUNT_JSON`).
   - If you store Strategy/Tone/Personality docs in Drive, drop their file IDs under `storage.google_drive.inputs.*`; the CLI fetches the latest content automatically when local files aren’t passed.
   - All CLI outputs (items, summaries, flagged list, newsletter JSON/Markdown/HTML, quality report) are uploaded to the run’s Drive folder, and Slack/email digests link to those artifacts.

## 3. Source Management

1. **Add / remove sources**
   - Edit the arrays in `Run Metadata` (`youtubeChannels`, `blogFeeds`).
   - Or pass new sources via webhook payload: `{ "youtube_channels": [...], "blog_feeds": [...] }`.

2. **Tagging strategy**
   - Use tags to categorize content by pillar (e.g., `frameworks`, `builder`, `case-study`).
   - Downstream analytics can filter on tags to balance content mix.

3. **Handling paywalled or unstable feeds**
   - Add a separate Function/Webhook branch to append manually curated links before `Normalize & Deduplicate`.
   - For paywalled sources, capture summaries via manual input (Webhook payload can include pre-written insights).

4. **Scraping non-RSS blogs**
   - Extend the `Discover Content` node (it already fetches HTML and strips boilerplate). Add extra parsing logic or additional endpoints as needed.

## 4. Prompt & Model Optimization

1. **Prompt storage**
   - Scoring, summaries, and assembly prompts live directly inside the respective Function nodes (`Score & Rank`, `Generate Summaries`, `Assemble Draft`).
   - Copy them into Langfuse/PromptMetheus for A/B testing and keep versions in Git alongside this repo.

2. **Experimentation workflow**
   - Adjust metadata payloads (e.g., toggle strategy text, tone text) to AB-test context.
   - Log experiments by extending Function nodes with `$emit` to your telemetry stack.

3. **Model selection**
   - Default: Claude 3.5 Sonnet for writing-heavy tasks.
   - Alternative: `gpt-4o` / `gpt-4.1` for latency tweaks.
   - Set `LLM_PROVIDER` / `LLM_MODEL` env vars or pass via webhook payload to switch models at runtime.

## 5. Troubleshooting

| Symptom | Likely Cause | Resolution |
| --- | --- | --- |
| No YouTube results | Expired API key or wrong channel ID | Verify `YOUTUBE_API_KEY`; confirm channel IDs in `Run Metadata`. |
| LLM JSON parse errors | Model hallucinated malformed JSON | Lower temperature, increase `max_tokens`, or switch providers; inspect `Score & Rank` / `Generate Summaries` logs. |
| Slack messages missing | Slack credentials not attached | Open the Slack node, assign credentials, or set channel env vars. |
| Beehiiv draft skipped | Missing API key/publication ID or HTML empty | Set `BEEHIIV_API_KEY` and publication ID; confirm assembly returned HTML. |
| Link validation failures | Sites block HEAD requests | Use the GET fallback already in place or adjust timeout. |

## 6. Enhancements Roadmap

- Add factual verification by sampling quotes and cross-checking via retrieval (SerpAPI/Bing Search).
- Integrate Whisper Flow for voice-to-text manual insights and append to discovery stage.
- Wire the archive payload into Airtable/Notion for collaborative review.
- Generate branded hero images via RUNWAY or Midjourney API, guided by reference imagery.
- Extend Quick Hits section with automated TL;DR generation per item (mini summarization pass).
