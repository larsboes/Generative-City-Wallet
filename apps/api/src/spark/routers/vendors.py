from datetime import date, datetime, timezone

from fastapi import APIRouter, Query

from spark.routers.errors import as_not_found
from spark.models.transactions import (
    DailyTransactionsResponse,
    DashboardHourlyBucket,
    HourRankingsResponse,
    HourlyAverageBucket,
    RevenueLast7DaysResponse,
    TransactionAveragesResponse,
    VendorDashboardTodayResponse,
)
from spark.services.vendor_metrics import (
    fetch_daily_transactions,
    fetch_hour_rankings,
    fetch_last_7_days_revenue,
    fetch_transaction_averages,
    fetch_vendor_dashboard_today,
)

router = APIRouter(prefix="/api/vendors", tags=["vendors"])

@router.get(
    "/{merchant_id}/transactions/daily", response_model=DailyTransactionsResponse
)
def api_daily_transactions(
    merchant_id: str,
    day: date | None = Query(default=None, alias="date"),
) -> DailyTransactionsResponse:
    target_day = day or datetime.now(timezone.utc).date()
    try:
        data = fetch_daily_transactions(merchant_id, target_day)
    except LookupError as exc:
        raise as_not_found(exc) from exc
    return DailyTransactionsResponse(merchant_id=merchant_id, **data)


@router.get(
    "/{merchant_id}/transactions/averages", response_model=TransactionAveragesResponse
)
def api_transaction_averages(
    merchant_id: str,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> TransactionAveragesResponse:
    try:
        daily, hourly = fetch_transaction_averages(merchant_id, lookback_days)
    except LookupError as exc:
        raise as_not_found(exc) from exc
    return TransactionAveragesResponse(
        merchant_id=merchant_id,
        hourly=[HourlyAverageBucket(**b) for b in hourly],
        **daily,
    )


@router.get(
    "/{merchant_id}/revenue/last-7-days", response_model=RevenueLast7DaysResponse
)
def api_last_7_days_revenue(merchant_id: str) -> RevenueLast7DaysResponse:
    try:
        data = fetch_last_7_days_revenue(merchant_id)
    except LookupError as exc:
        raise as_not_found(exc) from exc
    return RevenueLast7DaysResponse(**data)


@router.get(
    "/{merchant_id}/transactions/hour-rankings", response_model=HourRankingsResponse
)
def api_hour_rankings(
    merchant_id: str,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> HourRankingsResponse:
    try:
        data = fetch_hour_rankings(merchant_id, lookback_days)
    except LookupError as exc:
        raise as_not_found(exc) from exc
    return HourRankingsResponse(merchant_id=merchant_id, **data)


@router.get(
    "/{merchant_id}/dashboard/today", response_model=VendorDashboardTodayResponse
)
def api_vendor_dashboard_today(
    merchant_id: str,
    timestamp: datetime | None = None,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> VendorDashboardTodayResponse:
    try:
        payload = fetch_vendor_dashboard_today(merchant_id, timestamp, lookback_days)
    except LookupError as exc:
        raise as_not_found(exc) from exc
    target_day = payload.target_day
    daily = payload.daily
    comparison = payload.comparison
    demand = payload.demand
    revenue = payload.revenue
    current_hour = payload.current_hour

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
        current_hour=current_hour,
        hourly=[DashboardHourlyBucket(**b) for b in hourly],
        demand=demand,
        revenue_last_7_days=RevenueLast7DaysResponse(**revenue),
    )
