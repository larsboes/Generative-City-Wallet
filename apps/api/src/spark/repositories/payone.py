from __future__ import annotations

from spark.db.connection import get_connection


def insert_payone_transaction(
    *,
    merchant_id: str,
    merchant_type: str,
    timestamp: str,
    hour_of_day: int,
    day_of_week: int,
    hour_of_week: int,
    txn_count: int,
    total_volume_eur: float,
    db_path: str | None = None,
) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO payone_transactions (
                merchant_id, merchant_type, timestamp, hour_of_day, day_of_week,
                hour_of_week, txn_count, total_volume_eur
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                merchant_id,
                merchant_type,
                timestamp,
                hour_of_day,
                day_of_week,
                hour_of_week,
                txn_count,
                total_volume_eur,
            ),
        )
        conn.commit()
    finally:
        conn.close()
