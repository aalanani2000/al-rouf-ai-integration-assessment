"""
Pydantic models for request/response validation and OpenAPI documentation.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List


class LineItemRequest(BaseModel):
    """A single product line in a quote request."""

    sku: str = Field(..., description="Product SKU, e.g. 'LED-HB-150W'", examples=["LED-HB-150W"])
    quantity: int = Field(..., gt=0, description="Quantity ordered, must be greater than zero", examples=[200])


class QuoteRequest(BaseModel):
    """Incoming request to generate a new quotation."""

    customer_name: str = Field(..., min_length=1, examples=["Gulf Construction LLC"])
    customer_email: EmailStr = Field(..., examples=["ahmed@gulfconstruction.sa"])
    line_items: List[LineItemRequest] = Field(..., min_length=1)


class LineItemResponse(BaseModel):
    """A priced line item within a quote response."""

    sku: str
    product_name: str
    quantity: int
    unit_price_sar: float
    line_total_sar: float


class QuoteResponse(BaseModel):
    """Full quotation response returned to the client."""

    quote_id: str
    customer_name: str
    customer_email: str
    created_at: str
    line_items: List[LineItemResponse]
    subtotal_sar: float
    discount_pct: float
    discount_amount_sar: float
    total_sar: float
    currency: str = "SAR"


class ErrorResponse(BaseModel):
    """Standard error response shape."""

    error: str
    detail: str
