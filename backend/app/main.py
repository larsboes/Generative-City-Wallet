from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query

from backend.app import db
from backend.app.models import (
    DailyTransactionsResponse,
    HourRankingsResponse,
    LiveUpdateRequest,
    OccupancyQueryRequest,
    OccupancyQueryResponse,
    OccupancyResponse,
    RevenueLast7DaysResponse,
    TransactionAveragesResponse,
    TransactionGenerationRequest,
    TransactionGenerationResponse,
    Venue,
    VenueListResponse,
    VendorDashboardTodayResponse,
)
from backend.app.services.signals import compute_demand_context
from backend.app.services.transaction_stats import (
    get_daily_average,
    get_daily_transactions,
    get_fastest_slowest_hours,
    get_hourly_average_by_weekday,
    get_last_7_days_revenue,
)
from backend.app.services.transactions import (
    ensure_utc,
    floor_hour,
    generate_history_for_venues,
    generate_last_hour_update,
    resolve_venues,
)
from backend.app.services.venues import get_venue, list_venues


app = FastAPI(
    title="Spark Occupancy API",
    description="Generic venue demand and occupancy data source for LLM recommendations.",
    version="0.1.0",
)


@app.on_event("startup")
def startup() -> None:
    db.init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "occupancy-api"}


def require_venue(conn, merchant_id: str) -> Venue:
    venue = get_venue(conn, merchant_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


def require_selected_venues(conn, request) -> list[Venue]:
    venues = resolve_venues(
        conn,
        merchant_ids=request.merchant_ids,
        city=request.city,
        category=request.category,
        limit=request.limit,
    )
    if not venues:
        raise HTTPException(status_code=404, detail="No venues matched the request")
    return venues


@app.get("/api/venues", response_model=VenueListResponse)
def api_list_venues(
    category: str | None = Query(default=None, description="Comma-separated category filter."),
    city: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float | None = Query(default=None, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> VenueListResponse:
    with db.connect() as conn:
        venues = list_venues(conn, category, city, lat, lon, radius_m, limit)
    return VenueListResponse(venues=venues, count=len(venues))


@app.get("/api/venues/{merchant_id}", response_model=Venue)
def api_get_venue(merchant_id: str) -> Venue:
    with db.connect() as conn:
        venue = get_venue(conn, merchant_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@app.get("/api/occupancy/{merchant_id}", response_model=OccupancyResponse)
def api_get_occupancy(
    merchant_id: str,
    timestamp: datetime | None = None,
    arrival_offset_minutes: int = Query(default=10, ge=0, le=240),
) -> OccupancyResponse:
    dt = timestamp or datetime.now(timezone.utc)
    with db.connect() as conn:
        venue = require_venue(conn, merchant_id)
        demand = compute_demand_context(conn, venue, dt, arrival_offset_minutes)

    return OccupancyResponse(
        merchant_id=venue.merchant_id,
        name=venue.name,
        category=venue.category,
        city=venue.city,
        timestamp=dt,
        demand=demand,
    )


@app.post("/api/occupancy/query", response_model=OccupancyQueryResponse)
def api_query_occupancy(request: OccupancyQueryRequest) -> OccupancyQueryResponse:
    dt = request.timestamp or datetime.now(timezone.utc)
    results: list[OccupancyResponse] = []

    with db.connect() as conn:
        for merchant_id in request.merchant_ids:
            venue = get_venue(conn, merchant_id)
            if not venue:
                continue
            demand = compute_demand_context(
                conn,
                venue,
                dt,
                request.arrival_offset_minutes,
            )
            results.append(
                OccupancyResponse(
                    merchant_id=venue.merchant_id,
                    name=venue.name,
                    category=venue.category,
                    city=venue.city,
                    timestamp=dt,
                    demand=demand,
                )
            )

    return OccupancyQueryResponse(results=results, count=len(results))


@app.post("/api/transactions/generate/history", response_model=TransactionGenerationResponse)
def api_generate_history(request: TransactionGenerationRequest) -> TransactionGenerationResponse:
    end = ensure_utc(request.end or datetime.now(timezone.utc))
    start = ensure_utc(request.start or (end - timedelta(days=request.days)))
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    with db.connect() as conn:
        venues = require_selected_venues(conn, request)
        inserted = generate_history_for_venues(conn, venues, start, end, request.seed)

    return TransactionGenerationResponse(
        inserted_count=inserted,
        venue_count=len(venues),
        start=start,
        end=end,
        source="synthetic_history",
    )


@app.post("/api/transactions/generate/live-update", response_model=TransactionGenerationResponse)
def api_generate_live_update(request: LiveUpdateRequest) -> TransactionGenerationResponse:
    timestamp = ensure_utc(request.timestamp or datetime.now(timezone.utc))
    with db.connect() as conn:
        venues = require_selected_venues(conn, request)
        inserted, window_start, window_end = generate_last_hour_update(conn, venues, timestamp, request.seed)

    return TransactionGenerationResponse(
        inserted_count=inserted,
        venue_count=len(venues),
        start=window_start,
        end=window_end,
        source="synthetic_live_update",
    )


@app.get("/api/vendors/{merchant_id}/transactions/daily", response_model=DailyTransactionsResponse)
def api_daily_transactions(
    merchant_id: str,
    day: date | None = Query(default=None, alias="date"),
) -> DailyTransactionsResponse:
    target_day = day or datetime.now(timezone.utc).date()
    with db.connect() as conn:
        require_venue(conn, merchant_id)
        data = get_daily_transactions(conn, merchant_id, target_day)
    return DailyTransactionsResponse(merchant_id=merchant_id, **data)


@app.get("/api/vendors/{merchant_id}/transactions/averages", response_model=TransactionAveragesResponse)
def api_transaction_averages(
    merchant_id: str,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> TransactionAveragesResponse:
    today = datetime.now(timezone.utc).date()
    with db.connect() as conn:
        require_venue(conn, merchant_id)
        daily = get_daily_average(conn, merchant_id, lookback_days, today)
        hourly = get_hourly_average_by_weekday(conn, merchant_id, today.weekday(), lookback_days, today)
    return TransactionAveragesResponse(merchant_id=merchant_id, hourly=hourly, **daily)


@app.get("/api/vendors/{merchant_id}/revenue/last-7-days", response_model=RevenueLast7DaysResponse)
def api_last_7_days_revenue(merchant_id: str) -> RevenueLast7DaysResponse:
    with db.connect() as conn:
        require_venue(conn, merchant_id)
        data = get_last_7_days_revenue(conn, merchant_id)
    return RevenueLast7DaysResponse(**data)


@app.get("/api/vendors/{merchant_id}/transactions/hour-rankings", response_model=HourRankingsResponse)
def api_hour_rankings(
    merchant_id: str,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> HourRankingsResponse:
    with db.connect() as conn:
        require_venue(conn, merchant_id)
        data = get_fastest_slowest_hours(conn, merchant_id, lookback_days)
    return HourRankingsResponse(merchant_id=merchant_id, **data)


@app.get("/api/vendors/{merchant_id}/dashboard/today", response_model=VendorDashboardTodayResponse)
def api_vendor_dashboard_today(
    merchant_id: str,
    timestamp: datetime | None = None,
    lookback_days: int = Query(default=28, ge=1, le=365),
) -> VendorDashboardTodayResponse:
    dt = ensure_utc(timestamp or datetime.now(timezone.utc))
    target_day = dt.date()
    with db.connect() as conn:
        venue = require_venue(conn, merchant_id)
        daily = get_daily_transactions(conn, merchant_id, target_day)
        comparison = get_hourly_average_by_weekday(conn, merchant_id, dt.weekday(), lookback_days, target_day)
        demand = compute_demand_context(conn, venue, floor_hour(dt), arrival_offset_minutes=10)
        revenue = get_last_7_days_revenue(conn, merchant_id, target_day)

    comparison_by_hour = {bucket["hour"]: bucket for bucket in comparison}
    hourly = []
    for bucket in daily["hourly"]:
        compare = comparison_by_hour[bucket["hour"]]
        hourly.append(
            {
                **bucket,
                "comparison_avg_transaction_count": compare["avg_transaction_count"],
                "comparison_avg_revenue_eur": compare["avg_revenue_eur"],
            }
        )

    return VendorDashboardTodayResponse(
        merchant_id=merchant_id,
        date=target_day,
        current_hour=dt.hour,
        hourly=hourly,
        demand=demand,
        revenue_last_7_days=RevenueLast7DaysResponse(**revenue),
    )
