"""
SQLite connection helper for the Spark backend.
Uses a single file DB for the hackathon — swap for Postgres in prod.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from spark.config import DB_PATH

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _normalize_sqlite_target(db_path: str) -> tuple[str, bool]:
    """Return (target, uri) for sqlite3.connect."""
    if db_path == ":memory:":
        # Use shared in-memory URI so schema/seed/data survive across connections
        # in a single process (tests call init + seed via separate connections).
        return ("file:spark_memdb?mode=memory&cache=shared", True)
    return (db_path, False)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a new SQLite connection with WAL mode and row factory."""
    target, use_uri = _normalize_sqlite_target(db_path or DB_PATH)
    conn = sqlite3.connect(target, uri=use_uri)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database(
    db_path: str | None = None, conn: sqlite3.Connection | None = None
) -> None:
    """Create all tables from schema.sql if they don't exist."""
    owns_connection = conn is None
    if conn is None:
        conn = get_connection(db_path)
    schema = _SCHEMA_PATH.read_text()
    conn.executescript(schema)
    if owns_connection:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


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


def insert_venue_transactions(
    conn: sqlite3.Connection, transactions: list[dict[str, Any]]
) -> int:
    if not transactions:
        return 0
    before = conn.total_changes
    conn.executemany(
        """
        INSERT OR IGNORE INTO venue_transactions (
            transaction_id, merchant_id, category, timestamp, hour_of_day,
            day_of_week, hour_of_week, amount_eur, currency, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                txn["transaction_id"],
                txn["merchant_id"],
                txn["category"],
                txn["timestamp"],
                txn["hour_of_day"],
                txn["day_of_week"],
                txn["hour_of_week"],
                txn["amount_eur"],
                txn.get("currency", "EUR"),
                txn.get("source", "synthetic"),
            )
            for txn in transactions
        ],
    )
    return conn.total_changes - before
