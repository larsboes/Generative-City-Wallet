"""
Database seeder — loads Munich OSM fixture as demo data.
"""

from __future__ import annotations

import json
from pathlib import Path

from spark.db.connection import get_connection, init_database
from spark.repositories.venues import upsert_venues
from spark.services.location_cells import latlon_to_h3
from spark.services.transaction_generation import generate_history

_FIXTURE_PATH = Path(__file__).parents[5] / "resources" / "mock_venues_munich.json"

EXCLUDED_MERCHANT_NAME_TOKENS = {
    "casino",
    "sportcasino",
    "sportsbet",
    "sportsbook",
    "bookmaker",
    "betting",
    "gambling",
}


def seed_database(db_path: str | None = None) -> None:
    """Initialize DB schema and seed Munich OSM demo data."""
    init_database(db_path=db_path)

    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM venue_transactions")
        conn.execute("DELETE FROM current_signals")
        conn.execute("DELETE FROM transaction_baselines")
        conn.execute("DELETE FROM venues")
        conn.execute("DELETE FROM payone_transactions")
        conn.execute("DELETE FROM merchant_coupons")
        conn.execute("DELETE FROM merchants")
        conn.commit()
    finally:
        conn.close()

    fixture_path = _FIXTURE_PATH
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Munich fixture not found at {fixture_path}. "
            "Run from repo root or check resources/mock_venues_munich.json."
        )

    with fixture_path.open(encoding="utf-8") as f:
        venues = json.load(f)

    filtered = [
        v
        for v in venues
        if not any(
            t in str(v.get("name") or "").lower() for t in EXCLUDED_MERCHANT_NAME_TOKENS
        )
    ]
    imported = upsert_venues(db_path, filtered)

    history = generate_history(
        merchant_ids=None,
        category=None,
        city="München",
        limit=5000,
        days=28,
        start=None,
        end=None,
        seed=42,
    )

    conn = get_connection(db_path)
    try:
        venue_rows = conn.execute(
            "SELECT merchant_id, name, category, lat, lon, COALESCE(address, '') AS address FROM venues"
        ).fetchall()
        conn.executemany(
            "INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell) VALUES (?,?,?,?,?,?,?)",
            [
                (
                    r["merchant_id"],
                    r["name"],
                    r["category"],
                    r["lat"],
                    r["lon"],
                    r["address"],
                    latlon_to_h3(float(r["lat"]), float(r["lon"])),
                )
                for r in venue_rows
            ],
        )
        conn.execute(
            """
            INSERT INTO payone_transactions (
                merchant_id, merchant_type, timestamp, hour_of_day,
                day_of_week, hour_of_week, txn_count, total_volume_eur
            )
            SELECT
                vt.merchant_id,
                vt.category AS merchant_type,
                strftime('%Y-%m-%dT%H:00:00', vt.timestamp) AS timestamp,
                CAST(strftime('%H', vt.timestamp) AS INTEGER) AS hour_of_day,
                (CAST(strftime('%w', vt.timestamp) AS INTEGER) + 6) % 7 AS day_of_week,
                (((CAST(strftime('%w', vt.timestamp) AS INTEGER) + 6) % 7) * 24)
                    + CAST(strftime('%H', vt.timestamp) AS INTEGER) AS hour_of_week,
                COUNT(*) AS txn_count,
                ROUND(SUM(vt.amount_eur), 2) AS total_volume_eur
            FROM venue_transactions vt
            GROUP BY vt.merchant_id, strftime('%Y-%m-%d %H', vt.timestamp)
            """
        )
        conn.commit()
        merchants = conn.execute("SELECT COUNT(*) FROM merchants").fetchone()[0]
    finally:
        conn.close()

    print(
        f"✅ Seeded {imported} Munich venues → {merchants} merchants, {history.inserted} transactions"
    )


if __name__ == "__main__":
    seed_database()
