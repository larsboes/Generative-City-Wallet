from datetime import datetime, timedelta
from hashlib import sha256
import math
import random
import sqlite3
from typing import Iterable

from spark.models.transactions import Venue
from spark.repositories.transactions import insert_venue_transactions
from spark.services.canonicalization import ensure_utc, hour_of_week, normalize_category
from spark.services.signals import (
    BASE_HOURLY_RATES,
    DAY_MULTIPLIERS,
)
from spark.services.venues import get_venue, list_venues


CATEGORY_AVG_TICKET_EUR: dict[str, float] = {
    "bakery": 4.20,
    "cafe": 7.50,
    "fast_food": 10.50,
    "restaurant": 24.00,
    "bar": 12.00,
    "pub": 13.00,
    "biergarten": 18.00,
    "nightclub": 16.00,
    "retail": 32.00,
}

def floor_hour(dt: datetime) -> datetime:
    utc = ensure_utc(dt)
    return utc.replace(minute=0, second=0, microsecond=0)


def iter_hours(start: datetime, end: datetime) -> Iterable[datetime]:
    current = floor_hour(start)
    end_hour = floor_hour(end)
    while current < end_hour:
        yield current
        current += timedelta(hours=1)


def expected_txn_rate(category: str, dt: datetime) -> float:
    category = normalize_category(category)
    base = BASE_HOURLY_RATES.get(category, BASE_HOURLY_RATES["restaurant"])
    multipliers = DAY_MULTIPLIERS.get(category, DAY_MULTIPLIERS["restaurant"])
    return round(base[dt.hour] * multipliers[dt.weekday()], 3)


def _stable_seed(*parts: object) -> int:
    digest = sha256("|".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _rng_for(seed: int | None, *parts: object) -> random.Random:
    return random.Random(_stable_seed(seed if seed is not None else "default", *parts))


def sample_transaction_count(expected_rate: float, rng: random.Random) -> int:
    if expected_rate <= 0:
        return 0
    if expected_rate < 30:
        threshold = math.exp(-expected_rate)
        product = 1.0
        count = 0
        while product > threshold:
            count += 1
            product *= rng.random()
        return max(0, count - 1)
    return max(0, int(round(rng.gauss(expected_rate, math.sqrt(expected_rate)))))


def amount_for_category(
    category: str, dt: datetime, txn_rate: float, rng: random.Random
) -> float:
    category = normalize_category(category)
    base_ticket = CATEGORY_AVG_TICKET_EUR.get(category, 12.00)
    base_rates = BASE_HOURLY_RATES.get(category, BASE_HOURLY_RATES["restaurant"])
    multipliers = DAY_MULTIPLIERS.get(category, DAY_MULTIPLIERS["restaurant"])
    peak_rate = max(base_rates) * max(multipliers)
    demand_ratio = 0.0 if peak_rate <= 0 else min(1.0, txn_rate / peak_rate)

    demand_price_lift = 0.92 + 0.18 * demand_ratio
    evening_lift = (
        1.08
        if category in {"restaurant", "bar", "pub", "biergarten", "nightclub"}
        and dt.hour >= 18
        else 1.0
    )
    weekend_lift = 1.05 if dt.weekday() >= 5 else 1.0
    expected_ticket = base_ticket * demand_price_lift * evening_lift * weekend_lift

    amount = rng.gauss(expected_ticket, expected_ticket * 0.28)
    return round(max(0.80, amount), 2)


def build_transaction(
    venue: Venue,
    timestamp: datetime,
    amount_eur: float,
    source: str,
    ordinal: int,
    seed: int | None,
) -> dict:
    timestamp = ensure_utc(timestamp)
    transaction_id = sha256(
        f"{source}|{seed}|{venue.merchant_id}|{timestamp.isoformat()}|{ordinal}".encode(
            "utf-8"
        )
    ).hexdigest()
    return {
        "transaction_id": transaction_id,
        "merchant_id": venue.merchant_id,
        "category": normalize_category(venue.category),
        "timestamp": timestamp.isoformat(),
        "hour_of_day": timestamp.hour,
        "day_of_week": timestamp.weekday(),
        "hour_of_week": hour_of_week(timestamp),
        "amount_eur": amount_eur,
        "currency": "EUR",
        "source": source,
    }


def generate_transactions_for_hour(
    venue: Venue,
    hour_start: datetime,
    source: str,
    seed: int | None = None,
) -> list[dict]:
    hour_start = floor_hour(hour_start)
    txn_rate = expected_txn_rate(venue.category, hour_start)
    rng = _rng_for(seed, venue.merchant_id, hour_start.isoformat(), source)
    txn_count = sample_transaction_count(txn_rate, rng)
    transactions = []
    for ordinal in range(txn_count):
        offset_seconds = rng.randint(0, 3599)
        timestamp = hour_start + timedelta(seconds=offset_seconds)
        amount = amount_for_category(venue.category, hour_start, txn_rate, rng)
        transactions.append(
            build_transaction(venue, timestamp, amount, source, ordinal, seed)
        )
    return transactions


def generate_history_for_venues(
    conn: sqlite3.Connection,
    venues: list[Venue],
    start: datetime,
    end: datetime,
    seed: int | None = None,
) -> int:
    inserted = 0
    for venue in venues:
        batch: list[dict] = []
        for hour_start in iter_hours(start, end):
            batch.extend(
                generate_transactions_for_hour(
                    venue, hour_start, "synthetic_history", seed
                )
            )
            if len(batch) >= 1000:
                inserted += insert_venue_transactions(conn, batch)
                batch = []
        inserted += insert_venue_transactions(conn, batch)
    conn.commit()
    return inserted


def generate_last_hour_update(
    conn: sqlite3.Connection,
    venues: list[Venue],
    timestamp: datetime,
    seed: int | None = None,
) -> tuple[int, datetime, datetime]:
    window_end = floor_hour(timestamp)
    window_start = window_end - timedelta(hours=1)
    transactions: list[dict] = []
    for venue in venues:
        transactions.extend(
            generate_transactions_for_hour(
                venue, window_start, "synthetic_live_update", seed
            )
        )
    inserted = insert_venue_transactions(conn, transactions)
    conn.commit()
    return inserted, window_start, window_end


def resolve_venues(
    conn: sqlite3.Connection,
    merchant_ids: list[str] | None = None,
    category: str | None = None,
    city: str | None = None,
    limit: int = 100,
) -> list[Venue]:
    if merchant_ids:
        venues = [venue for mid in merchant_ids if (venue := get_venue(conn, mid))]
        return venues[:limit]
    return list_venues(conn, category=category, city=city, limit=limit)
