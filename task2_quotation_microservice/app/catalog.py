"""
Mock product catalog for AL ROUF LED Lighting quotation service.
Offline-friendly — no external pricing API dependency.
"""

CATALOG = {
    "LED-HB-150W": {
        "name": "LED High Bay Light, 150W",
        "unit_price_sar": 185.00,
        "uom": "unit",
    },
    "LED-HB-200W": {
        "name": "LED High Bay Light, 200W",
        "unit_price_sar": 240.00,
        "uom": "unit",
    },
    "LED-FL-100W": {
        "name": "LED Flood Light, 100W",
        "unit_price_sar": 145.00,
        "uom": "unit",
    },
    "LED-ST-30W": {
        "name": "LED Street Light, 30W",
        "unit_price_sar": 210.00,
        "uom": "unit",
    },
    "LED-PN-60W": {
        "name": "LED Panel Light, 60W",
        "unit_price_sar": 95.00,
        "uom": "unit",
    },
}

# Bulk discount tiers — applied based on total quantity ordered
DISCOUNT_TIERS = [
    {"min_quantity": 500, "discount_pct": 0.15},
    {"min_quantity": 200, "discount_pct": 0.10},
    {"min_quantity": 50, "discount_pct": 0.05},
    {"min_quantity": 0, "discount_pct": 0.0},
]


def get_discount_pct(quantity: int) -> float:
    """Return the applicable discount percentage for a given quantity."""
    for tier in DISCOUNT_TIERS:
        if quantity >= tier["min_quantity"]:
            return tier["discount_pct"]
    return 0.0
