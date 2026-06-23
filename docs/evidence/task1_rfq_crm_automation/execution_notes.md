# Task 1 — RFQ → CRM Automation: Execution Notes

## Approach

I used n8n, self-hosted via Docker, as the orchestration layer instead of Zapier or Make. The brief explicitly allows "an equivalent orchestration approach," and n8n let me keep the entire workflow definition version-controlled as exported JSON inside the repository — something a SaaS-only tool like Zapier can't offer, since the workflow logic lives entirely outside any repo you could share.

The workflow simulates an inbound RFQ via a webhook (rather than a live email/IMAP integration), parses it, runs the free-text portion through an AI extraction step, merges everything into a single structured record, writes it to a mock CRM store on disk, drafts a bilingual client reply, and logs an internal alert containing that reply for the sales team to action.

## Steps Taken

1. **Webhook trigger** — set up a POST endpoint at `/rfq-intake` that accepts a JSON payload representing an inbound RFQ (company details, product interest, quantity, deadline, attachments, and a free-text message body).

2. **AI field extraction (OpenAI node)** — scoped the AI call specifically to the `message_body` field, since the rest of the payload already arrives as clean structured JSON. The model (GPT-5.4-nano) extracts urgency level, key requirements, and a one-sentence summary, returned as strict JSON.

3. **Field merge (Edit Fields node)** — combined the structured webhook fields with the parsed AI output into one unified record (`company_name`, `contact_name`, `quantity`, `product_interest`, `extracted_intent`, etc.).

4. **CRM metadata (Edit Fields1 node)** — added a generated `crm_record_id` and `created_at` timestamp as a separate step, since this metadata is specific to the CRM persistence layer rather than the RFQ content itself.

5. **Mock CRM write (Read → Code → Write pattern)** — implemented persistence to a JSON file acting as the mock CRM. Initial attempt used a single Code node with Node's `fs` module directly, but n8n's Code node runs in a sandboxed VM2 environment that explicitly blocks built-in modules like `fs` — this surfaced as a "Cannot find module 'fs'" runtime error. Pivoted to n8n's native Read/Write Files from Disk nodes for actual filesystem I/O, with a Code node handling only in-memory JSON merge logic via binary buffers.

6. **Bilingual reply draft (second OpenAI node)** — given the merged RFQ record, generates a professional acknowledgment reply in both English and Arabic, explicitly instructed not to include pricing (since a formal quotation is a separate downstream step). Returned as structured JSON (`reply_en`, `reply_ar`).

7. **Internal alert (second Read → Code → Write trio)** — rather than building a separate persistence path for the bilingual reply and a separate one for the alert, I folded the reply directly into the alert record. The alert log (`alerts.json`) contains a human-readable summary of the new RFQ plus both draft replies, so whoever picks up the alert has everything needed to act on it immediately without cross-referencing the CRM separately.

8. **Persistence infrastructure** — discovered partway through that the original n8n container had zero Docker volumes attached, meaning workflows and data lived only in the container's ephemeral filesystem. Migrated from an ad-hoc `docker run` setup to a `docker-compose.yml` with two volumes: a named volume for n8n's internal database and a bind mount for the mock CRM/alerts JSON store.

## Decisions and Trade-offs

- **Webhook trigger instead of email/IMAP trigger.** Avoids OAuth complexity unrelated to demonstrating integration skill; remains reproducible by any evaluator via a simple POST request.
- **JSON files as the mock CRM and alert log, rather than SQLite or a real CRM API.** The brief explicitly allows "a robust mock equivalent." Both files are timestamped, append-only, and human-inspectable.
- **Scoped the LLM calls deliberately.** One call extracts intent only from unstructured text (not from fields that are already clean JSON); a second call drafts the bilingual reply only once the full record is assembled. Avoids redundant or unnecessary AI calls.
- **Folded the bilingual reply into the alert record rather than building a third independent storage path.** Given the time constraints of the assessment, combining the two related outputs (alert + reply) into one record was both faster to implement and arguably a better real-world design — the person actioning the alert has the drafted reply right there rather than needing to look it up separately.
- **Attachment handling — explicitly scoped down.** Attachments currently flow through the pipeline as filenames only (`["site_plan.pdf", "spec_sheet.pdf"]`), carried as metadata inside the CRM record. **Actual file archiving — receiving real file bytes and storing them to a structured path — was not implemented**, given the time available for this assessment. With more time, the next step would be: accept multipart file uploads (or base64-encoded file data) in the webhook payload, write each file to `/data/archive/{crm_record_id}/{filename}`, and store the resulting path(s) back into the CRM record so the original documents remain retrievable against that RFQ.

## Validation

- Verified the webhook trigger independently using a manual POST request via PowerShell's `Invoke-RestMethod`, since browser-based testing only sends GET requests.
- Verified the AI extraction node's output directly in n8n's execution panel — confirmed valid JSON with correct, contextually appropriate field values.
- Verified the merged record contained all expected fields, with `extracted_intent` present as a properly nested object.
- Verified Docker volume persistence using `docker inspect n8n --format '{{ .Mounts }}'`, confirming both the named volume and bind mount were active with read-write access.
- Debugged and resolved a silent pipeline break where the Read node, on its first run (file not yet existing), produced zero output items and halted the chain downstream — fixed by enabling "Always Output Data" on the Read node so a missing file fails gracefully into an empty array rather than stalling execution.
- Debugged two node-reference errors where Code nodes referenced node names (`'Read Alerts File'`, `'Edit Fields1'`) that didn't match the actual canvas after nodes were renamed/duplicated — resolved by cross-checking each reference against the real node names shown on the canvas, rather than assuming names from an earlier draft still applied.
- End-to-end validation across three full test runs: confirmed all nodes executed successfully each time, confirmed the webhook returned the actual processed record, confirmed both `mock_crm.json` and `alerts.json` received correctly structured records each run, and confirmed the bilingual reply text was coherent, professional, and contextually accurate in both English and Arabic.

## Final Results

A complete sample run produces a CRM record and a corresponding alert record:

**CRM record (`data/mock_crm.json`):**
```
crm_record_id: 1782220767270-ahmed
company_name: Gulf Construction LLC
contact_name: Ahmed Al-Mutairi
product_interest: LED High Bay Lights, 150W
quantity: 200
extracted_intent: { urgency: "standard", key_requirements: [...], summary: "..." }
```

**Alert record (`data/alerts.json`):**
```json
{
  "alert_id": "alert-1782220771366",
  "triggered_at": "2026-06-23T13:19:31.366Z",
  "type": "new_rfq_received",
  "message": "New RFQ from Gulf Construction LLC (Ahmed Al-Mutairi) — 200 units of LED High Bay Lights, 150W",
  "crm_record_id": "1782220767270-ahmed",
  "draft_reply_en": "Thank you for contacting AL ROUF LED Lighting Technology Co. ...",
  "draft_reply_ar": "شكرًا لتواصلكم مع شركة AL ROUF لتقنية إضاءة LED. ..."
}
```

## Task 1 Requirement Checklist

| Requirement | Status |
|---|---|
| Extract structured fields from RFQ | ✅ Complete |
| Create CRM record (mock) | ✅ Complete |
| Archive attachments | ⚠️ Partial — filenames captured as metadata; actual file storage not implemented (see Decisions and Trade-offs) |
| Generate bilingual client reply draft | ✅ Complete |
| Trigger internal alert | ✅ Complete |

## AI Assistance Disclosure

I used an AI assistant (Claude) throughout this task as a technical mentor and pair-programming partner — for reasoning through architecture decisions (webhook vs. email trigger, JSON-file vs. SQLite, where to scope each LLM call, folding the reply into the alert record), generating starter code for the n8n Code nodes, and debugging runtime errors (the `fs` module sandboxing issue, the "Always Output Data" misconfiguration, and node-reference mismatches after renaming nodes).

What remained my own work: all hands-on execution in n8n (building nodes, wiring connections, configuring settings, running tests), all Docker/terminal command execution and verification, diagnosing actual on-screen errors and reporting them back accurately, renaming nodes for clarity, and the judgment calls on which AI suggestions to accept, modify, or reject based on what I observed actually happening in my environment.
