from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from spark.db.connection import get_connection
from spark.models.transactions import (
    OccupancyQueryRequest,
    OccupancyQueryResponse,
    OccupancyResponse,
    Venue,
    VenueListResponse,
)
from spark.services.signals import compute_demand_context
from spark.services.venues import get_venue, list_venues

router = APIRouter(prefix="/api", tags=["occupancy"])


@router.get("/venues", response_model=VenueListResponse)
def api_list_venues(
    category: str | None = Query(
        default=None, description="Comma-separated category filter."
    ),
    city: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float | None = Query(default=None, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> VenueListResponse:
    conn = get_connection()
    try:
        venues = list_venues(conn, category, city, lat, lon, radius_m, limit)
    finally:
        conn.close()
    return VenueListResponse(venues=venues, count=len(venues))


@router.get("/venues/{merchant_id}", response_model=Venue)
def api_get_venue(merchant_id: str) -> Venue:
    conn = get_connection()
    try:
        venue = get_venue(conn, merchant_id)
    finally:
        conn.close()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.get("/occupancy/{merchant_id}", response_model=OccupancyResponse)
def api_get_occupancy(
    merchant_id: str,
    timestamp: datetime | None = None,
    arrival_offset_minutes: int = Query(default=10, ge=0, le=240),
) -> OccupancyResponse:
    dt = timestamp or datetime.now(timezone.utc)
    conn = get_connection()
    try:
        venue = get_venue(conn, merchant_id)
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        demand = compute_demand_context(conn, venue, dt, arrival_offset_minutes)
    finally:
        conn.close()
    return OccupancyResponse(
        merchant_id=venue.merchant_id,
        name=venue.name,
        category=venue.category,
        city=venue.city,
        timestamp=dt,
        demand=demand,
    )


@router.post("/occupancy/query", response_model=OccupancyQueryResponse)
def api_query_occupancy(request: OccupancyQueryRequest) -> OccupancyQueryResponse:
    dt = request.timestamp or datetime.now(timezone.utc)
    results: list[OccupancyResponse] = []
    conn = get_connection()
    try:
        for merchant_id in request.merchant_ids:
            venue = get_venue(conn, merchant_id)
            if not venue:
                continue
            demand = compute_demand_context(
                conn, venue, dt, request.arrival_offset_minutes
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
    finally:
        conn.close()
    return OccupancyQueryResponse(results=results, count=len(results))
