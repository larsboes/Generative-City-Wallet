"""Simulates Payone transaction webhooks for development."""
import random
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parents[2] / "apps" / "api" / "src"))

METHODS = ["contactless", "chip", "apple_pay", "google_pay"]
FLUENTBIT_URL = "http://localhost:8889"
DEFAULT_GRID_CELL = "891f8d7a49bffff"


def _load_merchants() -> list[tuple[str, str, float]]:
    """Pull live merchant IDs + types from the DB. Falls back to empty list."""
    try:
        from spark.db.connection import get_connection
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, type FROM merchants ORDER BY RANDOM() LIMIT 20"
        ).fetchall()
        conn.close()
        avg_by_type = {"cafe": 4.80, "bakery": 3.20, "bar": 7.40, "restaurant": 18.50, "club": 9.00}
        return [(r["id"], r["type"], avg_by_type.get(r["type"], 8.0)) for r in rows]
    except Exception as e:
        print(f"Could not load merchants from DB: {e}")
        return []


def generate_event(merchants: list[tuple[str, str, float]]) -> dict:
    mid, cat, avg_amount = random.choice(merchants)
    amount = round(max(0.50, random.gauss(avg_amount, avg_amount * 0.3)), 2)
    return {
        "merchant_id": mid,
        "amount": amount,
        "currency": "EUR",
        "category": cat,
        "grid_cell": DEFAULT_GRID_CELL,
        "method": random.choice(METHODS),
    }


def run(events_per_minute: int = 30):
    merchants = _load_merchants()
    if not merchants:
        print("No merchants found in DB — run seed_database() first.")
        return

    delay = 60.0 / events_per_minute
    print(f"Loaded {len(merchants)} merchants. Generating ~{events_per_minute} events/min -> {FLUENTBIT_URL}")
    while True:
        event = generate_event(merchants)
        try:
            httpx.post(FLUENTBIT_URL, json=event, timeout=2)
            print(f"  -> {event['merchant_id']} {event['category']} EUR{event['amount']}")
        except httpx.ConnectError:
            print("FluentBit not reachable, retrying...")
        time.sleep(delay + random.uniform(-delay * 0.2, delay * 0.2))


if __name__ == "__main__":
    run()
