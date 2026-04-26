"""SQLite repository for cross-session identity links."""

from __future__ import annotations

from spark.db.connection import get_connection


def link_session_to_continuity(
    continuity_id: str, session_id: str, db_path: str | None = None
) -> None:
    """Record that a session belongs to a continuity identity."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO identity_links (continuity_id, session_id) VALUES (?, ?)",
            (continuity_id, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_sessions_for_continuity(
    continuity_id: str, db_path: str | None = None
) -> list[str]:
    """All session_ids that have been linked to this continuity_id."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT session_id FROM identity_links WHERE continuity_id = ? ORDER BY linked_at",
            (continuity_id,),
        ).fetchall()
        return [r["session_id"] for r in rows]
    finally:
        conn.close()


def get_continuity_for_session(
    session_id: str, db_path: str | None = None
) -> str | None:
    """Look up what continuity_id a session is linked to, if any."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT continuity_id FROM identity_links WHERE session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        return row["continuity_id"] if row else None
    finally:
        conn.close()


def unlink_session(session_id: str, db_path: str | None = None) -> None:
    """Remove identity link for a session (opt-out / erasure)."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "DELETE FROM identity_links WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
    finally:
        conn.close()
