"""
Core quotation calculation logic — separated from the API layer
so it can be unit tested independently of FastAPI/HTTP concerns.
"""

import uuid
import json
import logging
from datetime import datetime, timezone

from app.catalog import CATALOG, get_discount_pct
from app.schemas import QuoteRequest

logger = logging.getLogger("quotation_service")


class UnknownSKUError(Exception):
    """Raised when a requested SKU does not exist in the catalog."""

    def __init__(self, sku: str):
        self.sku = sku
        super().__init__(f"Unknown SKU: {sku}")


def calculate_quote(request: QuoteRequest) -> dict:
    """
    Calculate a full quotation from a validated request.

    Raises:
        UnknownSKUError: if any requested SKU is not in the catalog.
    """
    line_items = []
    subtotal = 0.0
    total_quantity = 0

    for item in request.line_items:
        product = CATALOG.get(item.sku)
        if product is None:
            logger.warning(f"Quote request rejected — unknown SKU: {item.sku}")
            raise UnknownSKUError(item.sku)

        line_total = round(product["unit_price_sar"] * item.quantity, 2)
        line_items.append(
            {
                "sku": item.sku,
                "product_name": product["name"],
                "quantity": item.quantity,
                "unit_price_sar": product["unit_price_sar"],
                "line_total_sar": line_total,
            }
        )
        subtotal += line_total
        total_quantity += item.quantity

    subtotal = round(subtotal, 2)
    discount_pct = get_discount_pct(total_quantity)
    discount_amount = round(subtotal * discount_pct, 2)
    total = round(subtotal - discount_amount, 2)

    quote_id = f"Q-{uuid.uuid4().hex[:10].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()

    quote = {
        "quote_id": quote_id,
        "customer_name": request.customer_name,
        "customer_email": request.customer_email,
        "created_at": created_at,
        "line_items": line_items,
        "subtotal_sar": subtotal,
        "discount_pct": discount_pct,
        "discount_amount_sar": discount_amount,
        "total_sar": total,
        "currency": "SAR",
    }

    logger.info(
        f"Quote {quote_id} generated for {request.customer_name} "
        f"— {total_quantity} units, total {total} SAR"
    )

    return quote


def quote_to_db_record(quote: dict) -> dict:
    """Convert a quote dict to the flat structure expected by the database layer."""
    return {
        "quote_id": quote["quote_id"],
        "customer_name": quote["customer_name"],
        "customer_email": quote["customer_email"],
        "created_at": quote["created_at"],
        "line_items_json": json.dumps(quote["line_items"]),
        "subtotal_sar": quote["subtotal_sar"],
        "discount_pct": quote["discount_pct"],
        "discount_amount_sar": quote["discount_amount_sar"],
        "total_sar": quote["total_sar"],
        "currency": quote["currency"],
    }


def db_record_to_quote(record: dict) -> dict:
    """Convert a flat database record back into the API response shape."""
    return {
        "quote_id": record["quote_id"],
        "customer_name": record["customer_name"],
        "customer_email": record["customer_email"],
        "created_at": record["created_at"],
        "line_items": json.loads(record["line_items_json"]),
        "subtotal_sar": record["subtotal_sar"],
        "discount_pct": record["discount_pct"],
        "discount_amount_sar": record["discount_amount_sar"],
        "total_sar": record["total_sar"],
        "currency": record["currency"],
    }
