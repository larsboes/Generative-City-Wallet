"""
Wave rate-limiting service.

Contains rate-limit policy constants and helpers extracted from
``spark.repositories.wave``.  The repository imports the symbols it needs
from this module (architecture boundary checkers allow repositories to
import from services).
"""

from __future__ import annotations

from datetime import datetime, timezone

# ── rate-limit policy constants ──────────────────────────────────────

CREATE_RATE_WINDOW_SECONDS: int = 60
JOIN_RATE_WINDOW_SECONDS: int = 10
MAX_WAVE_PARTICIPANTS: int = 50
MAX_ACTIVE_WAVES_PER_SESSION: int = 3
MAX_CREATE_ATTEMPTS_PER_SESSION_WINDOW: int = 3
MAX_JOIN_ATTEMPTS_PER_SESSION_WINDOW: int = 12
MAX_JOIN_ATTEMPTS_PER_WAVE_WINDOW: int = 60
JOIN_RISK_WINDOW_SECONDS: int = 15 * 60
MAX_JOIN_RISK_SCORE: float = 0.8


# ── rate-limit helpers ───────────────────────────────────────────────


def _rate_limit_key(prefix: str, subject: str, window_seconds: int) -> str:
    bucket = int(datetime.now(timezone.utc).timestamp() // window_seconds)
    return f"{prefix}:{subject}:{bucket}"


def _acquire_rate_limit_slot(
    conn, *, key: str, session_id: str, source: str, offer_id: str | None = None
) -> bool:
    result = conn.execute(
        """
        INSERT OR IGNORE INTO graph_event_log (
            idempotency_key, event_type, session_id, offer_id, source
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (key, "wave_rate_limit", session_id, offer_id, source),
    )
    return result.rowcount > 0


def _recent_event_count(
    conn,
    *,
    event_type: str,
    session_id: str | None = None,
    offer_id: str | None = None,
    source: str | None = None,
    window_seconds: int,
) -> int:
    filters = ["event_type = ?", "datetime(created_at) >= datetime('now', ?)"]
    params: list[object] = [event_type, f"-{window_seconds} seconds"]
    if session_id is not None:
        filters.append("session_id = ?")
        params.append(session_id)
    if offer_id is not None:
        filters.append("offer_id = ?")
        params.append(offer_id)
    if source is not None:
        filters.append("source = ?")
        params.append(source)
    row = conn.execute(
        f"SELECT COUNT(*) AS c FROM graph_event_log WHERE {' AND '.join(filters)}",
        tuple(params),
    ).fetchone()
    return int((row and row["c"]) or 0)


def _log_join_denied(
    conn,
    *,
    wave_id: str,
    session_id: str,
    reason: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO graph_event_log (
            idempotency_key, event_type, session_id, offer_id, source, category
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            _rate_limit_key(
                "wave_join_denied",
                f"{wave_id}:{session_id}:{reason}",
                JOIN_RATE_WINDOW_SECONDS,
            ),
            "wave_join_denied",
            session_id,
            wave_id,
            "spark_wave_join_denied",
            reason,
        ),
    )


def _session_join_risk_score(conn, *, session_id: str) -> float:
    denied = _recent_event_count(
        conn,
        event_type="wave_join_denied",
        session_id=session_id,
        source="spark_wave_join_denied",
        window_seconds=JOIN_RISK_WINDOW_SECONDS,
    )
    attempts = _recent_event_count(
        conn,
        event_type="wave_rate_limit",
        session_id=session_id,
        source="spark_wave_join",
        window_seconds=JOIN_RISK_WINDOW_SECONDS,
    )
    successful = _recent_event_count(
        conn,
        event_type="wave_join",
        session_id=session_id,
        source="spark_wave",
        window_seconds=JOIN_RISK_WINDOW_SECONDS,
    )
    if attempts == 0 and denied == 0:
        return 0.0
    denial_pressure = denied / max(1, attempts)
    low_success_penalty = 0.35 if successful == 0 and (attempts + denied) >= 6 else 0.0
    score = min(1.0, (denial_pressure * 0.5) + low_success_penalty)
    return round(score, 3)
