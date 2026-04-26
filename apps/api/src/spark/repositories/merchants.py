from __future__ import annotations

from typing import Any

from spark.db.connection import get_connection


def get_merchant_by_id(
    merchant_id: str, db_path: str | None = None
) -> dict[str, Any] | None:
    """Return merchant record by ID, or None if missing."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, name, type, lat, lon, address, grid_cell FROM merchants WHERE id = ?",
            (merchant_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_active_coupon_for_merchant(
    merchant_id: str, db_path: str | None = None
) -> dict[str, Any] | None:
    """Return active coupon row for merchant, or None."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT coupon_type, config FROM merchant_coupons WHERE merchant_id = ? AND active = 1 LIMIT 1",
            (merchant_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_merchant_ids_by_grid_cell(
    grid_cell: str, db_path: str | None = None
) -> list[str]:
    """Return merchant IDs for a grid cell."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id FROM merchants WHERE grid_cell = ?",
            (grid_cell,),
        ).fetchall()
        return [row["id"] for row in rows]
    finally:
        conn.close()


def get_first_merchant_id(db_path: str | None = None) -> str | None:
    """Return first available merchant ID, or None if empty table."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT id FROM merchants LIMIT 1").fetchone()
        return row["id"] if row else None
    finally:
        conn.close()
