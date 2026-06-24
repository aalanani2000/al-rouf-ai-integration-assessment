# Task 1: RFQ To CRM Automation

This task implements an RFQ intake workflow using n8n as the orchestration tool. The workflow simulates an inbound RFQ through a webhook, extracts useful intent from the free-text message with OpenAI, creates a mock CRM record, drafts a bilingual reply, and writes an internal sales alert.

## What It Does

1. Accepts an inbound RFQ payload through a webhook.
2. Extracts structured intent from the RFQ message body.
3. Merges AI-extracted intent with already structured RFQ fields.
4. Adds CRM metadata such as record ID, timestamp, and status.
5. Writes the resulting CRM record to `data/mock_crm.json`.
6. Generates a professional English and Arabic client reply draft.
7. Writes an internal sales alert to `data/alerts.json`.

## Key Files

| File | Purpose |
|---|---|
| `n8n_workflows/rfq-crm-automation.json` | Exported n8n workflow definition. |
| `../docker-compose.yml` | Starts the local n8n container and mounts persistent data volumes. |
| `../data/mock_crm.json` | Mock CRM storage written by the workflow. |
| `../data/alerts.json` | Internal alert log written by the workflow. |
| `../docs/evidence/task1_rfq_crm_automation/execution_notes.md` | Detailed build notes, decisions, validation, and AI disclosure. |
| `../docs/screenshots/Task 1/` | Screenshots showing workflow construction, node configuration, errors, fixes, and successful runs. |

## Running The Workflow

Start n8n from the repository root:

```bash
docker-compose up -d
```

Open n8n at:

```text
http://localhost:5678
```

Import the workflow:

```text
task1_rfq_crm_automation/n8n_workflows/rfq-crm-automation.json
```

Configure the OpenAI credential inside n8n, then activate or manually execute the workflow. Use n8n's generated webhook URL for the `Webhook` node when sending test requests.

## Example Test Payload

```json
{
  "company_name": "Gulf Construction LLC",
  "contact_name": "Ahmed Al-Mutairi",
  "contact_email": "ahmed@gulfconstruction.sa",
  "contact_phone": "+966500000000",
  "product_interest": "LED High Bay Lights, 150W",
  "quantity": 200,
  "project_location": "Riyadh, Saudi Arabia",
  "deadline": "2026-07-15",
  "attachments": ["site_plan.pdf", "spec_sheet.pdf"],
  "message_body": "We need a quotation for 200 high bay LED lights for a warehouse project. Please include bulk pricing, delivery timeline, and warranty terms."
}
```

## Validation Evidence

The workflow was validated end to end through multiple n8n test executions. Evidence includes:

- Webhook configuration and canvas screenshots.
- OpenAI extraction node configuration.
- Edit Fields node output with merged structured data.
- Docker volume screenshot proving persistent storage was attached.
- Debug evidence for the n8n Code node `fs` module sandbox limitation.
- Successful workflow execution screenshots.
- Persisted mock CRM and alert JSON outputs.

## Implementation Decisions

- n8n was used as an equivalent orchestration approach because it can run locally and export workflow JSON into the repository.
- The webhook was used instead of IMAP/email to keep the assessment reproducible without OAuth or mailbox setup.
- JSON files were used as a mock CRM and alert store because they are inspectable, simple, and sufficient for assessment evaluation.
- AI calls were scoped to the parts that benefit from language understanding: RFQ intent extraction and bilingual reply drafting.
- Attachment archiving is partially implemented: filenames are preserved as metadata. A production version should accept real file bytes and store them under a CRM-record-specific archive path.

## Future Enhancements

- Replace the webhook simulation with real inbound email, website form, or WhatsApp Business ingestion.
- Store real attachment files, not only filenames.
- Add duplicate RFQ detection and customer matching.
- Push internal alerts to email, Slack, Teams, or a CRM activity feed.
- Add approval steps before sending bilingual replies to customers.
- Add retry and dead-letter handling for failed AI or persistence steps.

## AI Assistance Disclosure

AI assistance was used for architecture discussion, starter Code node logic, debugging support, and documentation polishing. The candidate completed the n8n workflow wiring, node configuration, Docker setup, testing, screenshot collection, and final implementation decisions.
