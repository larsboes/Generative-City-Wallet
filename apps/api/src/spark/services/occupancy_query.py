from __future__ import annotations

from datetime import datetime, timezone

from spark.db.connection import get_connection
from spark.services.contracts import OccupancyMerchantData, OccupancyQueryData
from spark.services.demand import compute_demand_context
from spark.services.venues import get_venue, list_venues


def list_available_venues(
    category: str | None,
    city: str | None,
    lat: float | None,
    lon: float | None,
    radius_m: float | None,
    limit: int,
):
    conn = get_connection()
    try:
        return list_venues(conn, category, city, lat, lon, radius_m, limit)
    finally:
        conn.close()


def get_venue_or_none(merchant_id: str):
    conn = get_connection()
    try:
        return get_venue(conn, merchant_id)
    finally:
        conn.close()


def get_occupancy_for_merchant(
    merchant_id: str,
    timestamp: datetime | None,
    arrival_offset_minutes: int,
) -> OccupancyMerchantData:
    dt = timestamp or datetime.now(timezone.utc)
    conn = get_connection()
    try:
        venue = get_venue(conn, merchant_id)
        if not venue:
            raise LookupError("Venue not found")
        demand = compute_demand_context(conn, venue, dt, arrival_offset_minutes)
        return OccupancyMerchantData(venue=venue, timestamp=dt, demand=demand)
    finally:
        conn.close()


def query_occupancy(
    merchant_ids: list[str], timestamp: datetime | None, arrival_offset_minutes: int
) -> OccupancyQueryData:
    dt = timestamp or datetime.now(timezone.utc)
    conn = get_connection()
    try:
        items = []
        for merchant_id in merchant_ids:
            venue = get_venue(conn, merchant_id)
            if not venue:
                continue
            demand = compute_demand_context(conn, venue, dt, arrival_offset_minutes)
            items.append((venue, demand))
        return OccupancyQueryData(timestamp=dt, items=items)
    finally:
        conn.close()
