# AL ROUF LED — Quotation Microservice

A FastAPI service that generates and retrieves product quotations with automatic bulk pricing tiers. Fully offline-friendly — the product catalog and pricing logic are mocked in-code, with no external ERP or pricing API required to run or test.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/catalog` | List available products and base pricing |
| `POST` | `/quote` | Generate a new quotation |
| `GET` | `/quote/{quote_id}` | Retrieve a previously generated quotation |

Full interactive API docs (OpenAPI/Swagger) are available at `/docs` once the service is running.

## Pricing Logic

- Each product SKU has a fixed base unit price (see `app/catalog.py`)
- Bulk discount tiers apply based on **total quantity across all line items** in a single quote:

| Total Quantity | Discount |
|---|---|
| 0–49 | 0% |
| 50–199 | 5% |
| 200–499 | 10% |
| 500+ | 15% |

## Running Locally (without Docker)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Service runs at `http://localhost:8000`. Visit `http://localhost:8000/docs` for interactive API documentation.

## Running with Docker

```bash
docker-compose up --build
```

This builds the image, starts the service on port 8000, and mounts a local `./data` folder for SQLite persistence — quotes survive container restarts.

## Running Tests

```bash
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v
```

12 tests covering: health check, catalog listing, quote creation (single item, multi-item, all discount tiers), input validation (invalid email, zero quantity, empty line items, unknown SKU), and quote retrieval (found and not-found cases).

## Example Request

```bash
curl -X POST http://localhost:8000/quote \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Gulf Construction LLC",
    "customer_email": "ahmed@gulfconstruction.sa",
    "line_items": [
      {"sku": "LED-HB-150W", "quantity": 200}
    ]
  }'
```

**Response:**
```json
{
  "quote_id": "Q-A1B2C3D4E5",
  "customer_name": "Gulf Construction LLC",
  "customer_email": "ahmed@gulfconstruction.sa",
  "created_at": "2026-06-23T14:00:00+00:00",
  "line_items": [
    {
      "sku": "LED-HB-150W",
      "product_name": "LED High Bay Light, 150W",
      "quantity": 200,
      "unit_price_sar": 185.0,
      "line_total_sar": 37000.0
    }
  ],
  "subtotal_sar": 37000.0,
  "discount_pct": 0.10,
  "discount_amount_sar": 3700.0,
  "total_sar": 33300.0,
  "currency": "SAR"
}
```

## Architecture Notes

- **SQLite over a JSON file or in-memory store**: chosen specifically because the task requires automated tests, and SQLite supports clean test isolation (a fresh temporary database per test run) without risking test pollution or filesystem mocking complexity.
- **Business logic separated from the API layer** (`app/quoting.py` vs `app/main.py`): pricing calculations are pure functions that can be unit tested independently of FastAPI/HTTP concerns.
- **Structured logging**: every quote creation, validation rejection, and lookup miss is logged with relevant context, supporting observability in a real deployment.
- **Catch-all exception handler**: prevents internal stack traces from leaking to API clients in unexpected failure cases, while still logging the full exception server-side.

## Error Handling

- Unknown SKU → `400 Bad Request` with a clear message and a pointer to `/catalog`
- Invalid input (bad email, zero/negative quantity, empty line items) → `422 Unprocessable Entity` via Pydantic validation, before business logic ever runs
- Quote not found → `404 Not Found`
- Unhandled errors → `500 Internal Server Error` with no internal details leaked to the client

## Security Hygiene Notes

- No secrets or credentials in this service — it has no external dependencies requiring API keys
- Database path configurable via `QUOTES_DB_PATH` environment variable rather than hardcoded
- Input validation enforced at the schema layer (Pydantic) before any business logic executes, reducing injection/malformed-input risk
