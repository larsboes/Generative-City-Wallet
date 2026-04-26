from __future__ import annotations

import sqlite3
from typing import Any

from spark.services.canonicalization import canonicalize_venue_transaction


def insert_venue_transactions(
    conn: sqlite3.Connection, transactions: list[dict[str, Any]]
) -> int:
    if not transactions:
        return 0
    normalized_transactions = []
    for txn in transactions:
        result = canonicalize_venue_transaction(txn)
        if result.value is None:
            continue
        normalized_transactions.append(result.value)

    before = conn.total_changes
    conn.executemany(
        """
        INSERT OR IGNORE INTO venue_transactions (
            transaction_id, merchant_id, category, timestamp, hour_of_day,
            day_of_week, hour_of_week, amount_eur, currency, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                txn.transaction_id,
                txn.merchant_id,
                txn.category,
                txn.timestamp,
                txn.hour_of_day,
                txn.day_of_week,
                txn.hour_of_week,
                txn.amount_eur,
                txn.currency,
                txn.source,
            )
            for txn in normalized_transactions
        ],
    )
    return conn.total_changes - before
