from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from spark.db.connection import get_connection, init_database
from spark.domain.interfaces import IVenueRepository


def upsert_venue(conn: sqlite3.Connection, venue: dict[str, Any]) -> None:
    raw_tags = venue.get("raw_tags")
    raw_tags_json = json.dumps(raw_tags, ensure_ascii=False) if raw_tags else None
    conn.execute(
        """
        INSERT INTO venues (
            merchant_id, osm_type, osm_id, name, category, lat, lon, city,
            address, website, phone, opening_hours, source, raw_tags_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(merchant_id) DO UPDATE SET
            osm_type = excluded.osm_type,
            osm_id = excluded.osm_id,
            name = excluded.name,
            category = excluded.category,
            lat = excluded.lat,
            lon = excluded.lon,
            city = excluded.city,
            address = excluded.address,
            website = excluded.website,
            phone = excluded.phone,
            opening_hours = excluded.opening_hours,
            source = excluded.source,
            raw_tags_json = excluded.raw_tags_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            venue["merchant_id"],
            venue.get("osm_type"),
            venue.get("osm_id"),
            venue["name"],
            venue["category"],
            venue["lat"],
            venue["lon"],
            venue.get("city"),
            venue.get("address"),
            venue.get("website"),
            venue.get("phone"),
            venue.get("opening_hours"),
            venue.get("source", "openstreetmap"),
            raw_tags_json,
        ),
    )


def upsert_venues(db_path: str | Path | None, venues: list[dict[str, Any]]) -> int:
    init_database(str(db_path) if db_path else None)
    conn = get_connection(str(db_path) if db_path else None)
    try:
        for venue in venues:
            upsert_venue(conn, venue)
        conn.commit()
    finally:
        conn.close()
    return len(venues)


def get_venue_row(conn: sqlite3.Connection, merchant_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM venues WHERE merchant_id = ?", (merchant_id,)
    ).fetchone()


def list_venue_rows(
    conn: sqlite3.Connection,
    *,
    categories: list[str] | None = None,
    city: str | None = None,
    query_limit: int = 100,
) -> list[sqlite3.Row]:
    clauses: list[str] = []
    params: list[object] = []

    if categories:
        placeholders = ",".join("?" for _ in categories)
        clauses.append(f"category IN ({placeholders})")
        params.extend(categories)

    if city:
        clauses.append("LOWER(city) = LOWER(?)")
        params.append(city)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    bounded_limit = max(1, min(query_limit, 5000))
    return conn.execute(
        f"SELECT * FROM venues {where} ORDER BY name LIMIT ?",
        (*params, bounded_limit),
    ).fetchall()


class VenueRepository(IVenueRepository):
    """Concrete IVenueRepository backed by SQLite, wrapping existing functions."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path

    def get_venue_row(self, merchant_id: str) -> sqlite3.Row | None:
        conn = get_connection(self.db_path)
        try:
            return get_venue_row(conn, merchant_id)
        finally:
            conn.close()

    def list_venue_rows(
        self,
        *,
        categories: list[str] | None = None,
        city: str | None = None,
        query_limit: int = 100,
    ) -> list[sqlite3.Row]:
        conn = get_connection(self.db_path)
        try:
            return list_venue_rows(
                conn, categories=categories, city=city, query_limit=query_limit
            )
        finally:
            conn.close()
