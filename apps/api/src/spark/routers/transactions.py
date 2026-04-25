from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from spark.db.connection import get_connection
from spark.models.contracts import (
    LiveUpdateRequest,
    TransactionGenerationRequest,
    TransactionGenerationResponse,
)
from spark.services.transactions import (
    ensure_utc,
    generate_history_for_venues,
    generate_last_hour_update,
    resolve_venues,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("/generate/history", response_model=TransactionGenerationResponse)
def api_generate_history(request: TransactionGenerationRequest) -> TransactionGenerationResponse:
    end = ensure_utc(request.end or datetime.now(timezone.utc))
    start = ensure_utc(request.start or (end - timedelta(days=request.days)))
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    conn = get_connection()
    try:
        venues = resolve_venues(conn, request.merchant_ids, request.category, request.city, request.limit)
        if not venues:
            raise HTTPException(status_code=404, detail="No venues matched the request")
        inserted = generate_history_for_venues(conn, venues, start, end, request.seed)
    finally:
        conn.close()

    return TransactionGenerationResponse(
        inserted_count=inserted,
        venue_count=len(venues),
        start=start,
        end=end,
        source="synthetic_history",
    )


@router.post("/generate/live-update", response_model=TransactionGenerationResponse)
def api_generate_live_update(request: LiveUpdateRequest) -> TransactionGenerationResponse:
    timestamp = ensure_utc(request.timestamp or datetime.now(timezone.utc))
    conn = get_connection()
    try:
        venues = resolve_venues(conn, request.merchant_ids, request.category, request.city, request.limit)
        if not venues:
            raise HTTPException(status_code=404, detail="No venues matched the request")
        inserted, window_start, window_end = generate_last_hour_update(conn, venues, timestamp, request.seed)
    finally:
        conn.close()

    return TransactionGenerationResponse(
        inserted_count=inserted,
        venue_count=len(venues),
        start=window_start,
        end=window_end,
        source="synthetic_live_update",
    )
