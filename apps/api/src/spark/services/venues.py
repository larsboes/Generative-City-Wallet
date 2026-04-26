import math
import sqlite3
from typing import Iterable

from spark.models.demand import Venue
from spark.repositories.venues import (
    get_venue_row,
    list_venue_rows,
    upsert_venues as repo_upsert_venues,
)
from spark.services.canonicalization import normalize_category


def row_to_venue(row: sqlite3.Row) -> Venue:
    return Venue(
        merchant_id=row["merchant_id"],
        osm_type=row["osm_type"],
        osm_id=row["osm_id"],
        name=row["name"],
        category=row["category"],
        lat=row["lat"],
        lon=row["lon"],
        city=row["city"],
        address=row["address"],
        website=row["website"],
        phone=row["phone"],
        opening_hours=row["opening_hours"],
        source=row["source"],
    )


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_venue(conn: sqlite3.Connection, merchant_id: str) -> Venue | None:
    row = get_venue_row(conn, merchant_id)
    return row_to_venue(row) if row else None


def list_venues(
    conn: sqlite3.Connection,
    category: str | None = None,
    city: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float | None = None,
    limit: int = 100,
) -> list[Venue]:
    categories: list[str] | None = None
    if category:
        categories = [
            normalize_category(part) for part in category.split(",") if part.strip()
        ]
    query_limit = (
        5000 if lat is not None and lon is not None and radius_m is not None else limit
    )
    rows = list_venue_rows(
        conn,
        categories=categories,
        city=city,
        query_limit=query_limit,
    )
    venues = [row_to_venue(row) for row in rows]

    if lat is None or lon is None or radius_m is None:
        return venues

    nearby = [v for v in venues if haversine_m(lat, lon, v.lat, v.lon) <= radius_m]
    return nearby[:limit]


def save_venues(db_path: str, venues: Iterable[dict]) -> int:
    return repo_upsert_venues(db_path, list(venues))
