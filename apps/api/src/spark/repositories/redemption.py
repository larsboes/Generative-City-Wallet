from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from spark.db.connection import get_connection


def _safe_add_column(conn, table: str, column_def: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
    except Exception:
        # Column already exists or table is unavailable in this context.
        return


def ensure_graph_learning_schema(db_path: str | None = None) -> None:
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
                category TEXT,
                source_event_id TEXT,
                payload_hash TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS preference_update_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                category TEXT NOT NULL,
                source_type TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_key TEXT NOT NULL,
                source_event_id TEXT,
                before_weight REAL,
                delta REAL NOT NULL,
                after_weight REAL,
                outcome TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_metrics_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_group TEXT,
                session_id TEXT,
                category TEXT,
                source_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _safe_add_column(conn, "graph_event_log", "category TEXT")
        _safe_add_column(conn, "graph_event_log", "source_event_id TEXT")
        _safe_add_column(conn, "graph_event_log", "payload_hash TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_event_log_created_at ON graph_event_log(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_event_log_session_event ON graph_event_log(session_id, event_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_event_log_category ON graph_event_log(category)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pref_update_log_session_category ON preference_update_log(session_id, category, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_learning_metrics_log_name ON learning_metrics_log(metric_name, created_at)"
        )
        conn.commit()
    finally:
        conn.close()


def _iso_from_unix(unix_seconds: float | None) -> str:
    if unix_seconds is None:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).isoformat()


def _hash_payload(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


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
    category: str | None = None,
    source_event_id: str | None = None,
    payload: dict[str, Any] | None = None,
    event_unix: float | None = None,
    db_path: str | None = None,
) -> bool:
    ensure_graph_learning_schema(db_path=db_path)
    payload_hash = _hash_payload(payload)
    event_bucket = _iso_from_unix(event_unix)
    event_bucket_component = str(event_unix) if event_unix is not None else "-"
    token = ":".join(
        [
            event_type,
            session_id or "-",
            offer_id or "-",
            category or "-",
            source_event_id or "-",
            payload_hash or "-",
            event_bucket_component,
        ]
    )
    key = hashlib.sha256(token.encode()).hexdigest()
    conn = get_connection(db_path)
    try:
        result = conn.execute(
            """
            INSERT OR IGNORE INTO graph_event_log (
                idempotency_key, event_type, session_id, offer_id, source, category,
                source_event_id, payload_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                event_type,
                session_id,
                offer_id,
                source,
                category,
                source_event_id,
                payload_hash,
                event_bucket,
            ),
        )
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()


def cleanup_graph_event_log(
    retention_days: int, db_path: str | None = None
) -> None:
    ensure_graph_learning_schema(db_path=db_path)
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


def count_graph_events_for_session(
    *,
    session_id: str,
    event_type_prefix: str,
    db_path: str | None = None,
) -> int:
    ensure_graph_learning_schema(db_path=db_path)
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM graph_event_log
            WHERE session_id = ?
              AND event_type LIKE ?
            """,
            (session_id, f"{event_type_prefix}%"),
        ).fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()


def count_recent_graph_events_for_category(
    *,
    session_id: str,
    category: str,
    window_seconds: int,
    event_type_prefix: str = "pref_update:",
    db_path: str | None = None,
) -> int:
    ensure_graph_learning_schema(db_path=db_path)
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM graph_event_log
            WHERE session_id = ?
              AND category = ?
              AND event_type LIKE ?
              AND datetime(created_at) >= datetime('now', ?)
            """,
            (session_id, category, f"{event_type_prefix}%", f"-{window_seconds} seconds"),
        ).fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()


def log_preference_update_event(
    *,
    session_id: str,
    category: str,
    source_type: str,
    event_type: str,
    event_key: str,
    source_event_id: str | None,
    before_weight: float | None,
    delta: float,
    after_weight: float | None,
    outcome: str,
    db_path: str | None = None,
) -> None:
    ensure_graph_learning_schema(db_path=db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO preference_update_log (
                session_id, category, source_type, event_type, event_key, source_event_id,
                before_weight, delta, after_weight, outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                category,
                source_type,
                event_type,
                event_key,
                source_event_id,
                before_weight,
                delta,
                after_weight,
                outcome,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_preference_update_events(
    *,
    session_id: str,
    limit: int = 10,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    ensure_graph_learning_schema(db_path=db_path)
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT
                session_id, category, source_type, event_type, event_key, source_event_id,
                before_weight, delta, after_weight, outcome, created_at
            FROM preference_update_log
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def record_learning_metric(
    *,
    metric_name: str,
    metric_value: float,
    metric_group: str | None = None,
    session_id: str | None = None,
    category: str | None = None,
    source_type: str | None = None,
    db_path: str | None = None,
) -> None:
    ensure_graph_learning_schema(db_path=db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO learning_metrics_log (
                metric_name, metric_value, metric_group, session_id, category, source_type
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (metric_name, metric_value, metric_group, session_id, category, source_type),
        )
        conn.commit()
    finally:
        conn.close()


def cleanup_preference_update_log(
    *,
    retention_days: int,
    source_prefix: str | None = None,
    db_path: str | None = None,
) -> int:
    ensure_graph_learning_schema(db_path=db_path)
    conn = get_connection(db_path)
    try:
        if source_prefix:
            result = conn.execute(
                """
                DELETE FROM preference_update_log
                WHERE datetime(created_at) < datetime('now', ?)
                  AND source_type LIKE ?
                """,
                (f"-{retention_days} days", f"{source_prefix}%"),
            )
        else:
            result = conn.execute(
                """
                DELETE FROM preference_update_log
                WHERE datetime(created_at) < datetime('now', ?)
                """,
                (f"-{retention_days} days",),
            )
        conn.commit()
        return int(result.rowcount or 0)
    finally:
        conn.close()


def get_latest_graph_event_timestamp(
    *,
    event_type: str,
    db_path: str | None = None,
) -> str | None:
    ensure_graph_learning_schema(db_path=db_path)
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT created_at
            FROM graph_event_log
            WHERE event_type = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            (event_type,),
        ).fetchone()
        if not row:
            return None
        return str(row["created_at"])
    finally:
        conn.close()
