from __future__ import annotations

import hashlib
from typing import Any

from spark.db.connection import get_connection


def get_offer_audit_row(offer_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM offer_audit_log WHERE offer_id = ?",
            (offer_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def mark_offer_redeemed(
    offer_id: str, redeemed_at_iso: str, db_path: str | None = None
) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE offer_audit_log SET status = 'REDEEMED', redeemed_at = ? WHERE offer_id = ?",
            (redeemed_at_iso, offer_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_offer_outcome(
    offer_id: str,
    status: str,
    occurred_at_iso: str,
    db_path: str | None = None,
) -> bool:
    """Persist a non-redemption offer lifecycle outcome in SQLite."""
    status = status.upper()
    timestamp_column = {
        "ACCEPTED": "accepted_at",
        "DECLINED": "declined_at",
        "EXPIRED": "expired_at",
    }.get(status)
    if timestamp_column is None:
        raise ValueError(f"Unsupported offer outcome status: {status}")

    conn = get_connection(db_path)
    try:
        result = conn.execute(
            f"UPDATE offer_audit_log SET status = ?, {timestamp_column} = ? WHERE offer_id = ?",
            (status, occurred_at_iso, offer_id),
        )
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()


def credit_wallet_transaction(
    session_id: str,
    offer_id: str,
    amount_eur: float,
    merchant_name: str,
    credited_at_iso: str,
    db_path: str | None = None,
) -> float:
    """Insert wallet credit and return current wallet balance."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO wallet_transactions (session_id, offer_id, amount_eur, merchant_name, credited_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, offer_id, amount_eur, merchant_name, credited_at_iso),
        )
        balance_row = conn.execute(
            "SELECT COALESCE(SUM(amount_eur), 0) as total FROM wallet_transactions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        conn.commit()
        return float(balance_row["total"]) if balance_row else 0.0
    finally:
        conn.close()


def get_wallet_snapshot(
    session_id: str, db_path: str | None = None, limit: int = 20
) -> tuple[float, list[dict[str, Any]]]:
    conn = get_connection(db_path)
    try:
        balance_row = conn.execute(
            "SELECT COALESCE(SUM(amount_eur), 0) as total FROM wallet_transactions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        transactions = conn.execute(
            "SELECT offer_id, amount_eur, merchant_name, credited_at FROM wallet_transactions WHERE session_id = ? ORDER BY credited_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        balance = float(balance_row["total"]) if balance_row else 0.0
        return balance, [dict(t) for t in transactions]
    finally:
        conn.close()


def lookup_merchant_category_for_offer(
    offer_id: str, db_path: str | None = None
) -> str | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT m.type AS category
            FROM offer_audit_log o
            JOIN merchants m ON m.id = o.merchant_id
            WHERE o.offer_id = ?
            """,
            (offer_id,),
        ).fetchone()
        return row["category"] if row else None
    finally:
        conn.close()


def acquire_graph_event_idempotency_key(
    *,
    event_type: str,
    session_id: str | None,
    offer_id: str | None,
    source: str = "kg_projection",
    db_path: str | None = None,
) -> bool:
    token = f"{event_type}:{session_id or '-'}:{offer_id or '-'}"
    key = hashlib.sha256(token.encode()).hexdigest()
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_event_log (
                idempotency_key TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                session_id TEXT,
                offer_id TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        result = conn.execute(
            """
            INSERT OR IGNORE INTO graph_event_log (
                idempotency_key, event_type, session_id, offer_id, source
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (key, event_type, session_id, offer_id, source),
        )
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()


def cleanup_graph_event_log(
    retention_days: int, db_path: str | None = None
) -> None:
    cutoff = f"-{retention_days} days"
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            DELETE FROM graph_event_log
            WHERE datetime(created_at) < datetime('now', ?)
            """,
            (cutoff,),
        )
        conn.commit()
    finally:
        conn.close()
