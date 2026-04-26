from __future__ import annotations

from datetime import date, datetime, timezone

from spark.db.connection import get_connection
from spark.services.contracts import VendorDashboardData
from spark.services.signals import compute_demand_context
from spark.repositories.transaction_stats import (
    get_daily_average,
    get_daily_transactions,
    get_fastest_slowest_hours,
    get_hourly_average_by_weekday,
    get_last_7_days_revenue,
)
from spark.services.transactions import ensure_utc, floor_hour
from spark.services.venues import get_venue


def _require_venue(conn, merchant_id: str):
    venue = get_venue(conn, merchant_id)
    if not venue:
        raise LookupError("Venue not found")
    return venue


def fetch_daily_transactions(merchant_id: str, day: date) -> dict:
    conn = get_connection()
    try:
        _require_venue(conn, merchant_id)
        return get_daily_transactions(conn, merchant_id, day)
    finally:
        conn.close()


def fetch_transaction_averages(
    merchant_id: str, lookback_days: int
) -> tuple[dict, list[dict]]:
    today = datetime.now(timezone.utc).date()
    conn = get_connection()
    try:
        _require_venue(conn, merchant_id)
        daily = get_daily_average(conn, merchant_id, lookback_days, today)
        hourly = get_hourly_average_by_weekday(
            conn, merchant_id, today.weekday(), lookback_days, today
        )
        return daily, hourly
    finally:
        conn.close()


def fetch_last_7_days_revenue(merchant_id: str) -> dict:
    conn = get_connection()
    try:
        _require_venue(conn, merchant_id)
        return get_last_7_days_revenue(conn, merchant_id)
    finally:
        conn.close()


def fetch_hour_rankings(merchant_id: str, lookback_days: int) -> dict:
    conn = get_connection()
    try:
        _require_venue(conn, merchant_id)
        return get_fastest_slowest_hours(conn, merchant_id, lookback_days)
    finally:
        conn.close()


def fetch_vendor_dashboard_today(
    merchant_id: str, timestamp: datetime | None, lookback_days: int
) -> VendorDashboardData:
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

    return VendorDashboardData(
        target_day=target_day,
        current_hour=dt.hour,
        daily=daily,
        comparison=comparison,
        demand=demand,
        revenue=revenue,
    )
