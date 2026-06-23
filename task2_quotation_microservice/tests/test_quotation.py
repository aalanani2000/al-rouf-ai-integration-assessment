"""
Test suite for the quotation microservice.

Uses a fresh temporary SQLite database per test session to avoid
state leaking between tests, and FastAPI's TestClient for HTTP-level
testing without needing a running server.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Point the app at a temporary DB file before importing the app,
# so init_db() creates the schema in an isolated location for tests.
TEST_DB_FD, TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["QUOTES_DB_PATH"] = TEST_DB_PATH

from app.main import app  # noqa: E402
from app import database  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    """Initialize the test database schema once for the whole test session."""
    database.init_db(TEST_DB_PATH)
    yield
    os.close(TEST_DB_FD)
    os.remove(TEST_DB_PATH)


# ── Health check ──────────────────────────────────────────────────────────

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── Catalog ───────────────────────────────────────────────────────────────

def test_catalog_lists_products():
    response = client.get("/catalog")
    assert response.status_code == 200
    body = response.json()
    assert "LED-HB-150W" in body
    assert body["LED-HB-150W"]["unit_price_sar"] == 185.00


# ── Quote creation — happy paths ─────────────────────────────────────────

def test_create_quote_single_item_no_discount():
    """Small quantity should receive no bulk discount."""
    response = client.post(
        "/quote",
        json={
            "customer_name": "Test Customer",
            "customer_email": "test@example.com",
            "line_items": [{"sku": "LED-HB-150W", "quantity": 10}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["discount_pct"] == 0.0
    assert body["subtotal_sar"] == 1850.00
    assert body["total_sar"] == 1850.00
    assert body["quote_id"].startswith("Q-")


def test_create_quote_applies_bulk_discount_tier_1():
    """Quantity >= 50 should trigger the 5% discount tier."""
    response = client.post(
        "/quote",
        json={
            "customer_name": "Bulk Buyer LLC",
            "customer_email": "bulk@example.com",
            "line_items": [{"sku": "LED-HB-150W", "quantity": 50}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["discount_pct"] == 0.05
    assert body["subtotal_sar"] == 9250.00
    assert body["discount_amount_sar"] == 462.50
    assert body["total_sar"] == 8787.50


def test_create_quote_applies_bulk_discount_tier_2():
    """Quantity >= 200 should trigger the 10% discount tier."""
    response = client.post(
        "/quote",
        json={
            "customer_name": "Gulf Construction LLC",
            "customer_email": "ahmed@gulfconstruction.sa",
            "line_items": [{"sku": "LED-HB-150W", "quantity": 200}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["discount_pct"] == 0.10


def test_create_quote_multi_line_items():
    """Quote with multiple distinct products should sum correctly."""
    response = client.post(
        "/quote",
        json={
            "customer_name": "Multi Item Co",
            "customer_email": "multi@example.com",
            "line_items": [
                {"sku": "LED-HB-150W", "quantity": 20},
                {"sku": "LED-FL-100W", "quantity": 30},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["line_items"]) == 2
    expected_subtotal = round((185.00 * 20) + (145.00 * 30), 2)
    assert body["subtotal_sar"] == expected_subtotal


# ── Quote creation — error paths ─────────────────────────────────────────

def test_create_quote_unknown_sku_returns_400():
    response = client.post(
        "/quote",
        json={
            "customer_name": "Bad SKU Co",
            "customer_email": "bad@example.com",
            "line_items": [{"sku": "NOT-A-REAL-SKU", "quantity": 5}],
        },
    )
    assert response.status_code == 400
    assert "NOT-A-REAL-SKU" in response.json()["detail"]


def test_create_quote_zero_quantity_rejected():
    """Pydantic validation should reject quantity <= 0 before it reaches business logic."""
    response = client.post(
        "/quote",
        json={
            "customer_name": "Zero Co",
            "customer_email": "zero@example.com",
            "line_items": [{"sku": "LED-HB-150W", "quantity": 0}],
        },
    )
    assert response.status_code == 422  # FastAPI validation error


def test_create_quote_invalid_email_rejected():
    response = client.post(
        "/quote",
        json={
            "customer_name": "Bad Email Co",
            "customer_email": "not-an-email",
            "line_items": [{"sku": "LED-HB-150W", "quantity": 5}],
        },
    )
    assert response.status_code == 422


def test_create_quote_empty_line_items_rejected():
    response = client.post(
        "/quote",
        json={
            "customer_name": "Empty Co",
            "customer_email": "empty@example.com",
            "line_items": [],
        },
    )
    assert response.status_code == 422


# ── Quote retrieval ───────────────────────────────────────────────────────

def test_retrieve_existing_quote():
    create_response = client.post(
        "/quote",
        json={
            "customer_name": "Retrieve Me Co",
            "customer_email": "retrieve@example.com",
            "line_items": [{"sku": "LED-PN-60W", "quantity": 5}],
        },
    )
    quote_id = create_response.json()["quote_id"]

    get_response = client.get(f"/quote/{quote_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["quote_id"] == quote_id
    assert body["customer_name"] == "Retrieve Me Co"


def test_retrieve_nonexistent_quote_returns_404():
    response = client.get("/quote/Q-DOESNOTEXIST")
    assert response.status_code == 404
