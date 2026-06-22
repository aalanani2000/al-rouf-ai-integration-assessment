# Task 1 — RFQ → CRM Automation: Execution Notes

## Approach

I used n8n, self-hosted via Docker, as the orchestration layer instead of Zapier or Make. The brief explicitly allows "an equivalent orchestration approach," and n8n let me keep the entire workflow definition version-controlled as exported JSON inside the repository — something a SaaS-only tool like Zapier can't offer, since the workflow logic lives entirely outside any repo you could share.

The workflow simulates an inbound RFQ via a webhook (rather than a live email/IMAP integration), parses it, runs the free-text portion through an AI extraction step, merges everything into a single structured record, and writes it to a mock CRM store on disk.

## Steps Taken

1. **Webhook trigger** — set up a POST endpoint at `/rfq-intake` that accepts a JSON payload representing an inbound RFQ (company details, product interest, quantity, deadline, attachments, and a free-text message body).

2. **AI field extraction (OpenAI node)** — rather than running an LLM over the entire payload, I scoped the AI call specifically to the `message_body` field, since the rest of the payload already arrives as clean structured JSON. The model (GPT-5.4-nano) extracts urgency level, key requirements (e.g. "bulk pricing requested," "delivery timeline requested"), and a one-sentence summary, returned as strict JSON.

3. **Field merge (Edit Fields nodes)** — combined the structured webhook fields with the parsed AI output into one unified record, also generating a CRM record ID and timestamp at this stage.

4. **Mock CRM write (Read → Code → Write pattern)** — implemented persistence to a JSON file acting as the mock CRM. Initial attempt used a single Code node with Node's `fs` module directly, but n8n's Code node runs in a sandboxed VM2 environment that explicitly blocks built-in modules like `fs` — this surfaced as a "Cannot find module 'fs'" runtime error. I pivoted to n8n's native Read/Write Files from Disk nodes for actual filesystem I/O, with a Code node handling only in-memory JSON merge logic (reading existing records via binary buffer, appending the new record, re-encoding for write).

5. **Persistence infrastructure** — discovered partway through that the original n8n container had zero Docker volumes attached, meaning workflows and data lived only in the container's ephemeral filesystem. Migrated from an ad-hoc `docker run` setup to a `docker-compose.yml` with two volumes: a named volume for n8n's internal database (workflows, credentials, executions) and a bind mount for the mock CRM JSON store, so both survive container restarts and are inspectable directly from the host filesystem.

## Decisions and Trade-offs

- **Webhook trigger instead of email/IMAP trigger.** A real email integration adds OAuth complexity and flakiness unrelated to demonstrating integration skill, and it isn't reproducible by anyone reviewing the repo without sharing real credentials. A webhook lets any evaluator test the pipeline themselves with a simple POST request.
- **JSON file as the mock CRM rather than SQLite or a real CRM API.** The brief explicitly allows "a robust mock equivalent." Given the data shape is flat with one nested object, a JSON file is simpler to inspect and verify than a database, while still being structured and timestamped rather than a flat dump.
- **Scoped the LLM call to only the free-text field.** Running an LLM over already-structured JSON fields would add cost and latency for zero benefit. Applying it only where unstructured text needs interpretation is the more defensible engineering choice, and is arguably the central judgment call this role is testing for.

## Validation

- Verified the webhook trigger independently using a manual POST request via PowerShell's `Invoke-RestMethod`, since browser-based testing only sends GET requests and would not exercise the actual intake path.
- Verified the AI extraction node's output directly in n8n's execution panel — confirmed it returned valid JSON with no markdown fences and contextually correct field values (e.g., correctly identifying "bulk pricing" and "delivery timeline" as key requirements from the sample RFQ text).
- Verified the merged record contained all ten expected fields, with `extracted_intent` present as a properly nested object (not an escaped string) by inspecting the node's JSON output view.
- Verified Docker volume persistence using `docker inspect n8n --format '{{ .Mounts }}'`, confirming both the named volume and bind mount were active with read-write access, and cross-checked container ownership via `.Config.Labels` showing `com.docker.compose.project`.
- End-to-end validation: sent a full sample RFQ payload via PowerShell, confirmed all 7 nodes executed successfully (green checkmarks across the full chain), confirmed the webhook returned the actual processed record (not an error or raw passthrough), and confirmed the record was physically written to `data/mock_crm.json` on the host filesystem.

## Final Results (so far)

The pipeline reliably processes an inbound RFQ end to end: webhook receipt → AI-based intent extraction → field consolidation → persisted mock CRM record. A sample execution produced the following record:

```
crm_record_id: 1782164206123-ahmed
created_at: 2026-06-23T00:36:46.123+03:00
status: new
company_name: Gulf Construction LLC
...
extracted_intent: {
  "urgency": "standard",
  "key_requirements": ["include delivery timeline", "bulk pricing for 200 units"],
  "summary": "Requesting a quotation for 200 units of 150W LED high bay lights for a warehouse project in Jeddah, with delivery timeline and bulk pricing included."
}
```

## Remaining Work for Task 1

- Bilingual (English/Arabic) client reply draft generation — not yet built
- Internal alert trigger — not yet built
- Attachment archiving beyond filename passthrough — attachments currently flow through as metadata only; no actual file storage/archive step exists yet

## AI Assistance Disclosure

I used an AI assistant (Claude) throughout this task as a technical mentor and pair-programming partner — for reasoning through architecture decisions (webhook vs. email trigger, JSON-file vs. SQLite for the mock CRM, where to scope the LLM call), generating starter code for the n8n Code nodes, and debugging runtime errors (the `fs` module sandboxing issue, the "Always Output Data" misconfiguration that silently broke the chain after the Read node).

What remained my own work: all hands-on execution in n8n itself (building nodes, wiring connections, configuring settings, running tests), all Docker/terminal command execution and verification, diagnosing actual on-screen errors and reporting them back accurately, and the judgment calls on which AI suggestions to accept, modify, or reject based on what I observed actually happening in my environment.
