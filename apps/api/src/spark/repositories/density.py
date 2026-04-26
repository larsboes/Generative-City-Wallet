from __future__ import annotations

from typing import Any

from spark.db.connection import get_connection
from spark.domain.interfaces import IDensityRepository


def get_hourly_transaction_stats(
    merchant_id: str, hour_of_week: int, db_path: str | None = None
) -> tuple[float, int]:
    """Return (historical_avg, sample_count) for merchant/hour bucket."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT AVG(txn_count), COUNT(*) FROM payone_transactions WHERE merchant_id = ? AND hour_of_week = ?",
            (merchant_id, hour_of_week),
        ).fetchone()
        avg_txn = float(row[0]) if row and row[0] else 0.0
        sample_count = int(row[1]) if row else 0
        return avg_txn, sample_count
    finally:
        conn.close()


def get_latest_transaction_rate(
    merchant_id: str, hour_of_week: int, db_path: str | None = None
) -> float:
    """Return most recent txn_count for merchant/hour bucket, or 0.0."""
    conn = get_connection(db_path)
    try:
        recent = conn.execute(
            "SELECT txn_count FROM payone_transactions WHERE merchant_id = ? AND hour_of_week = ? ORDER BY timestamp DESC LIMIT 1",
            (merchant_id, hour_of_week),
        ).fetchone()
        return float(recent[0]) if recent else 0.0
    finally:
        conn.close()


def get_historical_avg_at_arrival_hour(
    merchant_id: str, arrival_hour_of_week: int, db_path: str | None = None
) -> float | None:
    """Return average txn_count at arrival hour bucket."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT AVG(txn_count) FROM payone_transactions WHERE merchant_id = ? AND hour_of_week = ?",
            (merchant_id, arrival_hour_of_week),
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None
    finally:
        conn.close()


def list_merchants_for_density(db_path: str | None = None) -> list[dict[str, Any]]:
    """Return merchant rows needed for density listing endpoint."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, name, type, lat, lon, address, grid_cell FROM merchants"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


class DensityRepository(IDensityRepository):
    """Concrete IDensityRepository backed by SQLite, wrapping existing functions."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path

    def get_hourly_transaction_stats(
        self, merchant_id: str, hour_of_week: int
    ) -> tuple[float, int]:
        return get_hourly_transaction_stats(merchant_id, hour_of_week, self.db_path)

    def get_latest_transaction_rate(
        self, merchant_id: str, hour_of_week: int
    ) -> float:
        return get_latest_transaction_rate(merchant_id, hour_of_week, self.db_path)

    def get_historical_avg_at_arrival_hour(
        self, merchant_id: str, arrival_hour_of_week: int
    ) -> float | None:
        return get_historical_avg_at_arrival_hour(
            merchant_id, arrival_hour_of_week, self.db_path
        )

    def list_merchants_for_density(self) -> list[dict[str, Any]]:
        return list_merchants_for_density(self.db_path)
