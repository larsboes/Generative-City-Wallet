from __future__ import annotations

from datetime import datetime, timedelta, timezone

from spark.db.connection import get_connection
from spark.services.contracts import HistoryGenerationData, LiveUpdateGenerationData
from spark.services.transactions import (
    ensure_utc,
    generate_history_for_venues,
    generate_last_hour_update,
    resolve_venues,
)


def generate_history(
    *,
    merchant_ids: list[str] | None,
    category: str | None,
    city: str | None,
    limit: int,
    days: int,
    start: datetime | None,
    end: datetime | None,
    seed: int | None,
) -> HistoryGenerationData:
    end_dt = ensure_utc(end or datetime.now(timezone.utc))
    start_dt = ensure_utc(start or (end_dt - timedelta(days=days)))
    if start_dt >= end_dt:
        raise ValueError("start must be before end")

    conn = get_connection()
    try:
        venues = resolve_venues(conn, merchant_ids, category, city, limit)
        if not venues:
            raise LookupError("No venues matched the request")
        inserted = generate_history_for_venues(conn, venues, start_dt, end_dt, seed)
    finally:
        conn.close()

    return HistoryGenerationData(
        inserted=inserted,
        venue_count=len(venues),
        start=start_dt,
        end=end_dt,
    )


def generate_live_update(
    *,
    merchant_ids: list[str] | None,
    category: str | None,
    city: str | None,
    limit: int,
    timestamp: datetime | None,
    seed: int | None,
) -> LiveUpdateGenerationData:
    ts = ensure_utc(timestamp or datetime.now(timezone.utc))
    conn = get_connection()
    try:
        venues = resolve_venues(conn, merchant_ids, category, city, limit)
        if not venues:
            raise LookupError("No venues matched the request")
        inserted, window_start, window_end = generate_last_hour_update(
            conn, venues, ts, seed
        )
    finally:
        conn.close()

    return LiveUpdateGenerationData(
        inserted=inserted,
        venue_count=len(venues),
        window_start=window_start,
        window_end=window_end,
    )
