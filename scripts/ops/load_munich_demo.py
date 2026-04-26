from __future__ import annotations

import argparse
import json
from pathlib import Path

from spark.db.connection import get_connection, init_database
from spark.repositories.venues import upsert_venues
from spark.services.location_cells import is_valid_h3, latlon_to_h3
from spark.services.transaction_generation import generate_history

EXCLUDED_MERCHANT_NAME_TOKENS = {
    "casino",
    "sportcasino",
    "sportsbet",
    "sportsbook",
    "bookmaker",
    "betting",
    "gambling",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset DB demo data and load Munich fixture into both pipelines."
    )
    parser.add_argument(
        "--fixture",
        default="resources/mock_venues_munich.json",
        help="Path to the Munich venues fixture JSON file.",
    )
    parser.add_argument(
        "--city",
        default="München",
        help="City filter used for synthetic history generation.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=28,
        help="How many days of synthetic history to generate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic synthetic history.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")

    init_database()

    # 1) Reset both the newer venue pipeline and legacy merchant/payone pipeline.
    conn = get_connection()
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

    # 2) Import Munich venues.
    with fixture_path.open(encoding="utf-8") as handle:
        venues = json.load(handle)
    filtered_venues = [
        venue
        for venue in venues
        if not any(
            token in str(venue.get("name") or "").lower()
            for token in EXCLUDED_MERCHANT_NAME_TOKENS
        )
    ]
    imported_venues = upsert_venues(None, filtered_venues)

    # 3) Generate venue transactions from imported venues.
    history = generate_history(
        merchant_ids=None,
        category=None,
        city=args.city,
        limit=5000,
        days=args.days,
        start=None,
        end=None,
        seed=args.seed,
    )

    # 4) Build legacy merchant/payone tables from venue pipeline data.
    conn = get_connection()
    try:
        venue_rows = conn.execute(
            """
            SELECT merchant_id, name, category, lat, lon, COALESCE(address, '') AS address
            FROM venues
            """
        ).fetchall()
        conn.executemany(
            """
            INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["merchant_id"],
                    row["name"],
                    row["category"],
                    row["lat"],
                    row["lon"],
                    row["address"],
                    latlon_to_h3(float(row["lat"]), float(row["lon"])),
                )
                for row in venue_rows
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

        row_counts = {
            "venues": conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0],
            "venue_transactions": conn.execute(
                "SELECT COUNT(*) FROM venue_transactions"
            ).fetchone()[0],
            "merchants": conn.execute("SELECT COUNT(*) FROM merchants").fetchone()[0],
            "payone_transactions": conn.execute(
                "SELECT COUNT(*) FROM payone_transactions"
            ).fetchone()[0],
        }
        legacy_patterns = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM merchants
            WHERE substr(grid_cell, 1, 3) IN ('STR', 'MUC')
            """
        ).fetchone()
        invalid_h3 = conn.execute("SELECT grid_cell FROM merchants").fetchall()
        invalid_cells = [
            row["grid_cell"] for row in invalid_h3 if not is_valid_h3(row["grid_cell"])
        ]
    finally:
        conn.close()

    if legacy_patterns and int(legacy_patterns["c"]) > 0:
        raise RuntimeError("Legacy non-H3 grid_cell prefixes detected after load_munich_demo run.")
    if invalid_cells:
        raise RuntimeError(f"Invalid H3 grid_cell values detected: {invalid_cells[:5]}")

    print("Munich demo data loaded.")
    print(f"fixture={fixture_path}")
    print(f"imported_venues={imported_venues}")
    print(f"generated_transactions={history.inserted}")
    print(f"history_venue_count={history.venue_count}")
    print(f"history_window_start={history.start.isoformat()}")
    print(f"history_window_end={history.end.isoformat()}")
    for key, value in row_counts.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
