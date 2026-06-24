# AL ROUF LED AI Integration Assessment

This repository contains the completed AI Integration Engineer assessment for AL ROUF LED Lighting Technology Co. It includes three runnable task implementations, supporting evidence, screenshots, and the two mandatory report deliverables requested in the assessment brief.

Repository URL: https://github.com/aalanani2000/al-rouf-ai-integration-assessment  
Default branch: `main`  
Latest documented commit: `653ec552871083dca14498d120d6e6c156ed4f31`

## Assessment Tasks

| Task | Location | Summary |
|---|---|---|
| Task 1: RFQ to CRM automation | `task1_rfq_crm_automation/` | n8n workflow that accepts an RFQ webhook, extracts intent with OpenAI, creates a mock CRM record, drafts a bilingual reply, and writes an internal alert. |
| Task 2: Quotation microservice | `task2_quotation_microservice/` | FastAPI service for product catalog lookup, quotation creation, quote retrieval, bulk-discount pricing, SQLite persistence, Docker packaging, and automated tests. |
| Task 3: Bilingual RAG workflow | `task3_bilingual_rag/` | FastAPI bilingual knowledge service over English and Arabic sample documents, with embeddings, source citations, explicit refusal for out-of-scope questions, latency, and cost notes. |

## Deliverables

| Deliverable | Path |
|---|---|
| Execution evidence report | `reports/01_execution_evidence_report/01_execution_evidence_report.pdf` |
| Editable evidence report source | `reports/01_execution_evidence_report/01_execution_evidence_report.docx` |
| Final result report | `reports/02_final_result_report/02_final_result_report.pdf` |
| Editable final result report source | `reports/02_final_result_report/02_final_result_report.docx` |
| Task 1 exported n8n workflow | `task1_rfq_crm_automation/n8n_workflows/rfq-crm-automation.json` |
| Screenshots and evidence | `docs/screenshots/` and `docs/evidence/` |

## Quick Start

### Task 1: RFQ to CRM Automation

```bash
docker-compose up -d
```

n8n runs at `http://localhost:5678`. Import `task1_rfq_crm_automation/n8n_workflows/rfq-crm-automation.json`, configure the OpenAI credential in n8n, then test the webhook with a POST request to the generated n8n webhook URL. Runtime data is persisted through Docker volumes and the local `data/` folder.

### Task 2: Quotation Microservice

```bash
cd task2_quotation_microservice
docker-compose up --build
```

The service runs at `http://localhost:8000`, with OpenAPI documentation at `http://localhost:8000/docs`.

Run tests:

```bash
cd task2_quotation_microservice
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v
```

### Task 3: Bilingual RAG Knowledge Service

```bash
cd task3_bilingual_rag
cp .env.example .env
# add OPENAI_API_KEY to .env
docker-compose up --build
```

The service runs at `http://localhost:8001`, with OpenAPI documentation at `http://localhost:8001/docs`.

Run tests:

```bash
cd task3_bilingual_rag
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v
```

Most tests run offline; integration tests requiring `OPENAI_API_KEY` are skipped automatically if the key is not set.

## Repository Structure

```text
C:.
|   .env
|   .env.example
|   .gitignore
|   docker-compose.yml
|   README.md
|
+---data
|       alerts.json
|       mock_crm.json
|
+---docs
|   +---architecture
|   +---evidence
|   |   \---task1_rfq_crm_automation
|   |           execution_notes.md
|   |
|   \---screenshots
|       +---Task 1
|       |       javascript code 1 error .png
|       |       n8n canva.png
|       |       open ai node.png
|       |       proof of the volumes being correctly attached.png
|       |       repository structure.png
|       |       set field output.png
|       |       set field.png
|       |       Webhook node.png
|       |       workflow progress .png
|       |       workflow progress 1 .png
|       |       workflow succes.png
|       |       workflow.png
|       |       workflow2.png
|       |
|       +---Task 2
|       |       Open API.png
|       |
|       \---Task 3
|               a problem when communicating with model.png
|               testing the RAG on arabic question.pdf
|
+---reports
|   +---01_execution_evidence_report
|   \---02_final_result_report
+---task1_rfq_crm_automation
|   \---n8n_workflows
|           rfq-crm-automation.json
|
+---task2_quotation_microservice
|   |   .gitignore
|   |   docker-compose.yml
|   |   Dockerfile
|   |   README.md
|   |   requirements.txt
|   |
|   +---app
|   |       catalog.py
|   |       database.py
|   |       main.py
|   |       quoting.py
|   |       schemas.py
|   |       __init__.py
|   |
|   +---data
|   |       quotes.db
|   |
|   \---tests
|           test_quotation.py
|           __init__.py
|
\---task3_bilingual_rag
    |   .env
    |   .env.example
    |   .gitignore
    |   docker-compose.yml
    |   Dockerfile
    |   README.md
    |   requirements.txt
    |
    +---app
    |       embeddings.py
    |       llm.py
    |       loader.py
    |       main.py
    |       schemas.py
    |       __init__.py
    |
    +---data
    |       embeddings_cache.json
    |
    +---documents
    |       doc1_product_spec_high_bay_en.md
    |       doc2_warranty_policy_ar.md
    |       doc3_shipping_terms_en.md
    |       doc4_product_spec_street_light_ar.md
    |
    \---tests
            test_rag.py
            __init__.py
```

## Architecture Summary

Task 1 uses n8n as the orchestration layer. The workflow starts from a webhook, uses an OpenAI model for RFQ intent extraction, merges structured and AI-derived fields, persists a CRM-style record in `data/mock_crm.json`, drafts English and Arabic client replies, and writes a sales alert to `data/alerts.json`.

Task 2 uses FastAPI with clean separation between API routes, schema validation, product catalog data, pricing logic, and SQLite persistence. The service remains offline-friendly because all product and pricing data is mocked locally.

Task 3 uses FastAPI with a lightweight retrieval pipeline: Markdown source documents are chunked, embedded, cached locally, searched with cosine similarity, and passed to an OpenAI chat model only when retrieval confidence is high enough. Out-of-scope questions are refused before generation.

## Error Handling, Maintainability, And Security

- Secrets are read from `.env` or runtime environment variables and are not hardcoded.
- `.env.example` files document required configuration without exposing private keys.
- FastAPI services use Pydantic validation to reject malformed input before business logic runs.
- Task 2 returns clear errors for unknown SKUs, invalid quote input, and missing quote IDs.
- Task 3 uses retrieval thresholding to reduce hallucination risk and refuses unsupported questions.
- Task 1 uses Docker volumes and file-based mock persistence so data survives container restarts.
- Core business logic is separated from HTTP handlers where practical, making it easier to test and maintain.

## Future Enhancements

Task 1 can be extended from webhook simulation to real inbound channels such as email, WhatsApp Business, or website forms. A production version should store real attachment files, deduplicate RFQs, enrich CRM records with customer history, and route urgent RFQs to sales channels such as Slack, Microsoft Teams, or email.

Task 2 can be improved with a small quotation UI, authentication, PDF quote generation, configurable product/pricing administration, tax and shipping calculations, and ERP/CRM integration.

Task 3 can be improved with a simple chat UI, document upload and re-indexing, role-based access, better Arabic typography in the frontend, richer citation snippets, streaming answers, and a production vector database if the document set grows.

## AI Assistance Disclosure

AI assistance was used as a technical mentor and documentation partner for architecture reasoning, debugging support, report drafting, and README polish. The hands-on implementation, configuration, testing, screenshot collection, Docker execution, n8n workflow building, and final judgment calls were completed by the candidate.
