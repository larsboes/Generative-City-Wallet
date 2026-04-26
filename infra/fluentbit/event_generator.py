"""Simulates Payone transaction webhooks for development."""
import random
import time

import httpx

MERCHANTS = [
    ("MERCHANT_001", "cafe", 4.80),
    ("MERCHANT_002", "bakery", 3.20),
    ("MERCHANT_003", "bar", 7.40),
    ("MERCHANT_004", "restaurant", 18.50),
    ("MERCHANT_005", "club", 9.00),
]
METHODS = ["contactless", "chip", "apple_pay", "google_pay"]
FLUENTBIT_URL = "http://localhost:8888"
DEFAULT_GRID_CELL = "891f8d7a49bffff"


def generate_event() -> dict:
    mid, cat, avg_amount = random.choice(MERCHANTS)
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
    delay = 60.0 / events_per_minute
    print(f"Generating ~{events_per_minute} events/min -> {FLUENTBIT_URL}")
    while True:
        event = generate_event()
        try:
            httpx.post(FLUENTBIT_URL, json=event, timeout=2)
            print(f"  -> {event['merchant_id']} {event['category']} EUR{event['amount']}")
        except httpx.ConnectError:
            print("FluentBit not reachable, retrying...")
        time.sleep(delay + random.uniform(-delay * 0.2, delay * 0.2))


if __name__ == "__main__":
    run()
