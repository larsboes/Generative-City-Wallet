from __future__ import annotations

from datetime import datetime, timezone

from spark.models.transactions import PayoneIngestRequest, PayoneIngestResponse
from spark.repositories.payone import insert_payone_transaction


def ingest_payone_event(request: PayoneIngestRequest) -> PayoneIngestResponse:
    timestamp = request.timestamp or datetime.now(timezone.utc)
    day_of_week = (
        request.day_of_week if request.day_of_week is not None else timestamp.weekday()
    )
    hour_of_day = (
        request.hour_of_day if request.hour_of_day is not None else timestamp.hour
    )
    hour_of_week = (
        request.hour_of_week
        if request.hour_of_week is not None
        else (day_of_week * 24 + hour_of_day)
    )
    merchant_type = request.merchant_type or request.category or "unknown"
    total_volume_eur = (
        request.total_volume_eur
        if request.total_volume_eur is not None
        else float(request.amount or 0.0)
    )

    insert_payone_transaction(
        merchant_id=request.merchant_id,
        merchant_type=merchant_type,
        timestamp=timestamp.isoformat(),
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        hour_of_week=hour_of_week,
        txn_count=request.txn_count,
        total_volume_eur=float(total_volume_eur),
    )
    return PayoneIngestResponse(
        success=True,
        merchant_id=request.merchant_id,
        hour_of_week=hour_of_week,
        txn_count=request.txn_count,
        total_volume_eur=float(total_volume_eur),
        timestamp=timestamp,
    )
