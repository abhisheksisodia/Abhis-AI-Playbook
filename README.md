# OBS Automation Playbook

## Overview
This repository contains production-ready n8n assets for the Onboarding Specialist (OBS) automation. The stack orchestrates Gmail, Google Drive, Google Calendar, Google Sheets, PostgreSQL, and OpenAI (JSON mode) to deliver deterministic onboarding outcomes.

## Prerequisites
- n8n v1.42+ running in queue mode with worker(s)
- Redis configured for n8n queue execution
- PostgreSQL 15 or newer
- Google Workspace service account with delegated domain-wide authority for Gmail, Drive, Calendar, and Sheets
- Published Google Sheets for playbooks, templates, checklists, and FAQs (share with service account)
- OpenAI API key with access to `gpt-4o-mini`
- Shared Gmail alias (e.g., `obs@demo.local`) with IMAP/label permissions
- HTTPS endpoint for public upload webhooks (`APP_BASE_URL`)

## Environment Variables
Create a `.env` file (see [.env.example](./.env.example)) and populate the required credentials:
- PostgreSQL host, database, user, password
- Google service account project ID, client email, and escaped private key
- Gmail alias and Drive Shared Drive ID
- Sheets IDs for playbooks, templates, checklists, FAQs
- OpenAI API key
- Google Chat space webhook URL
- Application base URL for public uploads

## Database Setup
Run the migration before importing workflows:
```bash
psql "$POSTGRES_URL" -f db/001_init.sql
```
Ensure the `citext` extension is available if using PostgreSQL without it pre-installed.

## Importing Workflows
1. Log into the n8n editor UI.
2. Use **Import from File** and select each JSON under `workflows/`.
3. After import, assign the workflow IDs to match the file names (n8n retains names automatically).
4. Activate the workflows once credentials are connected.

## Credential Wiring in n8n
Create the following credentials and update node references:
- **Gmail OAuth2** → `OBS Gmail Service`
- **Google Drive Service Account** → `OBS Google Drive`
- **Google Calendar OAuth2** → `OBS Google Calendar`
- **Google Sheets OAuth2** → `OBS Google Sheets`
- **Postgres** → `OBS Postgres`
- **OpenAI** → `OBS OpenAI`
- **Google Vision** (optional) → `OBS Google Vision`

## Google Sheets Configuration
1. Publish each seed CSV in `sheets/` to Google Sheets.
2. Share the Sheets with the service account email.
3. Copy the Sheet IDs and set the environment variables:
   - `SHEETS_PLAYBOOK_ID`
   - `SHEETS_TEMPLATES_ID`
   - `SHEETS_CHECKLISTS_ID`
   - `SHEETS_FAQS_ID`
4. Verify ranges match the expected tab names (`playbooks!A:G`, `templates!A:D`, etc.).

## Google Drive Structure
Create a Shared Drive and store its ID in `DRIVE_SHARED_DRIVE_ID`. The workflows create folders automatically:
```
Shared Drive /
  Clients /
    {CLIENT_ID}_{OrgName} /
      business_license /
      id_front /
      floor_plan /
      _meta /
        client.json
```

## Gmail Labels
Create the following labels ahead of time:
- `OBS/NEW`
- `OBS/INTAKE_PENDING`
- `OBS/DOCS_REQUESTED`
- `OBS/DOCS_RECEIVED`
- `OBS/VALIDATED`
- `OBS/SCHEDULED`
- `OBS/COMPLETE`
- `OBS/ON_HOLD`
- `OBS/ESCALATED`

## Workflow Summary
- **EDGE_Inbound_Router**: Classifies inbound Gmail, applies idempotency guard, dispatches to downstream DOM workflows, and logs audits.
- **DOM_New_Client_Intake**: Handles CRM/webhook intake, creates Drive structures, generates upload links, and sends intro emails.
- **DOM_Doc_Request**: Issues document requests, ensures Drive subfolders, starts reminder cadences, and updates client status.
- **DOM_Doc_Intake_And_Validation**: Processes uploads via webhook or Gmail attachments, performs virus scanning, runs AI extraction, and updates requirement statuses.
- **DOM_Scheduling_Orchestrator**: Builds candidate slots or processes booking payloads, books calendar events, and kicks off training cadences.
- **DOM_Reminder_Cadence**: Reads cadence definitions and dispatches timed reminder emails.
- **DOM_QA_Auto_Reply**: Generates FAQ answers with guardrails and escalates when confidence is low.
- **DOM_Completion_And_Handoff**: Generates PDF summaries, emails stakeholders, updates CRM, and finalizes client status.
- **DOM_Escalation**: Posts actionable cards to Google Chat, waits for responses, and labels Gmail.
- **OPS_Error_Inbox**: Centralized notification for failed executions with replay links.

## Runbooks
### 1. Add a New Segment via Sheets
1. Duplicate `sheets/playbooks.csv` row in Google Sheets with a new segment key and custom JSON settings.
2. Add matching rules in the `checklists` tab and templates if required.
3. Update `cadences_json` as needed.
4. No workflow changes required—new segment is auto-picked on next run.

### 2. Pause & Resume a Client
1. Set `status = 'ON_HOLD'` in the `clients` table (manual SQL) or trigger `DOM_Escalation` with context.
2. Resume by updating status to the appropriate pipeline stage and optionally re-running the necessary DOM workflow.

### 3. Re-validate a Document
1. In `doc_requirements`, set the target row’s `status` back to `PENDING`.
2. Re-invite the client via `DOM_Doc_Request` to regenerate upload links.
3. Upon new upload, `DOM_Doc_Intake_And_Validation` performs validation.

### 4. Adjust Cadences & Templates
1. Modify cadence arrays in the playbook sheet (JSON cell).
2. Update the template body/subject in the templates sheet.
3. Changes take effect on the next workflow execution—no redeploy needed.

### 5. Troubleshoot Failed Runs (OPS_Error_Inbox)
1. Monitor Gmail alias and Google Chat space for failure alerts.
2. Use the replay link in the alert to reopen the execution in n8n.
3. Fix the underlying issue (credentials, schema mismatch, etc.).
4. Replay from the failed node or re-trigger the originating workflow.

## Public Upload Portal Response
The `DOM_Doc_Intake_And_Validation` webhook returns HTML responses. Customize the Function node to deliver a branded confirmation page similar to:
```html
<html>
  <body>
    <h1>Upload received</h1>
    <p>Thanks for submitting your {{doc_type}}. We will validate it shortly.</p>
  </body>
</html>
```

## OpenAI Usage
All OpenAI nodes run in JSON-only mode and validate against explicit schemas before downstream nodes execute. Update rate limits and concurrency in n8n’s settings if you observe throttling.

## Support
For operational runbooks or escalations, ping the `#obs-automation` channel or email `ops@demo.local`.
