# AL ROUF LED — Bilingual RAG Knowledge Service

Answers questions in English or Arabic over a small set of sample product and policy documents, with source citations and explicit refusal when a question falls outside the supported document scope.

## How It Works

1. **4 sample documents** (mix of English and Arabic) are loaded and chunked along section boundaries on startup
2. Each chunk is embedded using OpenAI's `text-embedding-3-small` model — this model handles both languages, so an Arabic question can retrieve relevant English content and vice versa
3. Embeddings are cached to disk (`/data/embeddings_cache.json`) so the service doesn't re-embed identical content on every restart
4. A question comes in → it's embedded → the top-k most similar chunks are retrieved via cosine similarity
5. If the best match is below a relevance threshold (or nothing is retrieved), the service **refuses explicitly** rather than letting the model guess
6. Otherwise, the retrieved chunks are passed to `gpt-5.4-nano`, which is instructed to answer **only** from the provided excerpts, cite which document(s) it used, and respond in the same language as the question

## Sample Documents

| File | Language | Topic |
|---|---|---|
| `doc1_product_spec_high_bay_en.md` | English | 150W LED High Bay Light specs |
| `doc2_warranty_policy_ar.md` | Arabic | Warranty policy |
| `doc3_shipping_terms_en.md` | English | Shipping and delivery terms |
| `doc4_product_spec_street_light_ar.md` | Arabic | 30W LED Street Light specs |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check, shows indexed chunk count |
| `GET` | `/documents` | List indexed source documents |
| `POST` | `/ask` | Ask a question, get a cited answer or explicit refusal |

Interactive API docs at `/docs` once running.

## Running Locally

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-proj-your-key-here
uvicorn app.main:app --reload --port 8001
```

## Running with Docker

```bash
cp .env.example .env
# edit .env and add your real OpenAI API key
docker-compose up --build
```

## Running Tests

```bash
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v
```

15 tests total — 12 run with no API key (document loading, chunking including Arabic text, vector index search logic, refusal logic for both languages). 3 integration tests require a real `OPENAI_API_KEY` and are automatically skipped if one isn't set, so the suite still runs cleanly offline.

## Example Requests

**English question, in-scope:**
```bash
curl -X POST http://localhost:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the warranty period for the 150W high bay light?"}'
```

**Arabic question, in-scope:**
```bash
curl -X POST http://localhost:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "ما هي مدة الضمان على إضاءة الشوارع؟"}'
```

**Out-of-scope question (should refuse):**
```bash
curl -X POST http://localhost:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the population of Japan?"}'
```

## Latency and Cost Notes

Every response includes `latency_seconds` and `estimated_cost_usd`:
- **Embedding cost**: negligible (`text-embedding-3-small` is priced per-token, sub-cent per query)
- **Generation cost**: estimated from `gpt-5.4-nano` published per-token pricing, calculated from actual token usage returned by the API
- **Typical latency**: ~1-2 seconds per query (embedding + retrieval + generation combined), with refused (out-of-scope) queries returning near-instantly since no generation call is made

This is informational rather than a strict cost-tracking system — sufficient for understanding the cost profile of the workflow at this scale.

## Architecture Notes — Decisions and Trade-offs

- **In-memory/file-cached vector index instead of a dedicated vector database** (Pinecone, Weaviate, etc.): with only 3-5 documents and ~24 chunks, a full vector DB is unnecessary infrastructure. A numpy-based cosine similarity search is simpler, fully offline-friendly, and trivially inspectable.
- **OpenAI embeddings over a local embedding model**: chosen for genuine multilingual quality — local models that handle Arabic well typically require more setup and tuning than this assessment's scope justifies, and consistency with the rest of the stack (also OpenAI-based) keeps the submission cohesive.
- **Explicit refusal via a similarity threshold, not just prompt instructions**: relying solely on "refuse if you don't know" in the prompt is unreliable — models can still confabulate plausible-sounding answers. Gating on retrieval similarity score is a more robust mechanism, since if nothing relevant was even retrieved, there's nothing for the model to truthfully ground an answer in.
- **Markdown documents with simple section-based chunking, not a general-purpose PDF/document loader**: the brief asks for a workflow over 3-5 sample documents, not a production document ingestion pipeline. Keeping this layer simple kept focus on the retrieval and refusal logic, which is the actual subject of the task.

## Security Hygiene Notes

- `OPENAI_API_KEY` is read from environment/`.env`, never hardcoded
- `.env` is gitignored; only `.env.example` is committed
- No user-supplied input is ever passed to file paths or shell commands — questions are only ever used as LLM input
