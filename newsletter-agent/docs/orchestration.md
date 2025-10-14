# Orchestration Guide (N8N)

The `workflows/n8n-newsletter-workflow.json` file provides a ready-to-import blueprint for building the production automation in N8N. This document explains the stages, required environment variables, and human-in-the-loop checkpoints.

## Workflow Overview

1. **Trigger Layer**
   - `Cron` node (default: Sunday 06:00 UTC) for scheduled runs.
   - `Webhook` node for manual triggers (e.g., triggered from Slack slash command).

2. **Context Warm-Up**
   - `Google Drive` / `Notion` nodes to fetch the latest Strategy Report, Tone of Voice Report, and Personality Notes.
   - `IF` node ensures all required context files exist; otherwise routes to Slack alert.

3. **Discovery Sub-Workflow**
   - `Execute Command` or `HTTP Request` nodes that call the CLI’s discovery endpoints (or direct API integrations).
   - YouTube stage uses the YouTube Data API node; blog stage uses RSS fetch nodes.
   - Combined payloads stored in `Items` collection and forwarded.

4. **Normalization & Deduplication**
   - `Code` node (JavaScript) leveraging the token sort ratio snippet provided in the JSON export.
   - Deduplicated list persisted to Airtable/Notion via connectors.

5. **Scoring Stage**
   - `OpenAI` / `HTTP Request` node pointing at Anthropic’s Messages API (depending on provider).
   - `SplitInBatches` + `Wait` nodes to respect rate limits.
   - Branch: `IF` node routes items scoring 50–59 to a Slack approval thread.

6. **Summaries Stage**
   - Batched LLM calls generating structured summaries; the JSON schema is enforced via `Function` nodes before persisting to datastore.
   - `Set` node keeps only the top `top_k` items as defined in config.

7. **Assembly Stage**
   - `Execute Command` node calling `python -m newsletter_agent.cli assemble ...` or direct LLM call producing Markdown + Beehiiv HTML.
   - Reference newsletter files loaded from Google Drive and injected as binary data for prompt context.

8. **Quality Gates**
   - `HTTP Request` node for link validation (HEAD requests).
   - `Function` node for TL;DR length checks and CTA validation.
   - `Merge` node collates pass/fail results into a quality report.

9. **Delivery & Notifications**
   - `Beehiiv` API node (POST `/v2/publications/{id}/drafts`) using API key from credentials store.
   - `Slack` node posts draft link, top picks, and quality summary.
   - `Email` node sends digest to the editorial team.

10. **Archival**
    - `Airtable` or `Postgres` nodes persist items, summaries, newsletter JSON, and quality report.
    - `Google Drive` node saves Markdown + HTML backups.

## Human-in-the-loop Touchpoints

- **Strategy Approval** — After the onboarding prompt run, send report to Slack with “Approve / Revise” buttons. Use `Wait for Webhook` to pause the workflow until approved.
- **Borderline Items Review** — Items scoring between 50–59 are posted to a Slack thread with Approve/Snooze buttons. Approved links are reinjected into the pipeline via a webhook.
- **Final Editorial Review** — The Beehiiv draft link is posted with a “Mark as Approved” button; the workflow only notifies the wider team once approved.

## Environment & Secrets

Configure the following credentials in N8N:
- `YOUTUBE_API_KEY`
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- `BEEHIIV_API_KEY` and `publication_id`
- Slack webhook / bot token
- Airtable API key & base ID (if used)
- Google Drive service account (for reference documents)

## Scaling Considerations

- Use `SplitInBatches` with concurrency controls to respect LLM rate limits.
- Persist intermediate outputs (items, summaries) to a database so failed runs can resume without repeating earlier stages.
- Add retry + error branches (`Error Workflow`) to handle transient API failures gracefully.
- Instrument with Langfuse or PromptMetheus by logging prompt IDs and timings in dedicated nodes.

## Customization Checklist

1. Replace placeholder channel/feed IDs in the configuration sheet or `default_config.yaml`.
2. Update the Beehiiv publication ID and Slack channels in the workflow.
3. Upload 3–5 reference newsletters (PDF/Markdown) to your storage provider; update file IDs in the “Context Warm-Up” section.
4. Connect the manual insights intake (e.g., voice notes via Whisper Flow) by adding a branch that appends manual insights to the discovery payload.
5. Test each stage individually in N8N’s “Execute Node” mode before enabling the full schedule.
