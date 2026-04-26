from __future__ import annotations

from typing import Any

from spark.db.connection import get_connection
from spark.repositories.redemption import ensure_graph_learning_schema


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
