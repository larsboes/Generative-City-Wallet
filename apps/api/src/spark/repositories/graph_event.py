from __future__ import annotations

import hashlib
from typing import Any

from spark.db.connection import get_connection
from spark.repositories.redemption import (
    _hash_payload,
    _iso_from_unix,
    ensure_graph_learning_schema,
)


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
