from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from spark.db.connection import get_connection
from spark.models.transactions import (
    DailyTransactionsResponse,
    DashboardHourlyBucket,
    HourRankingsResponse,
    HourlyAverageBucket,
    RevenueLast7DaysResponse,
    TransactionAveragesResponse,
    VendorDashboardTodayResponse,
)
from spark.services.signals import compute_demand_context
from spark.services.transaction_stats import (
    get_daily_average,
    get_daily_transactions,
    get_fastest_slowest_hours,
    get_hourly_average_by_weekday,
    get_last_7_days_revenue,
)
from spark.services.transactions import ensure_utc, floor_hour
from spark.services.venues import get_venue

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


def _require_venue(conn, merchant_id: str):
    venue = get_venue(conn, merchant_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.get(
    "/{merchant_id}/transactions/daily", response_model=DailyTransactionsResponse
)
def api_daily_transactions(
    merchant_id: str,
    day: date | None = Query(default=None, alias="date"),
) -> DailyTransactionsResponse:
    target_day = day or datetime.now(timezone.utc).date()
    conn = get_connection()
    try:
        _require_venue(conn, merchant_id)
        data = get_daily_transactions(conn, merchant_id, target_day)
    finally:
        conn.close()
    return DailyTransactionsResponse(merchant_id=merchant_id, **data)


@router.get(
    "/{merchant_id}/transactions/averages", response_model=TransactionAveragesResponse
)
def api_transaction_averages(
    merchant_id: str,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> TransactionAveragesResponse:
    today = datetime.now(timezone.utc).date()
    conn = get_connection()
    try:
        _require_venue(conn, merchant_id)
        daily = get_daily_average(conn, merchant_id, lookback_days, today)
        hourly = get_hourly_average_by_weekday(
            conn, merchant_id, today.weekday(), lookback_days, today
        )
    finally:
        conn.close()
    return TransactionAveragesResponse(
        merchant_id=merchant_id,
        hourly=[HourlyAverageBucket(**b) for b in hourly],
        **daily,
    )


@router.get(
    "/{merchant_id}/revenue/last-7-days", response_model=RevenueLast7DaysResponse
)
def api_last_7_days_revenue(merchant_id: str) -> RevenueLast7DaysResponse:
    conn = get_connection()
    try:
        _require_venue(conn, merchant_id)
        data = get_last_7_days_revenue(conn, merchant_id)
    finally:
        conn.close()
    return RevenueLast7DaysResponse(**data)


@router.get(
    "/{merchant_id}/transactions/hour-rankings", response_model=HourRankingsResponse
)
def api_hour_rankings(
    merchant_id: str,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> HourRankingsResponse:
    conn = get_connection()
    try:
        _require_venue(conn, merchant_id)
        data = get_fastest_slowest_hours(conn, merchant_id, lookback_days)
    finally:
        conn.close()
    return HourRankingsResponse(merchant_id=merchant_id, **data)


@router.get(
    "/{merchant_id}/dashboard/today", response_model=VendorDashboardTodayResponse
)
def api_vendor_dashboard_today(
    merchant_id: str,
    timestamp: datetime | None = None,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> VendorDashboardTodayResponse:
    dt = ensure_utc(timestamp or datetime.now(timezone.utc))
    target_day = dt.date()
    conn = get_connection()
    try:
        venue = _require_venue(conn, merchant_id)
        daily = get_daily_transactions(conn, merchant_id, target_day)
        comparison = get_hourly_average_by_weekday(
            conn, merchant_id, dt.weekday(), lookback_days, target_day
        )
        demand = compute_demand_context(
            conn, venue, floor_hour(dt), arrival_offset_minutes=10
        )
        revenue = get_last_7_days_revenue(conn, merchant_id, target_day)
    finally:
        conn.close()

    comparison_by_hour = {b["hour"]: b for b in comparison}
    hourly = [
        {
            **bucket,
            "comparison_avg_transaction_count": comparison_by_hour[bucket["hour"]][
                "avg_transaction_count"
            ],
            "comparison_avg_revenue_eur": comparison_by_hour[bucket["hour"]][
                "avg_revenue_eur"
            ],
        }
        for bucket in daily["hourly"]
    ]

    return VendorDashboardTodayResponse(
        merchant_id=merchant_id,
        date=target_day,
        current_hour=dt.hour,
        hourly=[DashboardHourlyBucket(**b) for b in hourly],
        demand=demand,
        revenue_last_7_days=RevenueLast7DaysResponse(**revenue),
    )
