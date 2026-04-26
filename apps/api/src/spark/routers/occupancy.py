from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from spark.models.demand import (
    OccupancyQueryRequest,
    OccupancyQueryResponse,
    OccupancyResponse,
    Venue,
    VenueListResponse,
)
from spark.routers.errors import as_not_found
from spark.services.occupancy_query import (
    get_occupancy_for_merchant,
    get_venue_or_none,
    list_available_venues,
    query_occupancy,
)

router = APIRouter(prefix="/api/v1", tags=["occupancy"])


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
    venues = list_available_venues(category, city, lat, lon, radius_m, limit)
    return VenueListResponse(venues=venues, count=len(venues))


@router.get("/venues/{merchant_id}", response_model=Venue)
def api_get_venue(merchant_id: str) -> Venue:
    venue = get_venue_or_none(merchant_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.get("/occupancy/{merchant_id}", response_model=OccupancyResponse)
def api_get_occupancy(
    merchant_id: str,
    timestamp: datetime | None = None,
    arrival_offset_minutes: int = Query(default=10, ge=0, le=240),
) -> OccupancyResponse:
    try:
        data = get_occupancy_for_merchant(
            merchant_id, timestamp, arrival_offset_minutes
        )
    except LookupError as exc:
        raise as_not_found(exc) from exc
    return OccupancyResponse(
        merchant_id=data.venue.merchant_id,
        name=data.venue.name,
        category=data.venue.category,
        city=data.venue.city,
        timestamp=data.timestamp,
        demand=data.demand,
    )


@router.post("/occupancy/query", response_model=OccupancyQueryResponse)
def api_query_occupancy(request: OccupancyQueryRequest) -> OccupancyQueryResponse:
    results: list[OccupancyResponse] = []
    data = query_occupancy(
        request.merchant_ids, request.timestamp, request.arrival_offset_minutes
    )
    for venue, demand in data.items:
        results.append(
            OccupancyResponse(
                merchant_id=venue.merchant_id,
                name=venue.name,
                category=venue.category,
                city=venue.city,
                timestamp=data.timestamp,
                demand=demand,
            )
        )
    return OccupancyQueryResponse(results=results, count=len(results))
