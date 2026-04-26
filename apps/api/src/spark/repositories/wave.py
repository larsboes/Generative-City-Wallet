from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from spark.db.connection import get_connection

CREATE_RATE_WINDOW_SECONDS = 60
JOIN_RATE_WINDOW_SECONDS = 10
MAX_WAVE_PARTICIPANTS = 50
MAX_ACTIVE_WAVES_PER_SESSION = 3
MAX_CREATE_ATTEMPTS_PER_SESSION_WINDOW = 3
MAX_JOIN_ATTEMPTS_PER_SESSION_WINDOW = 12
MAX_JOIN_ATTEMPTS_PER_WAVE_WINDOW = 60
JOIN_RISK_WINDOW_SECONDS = 15 * 60
MAX_JOIN_RISK_SCORE = 0.8


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
        active_waves = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM spark_waves
            WHERE created_by_session = ? AND status = 'ACTIVE'
            """,
            (created_by_session,),
        ).fetchone()
        if (
            int((active_waves and active_waves["c"]) or 0)
            >= MAX_ACTIVE_WAVES_PER_SESSION
        ):
            return None

        recent_creates = _recent_event_count(
            conn,
            event_type="wave_rate_limit",
            session_id=created_by_session,
            source="spark_wave_create",
            window_seconds=CREATE_RATE_WINDOW_SECONDS,
        )
        if recent_creates >= MAX_CREATE_ATTEMPTS_PER_SESSION_WINDOW:
            return None

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


def get_completed_wave_bonus_for_offer(
    *, offer_id: str, db_path: str | None = None
) -> float:
    """
    Return deterministic catalyst bonus pct for a completed, non-expired wave.

    If multiple completed waves exist for the same offer, choose the highest
    deterministic bonus to keep redemption economics stable and auditable.
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT participant_count, milestone_target, status
            FROM spark_waves
            WHERE offer_id = ?
              AND status = 'COMPLETED'
              AND datetime(expires_at) >= datetime('now')
            """,
            (offer_id,),
        ).fetchall()
        if not rows:
            return 0.0
        bonuses = [
            _compute_catalyst_bonus_pct(
                participant_count=int(row["participant_count"]),
                milestone_target=int(row["milestone_target"]),
                status=str(row["status"]),
            )
            for row in rows
        ]
        return float(max(bonuses))
    finally:
        conn.close()


def get_session_wave_bonus_for_merchant(
    *, session_id: str, merchant_id: str, db_path: str | None = None
) -> float:
    """
    Return the highest deterministic catalyst bonus for waves this session is
    participating in (creator or joiner) for the given merchant.
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT
                sw.participant_count,
                sw.milestone_target,
                sw.status
            FROM spark_waves sw
            LEFT JOIN graph_event_log gel
              ON gel.offer_id = sw.wave_id
             AND gel.event_type = 'wave_join'
             AND gel.session_id = ?
            WHERE sw.merchant_id = ?
              AND sw.status IN ('ACTIVE', 'COMPLETED')
              AND datetime(sw.expires_at) >= datetime('now')
              AND (
                sw.created_by_session = ?
                OR gel.idempotency_key IS NOT NULL
              )
            """,
            (session_id, merchant_id, session_id),
        ).fetchall()
        if not rows:
            return 0.0
        bonuses = [
            _compute_catalyst_bonus_pct(
                participant_count=int(row["participant_count"]),
                milestone_target=int(row["milestone_target"]),
                status=str(row["status"]),
            )
            for row in rows
        ]
        return float(max(bonuses))
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
        risk_score = _session_join_risk_score(conn, session_id=session_id)
        if risk_score >= MAX_JOIN_RISK_SCORE:
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="risk_gate",
            )
            conn.commit()
            return None

        recent_joins_for_session = _recent_event_count(
            conn,
            event_type="wave_rate_limit",
            session_id=session_id,
            source="spark_wave_join",
            window_seconds=60,
        )
        if recent_joins_for_session >= MAX_JOIN_ATTEMPTS_PER_SESSION_WINDOW:
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="session_burst_limit",
            )
            conn.commit()
            return None

        recent_joins_for_wave = _recent_event_count(
            conn,
            event_type="wave_rate_limit",
            offer_id=wave_id,
            source="spark_wave_join",
            window_seconds=60,
        )
        if recent_joins_for_wave >= MAX_JOIN_ATTEMPTS_PER_WAVE_WINDOW:
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="wave_burst_limit",
            )
            conn.commit()
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None

        join_slot = _acquire_rate_limit_slot(
            conn,
            key=_rate_limit_key(
                "wave_join_attempt",
                f"{wave_id}:{session_id}",
                JOIN_RATE_WINDOW_SECONDS,
            ),
            session_id=session_id,
            source="spark_wave_join",
            offer_id=wave_id,
        )
        if not join_slot:
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="join_slot_duplicate",
            )
            conn.commit()
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None

        row = conn.execute(
            "SELECT participant_count, milestone_target, status, expires_at FROM spark_waves WHERE wave_id = ?",
            (wave_id,),
        ).fetchone()
        if not row:
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="wave_not_found",
            )
            conn.commit()
            return None
        if row["status"] == "COMPLETED":
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="wave_completed",
            )
            conn.commit()
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None
        if row["status"] != "ACTIVE":
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="wave_inactive",
            )
            conn.commit()
            return None
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(row["expires_at"])
        if now > expires_at:
            conn.execute(
                "UPDATE spark_waves SET status = 'EXPIRED' WHERE wave_id = ?",
                (wave_id,),
            )
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="wave_expired",
            )
            conn.commit()
            return None

        replay_guard = conn.execute(
            """
            INSERT OR IGNORE INTO graph_event_log (
                idempotency_key, event_type, session_id, offer_id, source
            )
            SELECT ?, 'wave_join', ?, ?, 'spark_wave'
            FROM spark_waves WHERE wave_id = ?
            """,
            (
                f"wave_join:{wave_id}:{session_id}",
                session_id,
                wave_id,
                wave_id,
            ),
        )
        if replay_guard.rowcount == 0:
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="join_replay",
            )
            conn.commit()
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None

        if int(row["participant_count"]) >= MAX_WAVE_PARTICIPANTS:
            _log_join_denied(
                conn,
                wave_id=wave_id,
                session_id=session_id,
                reason="participant_cap",
            )
            conn.commit()
            existing = get_wave(wave_id=wave_id, db_path=db_path)
            return (existing, False) if existing else None

        next_count = int(row["participant_count"]) + 1
        next_status = (
            "COMPLETED" if next_count >= int(row["milestone_target"]) else "ACTIVE"
        )
        conn.execute(
            "UPDATE spark_waves SET participant_count = ?, status = ? WHERE wave_id = ?",
            (next_count, next_status, wave_id),
        )
        conn.commit()
        updated = get_wave(wave_id=wave_id, db_path=db_path)
        return (updated, True) if updated else None
    finally:
        conn.close()
