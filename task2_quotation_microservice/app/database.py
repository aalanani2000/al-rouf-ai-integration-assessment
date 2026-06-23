"""
SQLite persistence layer for quotations.
Uses Python's built-in sqlite3 module — no external DB dependency required,
keeping the service fully offline-friendly per the assessment brief.
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.getenv("QUOTES_DB_PATH", "/data/quotes.db")


def init_db(db_path: str = None) -> None:
    """Create the quotes table if it doesn't already exist."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                quote_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                line_items_json TEXT NOT NULL,
                subtotal_sar REAL NOT NULL,
                discount_pct REAL NOT NULL,
                discount_amount_sar REAL NOT NULL,
                total_sar REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'SAR'
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection(db_path: str = None):
    """Context-managed SQLite connection."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_quote(quote: dict, db_path: str = None) -> None:
    """Persist a quote record to the database."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO quotes (
                quote_id, customer_name, customer_email, created_at,
                line_items_json, subtotal_sar, discount_pct,
                discount_amount_sar, total_sar, currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quote["quote_id"],
                quote["customer_name"],
                quote["customer_email"],
                quote["created_at"],
                quote["line_items_json"],
                quote["subtotal_sar"],
                quote["discount_pct"],
                quote["discount_amount_sar"],
                quote["total_sar"],
                quote["currency"],
            ),
        )
        conn.commit()


def get_quote(quote_id: str, db_path: str = None) -> Optional[dict]:
    """Retrieve a single quote by ID. Returns None if not found."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)
        ).fetchone()
        return dict(row) if row else None
