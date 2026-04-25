import json
import os
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(os.getenv("OCCUPANCY_DB_PATH", "data/occupancy.db"))


def get_db_path(db_path: str | Path | None = None) -> Path:
    return Path(db_path) if db_path else DEFAULT_DB_PATH


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = get_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS venues (
                merchant_id TEXT PRIMARY KEY,
                osm_type TEXT,
                osm_id TEXT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                city TEXT,
                address TEXT,
                website TEXT,
                phone TEXT,
                opening_hours TEXT,
                source TEXT NOT NULL DEFAULT 'openstreetmap',
                raw_tags_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_venues_category ON venues(category);
            CREATE INDEX IF NOT EXISTS idx_venues_city ON venues(city);
            CREATE INDEX IF NOT EXISTS idx_venues_lat_lon ON venues(lat, lon);

            CREATE TABLE IF NOT EXISTS transaction_baselines (
                merchant_id TEXT NOT NULL,
                hour_of_week INTEGER NOT NULL CHECK(hour_of_week BETWEEN 0 AND 167),
                historical_avg_txn_rate REAL NOT NULL CHECK(historical_avg_txn_rate >= 0),
                sample_count INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'synthetic',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (merchant_id, hour_of_week),
                FOREIGN KEY (merchant_id) REFERENCES venues(merchant_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS current_signals (
                merchant_id TEXT PRIMARY KEY,
                current_txn_rate REAL NOT NULL CHECK(current_txn_rate >= 0),
                observed_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'demo_override',
                FOREIGN KEY (merchant_id) REFERENCES venues(merchant_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS payone_transactions (
                transaction_id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL,
                category TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                hour_of_day INTEGER NOT NULL CHECK(hour_of_day BETWEEN 0 AND 23),
                day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
                hour_of_week INTEGER NOT NULL CHECK(hour_of_week BETWEEN 0 AND 167),
                amount_eur REAL NOT NULL CHECK(amount_eur >= 0),
                currency TEXT NOT NULL DEFAULT 'EUR',
                source TEXT NOT NULL DEFAULT 'synthetic',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES venues(merchant_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_payone_merchant_timestamp
                ON payone_transactions(merchant_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_payone_merchant_category_timestamp
                ON payone_transactions(merchant_id, category, timestamp);
            CREATE INDEX IF NOT EXISTS idx_payone_merchant_hour_of_week
                ON payone_transactions(merchant_id, hour_of_week, timestamp);
            """
        )


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
    init_db(db_path)
    with connect(db_path) as conn:
        for venue in venues:
            upsert_venue(conn, venue)
        conn.commit()
    return len(venues)


def insert_transactions(conn: sqlite3.Connection, transactions: list[dict[str, Any]]) -> int:
    if not transactions:
        return 0

    before = conn.total_changes
    conn.executemany(
        """
        INSERT OR IGNORE INTO payone_transactions (
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
