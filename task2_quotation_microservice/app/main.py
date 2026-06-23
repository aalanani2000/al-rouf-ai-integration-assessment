"""
AL ROUF LED Lighting — Quotation Microservice

A FastAPI service that generates and retrieves product quotations
with bulk pricing tiers. Built to be fully offline-friendly: the
product catalog and pricing logic are mocked in-code, with no
external pricing API or ERP dependency required to run or test.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import QuoteRequest, QuoteResponse, ErrorResponse
from app.quoting import calculate_quote, quote_to_db_record, db_record_to_quote, UnknownSKUError
from app.database import init_db, save_quote, get_quote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quotation_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database schema on service startup."""
    init_db()
    logger.info("Quotation service started, database initialized.")
    yield
    logger.info("Quotation service shutting down.")


app = FastAPI(
    title="AL ROUF LED Quotation Service",
    description=(
        "Generates product quotations with bulk pricing tiers for "
        "AL ROUF LED Lighting Technology Co. Offline-friendly mock "
        "pricing engine — no external ERP dependency required."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["System"])
def health_check():
    """Basic health check endpoint for monitoring/orchestration."""
    return {"status": "ok"}


@app.post(
    "/quote",
    response_model=QuoteResponse,
    responses={400: {"model": ErrorResponse}},
    tags=["Quotes"],
)
def create_quote(request: QuoteRequest):
    """
    Generate a new quotation for one or more product line items.

    Applies bulk discount tiers based on total quantity across all
    line items, and persists the resulting quote for later retrieval.
    """
    try:
        quote = calculate_quote(request)
    except UnknownSKUError as e:
        logger.warning(f"Rejected quote request — unknown SKU: {e.sku}")
        raise HTTPException(
            status_code=400,
            detail=f"Unknown product SKU: '{e.sku}'. Check /catalog for valid SKUs.",
        )

    save_quote(quote_to_db_record(quote))
    return quote


@app.get(
    "/quote/{quote_id}",
    response_model=QuoteResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Quotes"],
)
def retrieve_quote(quote_id: str):
    """Retrieve a previously generated quotation by its ID."""
    record = get_quote(quote_id)
    if record is None:
        logger.info(f"Quote lookup miss: {quote_id}")
        raise HTTPException(status_code=404, detail=f"Quote '{quote_id}' not found.")

    return db_record_to_quote(record)


@app.get("/catalog", tags=["System"])
def list_catalog():
    """List all available product SKUs and their base pricing."""
    from app.catalog import CATALOG

    return CATALOG


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """Catch-all handler so unexpected errors don't leak stack traces to clients."""
    logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
    )
