from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from spark.db.connection import get_connection

CREATE_RATE_WINDOW_SECONDS = 60
JOIN_RATE_WINDOW_SECONDS = 10
MAX_WAVE_PARTICIPANTS = 50


def _rate_limit_key(prefix: str, subject: str, window_seconds: int) -> str:
    bucket = int(datetime.now(timezone.utc).timestamp() // window_seconds)
    return f"{prefix}:{subject}:{bucket}"


def _acquire_rate_limit_slot(
    conn, *, key: str, session_id: str, source: str
) -> bool:
    result = conn.execute(
        """
        INSERT OR IGNORE INTO graph_event_log (
            idempotency_key, event_type, session_id, offer_id, source
        ) VALUES (?, ?, ?, NULL, ?)
        """,
        (key, "wave_rate_limit", session_id, source),
    )
    return result.rowcount > 0


def create_wave(
    *,
    offer_id: str,
    merchant_id: str,
    created_by_session: str,
    milestone_target: int,
    ttl_minutes: int,
    db_path: str | None = None,
) -> dict | None:
    wave_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    conn = get_connection(db_path)
    try:
        create_slot = _acquire_rate_limit_slot(
            conn,
            key=_rate_limit_key(
                "wave_create",
                f"{created_by_session}:{offer_id}",
                CREATE_RATE_WINDOW_SECONDS,
            ),
            session_id=created_by_session,
            source="spark_wave_create",
        )
        if not create_slot:
            return None

        conn.execute(
            """
            INSERT INTO spark_waves (
                wave_id, offer_id, merchant_id, created_by_session,
                participant_count, milestone_target, expires_at, status
            ) VALUES (?, ?, ?, ?, 1, ?, ?, 'ACTIVE')
            """,
            (
                wave_id,
                offer_id,
                merchant_id,
                created_by_session,
                milestone_target,
                expires_at.isoformat(),
            ),
        )
        conn.commit()
        return get_wave(wave_id=wave_id, db_path=db_path)
    finally:
        conn.close()


def _compute_catalyst_bonus_pct(
    *, participant_count: int, milestone_target: int, status: str
) -> float:
    if status == "EXPIRED":
        return 0.0
    progress = 0.0
    if milestone_target > 0:
        progress = min(max(participant_count / milestone_target, 0.0), 1.0)
    # Deterministic and auditable: starts at 5%, scales to 20% at completion.
    return round(0.05 + (0.15 * progress), 3)


def get_wave(*, wave_id: str, db_path: str | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT wave_id, offer_id, merchant_id, participant_count, milestone_target, status, expires_at
            FROM spark_waves
            WHERE wave_id = ?
            """,
            (wave_id,),
        ).fetchone()
        if not row:
            return None
        wave = dict(row)
        wave["catalyst_bonus_pct"] = _compute_catalyst_bonus_pct(
            participant_count=int(wave["participant_count"]),
            milestone_target=int(wave["milestone_target"]),
            status=str(wave["status"]),
        )
        return wave
    finally:
        conn.close()


def expire_old_waves(db_path: str | None = None) -> int:
    """Best-effort TTL cleanup for waves; returns number of rows updated."""
    conn = get_connection(db_path)
    try:
        result = conn.execute(
            """
            UPDATE spark_waves
            SET status = 'EXPIRED'
            WHERE status = 'ACTIVE'
              AND datetime(expires_at) < datetime('now')
            """
        )
        conn.commit()
        return int(result.rowcount or 0)
    finally:
        conn.close()


def join_wave(
    *, wave_id: str, session_id: str, db_path: str | None = None
) -> tuple[dict, bool] | None:
    expire_old_waves(db_path=db_path)
    conn = get_connection(db_path)
    try:
        join_slot = _acquire_rate_limit_slot(
            conn,
            key=_rate_limit_key(
                "wave_join_attempt",
                f"{wave_id}:{session_id}",
                JOIN_RATE_WINDOW_SECONDS,
            ),
            session_id=session_id,
            source="spark_wave_join",
        )
        if not join_slot:
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None

        row = conn.execute(
            "SELECT participant_count, milestone_target, status, expires_at FROM spark_waves WHERE wave_id = ?",
            (wave_id,),
        ).fetchone()
        if not row:
            return None
        if row["status"] == "COMPLETED":
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None
        if row["status"] != "ACTIVE":
            return None
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(row["expires_at"])
        if now > expires_at:
            conn.execute(
                "UPDATE spark_waves SET status = 'EXPIRED' WHERE wave_id = ?",
                (wave_id,),
            )
            conn.commit()
            return None

        replay_guard = conn.execute(
            """
            INSERT OR IGNORE INTO graph_event_log (
                idempotency_key, event_type, session_id, offer_id, source
            )
            SELECT ?, 'wave_join', ?, wave_id, 'spark_wave'
            FROM spark_waves WHERE wave_id = ?
            """,
            (
                f"wave_join:{wave_id}:{session_id}",
                session_id,
                wave_id,
            ),
        )
        if replay_guard.rowcount == 0:
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None

        if int(row["participant_count"]) >= MAX_WAVE_PARTICIPANTS:
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None

        next_count = int(row["participant_count"]) + 1
        next_status = "COMPLETED" if next_count >= int(row["milestone_target"]) else "ACTIVE"
        conn.execute(
            "UPDATE spark_waves SET participant_count = ?, status = ? WHERE wave_id = ?",
            (next_count, next_status, wave_id),
        )
        conn.commit()
        updated = get_wave(wave_id=wave_id, db_path=db_path)
        return (updated, True) if updated else None
    finally:
        conn.close()
