from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from spark.db.connection import get_connection, init_database


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

