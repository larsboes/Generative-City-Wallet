from __future__ import annotations

import sqlite3


def get_historical_transaction_counts_by_day(
    conn: sqlite3.Connection, merchant_id: str, hour_of_week: int, before_iso: str
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS transaction_count
        FROM venue_transactions
        WHERE merchant_id = ?
          AND hour_of_week = ?
          AND timestamp < ?
        GROUP BY substr(timestamp, 1, 10)
        """,
        (merchant_id, hour_of_week, before_iso),
    ).fetchall()


def get_current_transaction_count(
    conn: sqlite3.Connection, merchant_id: str, start_iso: str, end_iso: str
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS transaction_count
        FROM venue_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        """,
        (merchant_id, start_iso, end_iso),
    ).fetchone()
    return int(row["transaction_count"] or 0) if row else 0
