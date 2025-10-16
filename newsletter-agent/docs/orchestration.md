# Orchestration Guide (Pure n8n)

Import `workflows/n8n-newsletter-workflow.json` into your n8n instance to run the entire “Abhi’s AI Playbook” curation pipeline without leaving n8n. This guide explains each node, required credentials, and common customisations.

## Node-by-Node Walkthrough

| Order | Node | Purpose | Key Inputs/Outputs |
| --- | --- | --- | --- |
| 1 | **Weekly Schedule** | Cron trigger (default Sunday 06:00 UTC). | Optional: adjust `weekday`, `hour`, `minute`. |
| 2 | **Manual Trigger** | Webhook for on-demand runs (e.g., Slack slash command). | POST JSON body to override defaults (lookback days, sources, strategy text, etc.). |
| 3 | **Run Metadata** | Normalises run configuration and injects defaults (sources, scoring thresholds, LLM provider/model, notification channels, Beehiiv publication ID). | Reads webhook body + env vars. Update the default source lists here. |
| 4 | **Discover Content** | Fetches YouTube videos (Data API + transcript endpoint) and engineering/AI blog posts (RSS → HTML scrape). Returns one item per discovery with embedded config. | Requires `YOUTUBE_API_KEY`. Uses `$httpRequest` internally. |
| 5 | **Normalize & Deduplicate** | Cleans text, strips boilerplate, and removes duplicates using token overlap heuristics. | Produces cleaned items; carries forward `__config` and discovery logs. |
| 6 | **Score & Rank** | Calls Anthropic or OpenAI (based on config) to score content against the rubric (audience fit, practicality, originality, freshness, brand safety). | Needs `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. Output includes score, breakdown, and rationale. |
| 7 | **Aggregate Results** | Splits items into `passed`, `flagged`, and `dropped` collections. | Config thresholds (`min`, `review`) taken from metadata. |
| 8 | **Flagged Items?** | Checks for manual-review items and, if present, routes them to Slack. | |
| 9 | **Slack Flagged Review** | Posts flagged items (scores 50–59) to the review channel with score + rationale. | Configure Slack credentials and review channel in metadata or env vars. |
| 10 | **Any Passed?** | Determines whether any items cleared the auto-publish threshold. | True → continue pipeline. False → trigger “No Draft Alert”. |
| 11 | **No Draft Alert** | Notifies the editorial channel when no items passed scoring (includes flagged count). | Slack credentials required. |
| 12 | **Generate Summaries** | Produces deep structured summaries for the top K items (TL;DR, Why It Matters, actionable bullets, risks, social copy, SEO metadata). | Uses same LLM provider/model as scoring. |
| 13 | **Assemble Draft** | Builds the full newsletter draft (hook, top picks, playbook tip, quick hits, CTA) in Markdown + Beehiiv HTML while mimicking brand voice. | Injects strategy/tone/personality text supplied via metadata/webhook. |
| 14 | **Quality & Outputs** | Runs quality gates (length checks, link validation) and prepares Slack message, Beehiiv payload, and archive bundle (`$json.archive`). | |
| 15 | **Beehiiv Draft** | Conditionally pushes the draft via Beehiiv API (`/v2/publications/{id}/drafts`). Skips gracefully if credentials are missing. | Requires `BEEHIIV_API_KEY` + publication ID (env or metadata). |
| 16 | **Slack Digest** | Sends final status (top picks + Beehiiv status) to the newsletter alerts channel. | Slack credentials. |
| 17 | **Archive to DB (configure)** *(disabled placeholder)* | Attach your datastore node (Airtable, Notion, Postgres) here and use `{{$json.archive}}`. | Enable and configure to persist items/summaries/quality reports. |

## Required Credentials & Environment Vars

Set these in n8n’s credential store or via environment variables referenced by the Function nodes:

- `YOUTUBE_API_KEY` — YouTube Data API v3 key.
- `ANTHROPIC_API_KEY` **or** `OPENAI_API_KEY` — choose one provider and set `LLM_PROVIDER` / `LLM_MODEL` if you want different defaults.
- `BEEHIIV_API_KEY` & `BEEHIIV_PUBLICATION_ID` — optional; if absent the workflow skips the Beehiiv call but still delivers the draft markdown/HTML.
- Slack OAuth or webhook credentials — used by `Slack Flagged Review`, `Slack Digest`, and `No Draft Alert`.
- Optional: `SLACK_NEWSLETTER_CHANNEL`, `SLACK_REVIEW_CHANNEL`, `DEFAULT_LOOKBACK_DAYS`, `LLM_PROVIDER`, `LLM_MODEL`.

## Customising Inputs

- **Webhook payload overrides** — send JSON fields such as `lookback_days`, `youtube_channels`, `blog_feeds`, `strategy_text`, `tone_text`, `personality_text`, `min_score`, `manual_review_floor`, `top_k`, `slack_channel`, or `flagged_channel`.
- **Reference assets** — upstream nodes (Google Drive, Notion, etc.) can fetch documents, then pass their text into the webhook payload before hitting `Run Metadata`.
- **Sources** — edit the default arrays inside `Run Metadata` or supply new ones via payload for non-technical updates.

## Human-in-the-Loop Touchpoints

- **Flagged review** — node 9 posts borderline items for manual decision. Approve/Reject can be handled by adding a “Wait for Webhook” branch that reinjects approved URLs into the pipeline.
- **Editorial approval** — extend the workflow after `Slack Digest` with an approval button (Slack interactivity) if you want the draft to pause before notifying the wider team.
- **Strategy refresh** — create a separate n8n workflow that regenerates strategy/tone reports and stores them; feed the latest text into the webhook payload.

## Scaling & Reliability Tips

- **Rate limits** — the Function nodes already sequence requests; if you hit rate limits, add `Wait` nodes or throttle using `$sleep()` inside the functions.
- **Retries** — wrap high-risk HTTP calls (YouTube, RSS, Beehiiv) in try/catch (already done) and log to Slack or a monitoring channel via an additional branch.
- **Observability** — extend the workflow to push `$json.qualityReport` into Langfuse/PromptMetheus or your analytics stack.
- **Archival** — connect the placeholder Set node to Airtable/Notion/Postgres to keep a queryable history of discoveries, summaries, drafts, and quality results.

## Testing Checklist

1. Import the workflow and wire credentials (YouTube, LLM provider, Slack). Leave Beehiiv unset for dry runs.
2. Trigger manually with a webhook payload containing `lookback_days: 1` to limit scope while testing.
3. Verify Slack messages for flagged items, draft digest, and “no draft” scenario by temporarily setting high thresholds.
4. Once satisfied, enable the cron trigger and the optional Beehiiv node.
5. Integrate your datastore by enabling “Archive to DB (configure)” and replacing it with the connector of your choice.
