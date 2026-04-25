"""
Synthetic Payone data generator + merchant seeder.
Produces 28 days of hourly transaction buckets for 5 Stuttgart demo merchants.
"""

import json
import numpy as np
from datetime import datetime, timedelta

from spark.db.connection import get_connection, init_database

# ── Base rate profiles (transactions per hour, indexed by hour 0-23) ───────────
# These are "typical Friday" shapes — calibrated to Stuttgart venue sizes.

BASE_HOURLY_RATES: dict[str, list[float]] = {
    "cafe": [
        0,
        0,
        0,
        0,
        0,
        0,
        0.5,
        3,
        9,
        7,
        5,
        4,
        11,
        13,
        9,
        6,
        5,
        4,
        3,
        2,
        1,
        0,
        0,
        0,
    ],
    "bakery": [
        0,
        0,
        0,
        0,
        0,
        0,
        0.5,
        8,
        12,
        9,
        6,
        4,
        8,
        7,
        4,
        3,
        2,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
    ],
    "restaurant": [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        2,
        3,
        5,
        13,
        15,
        8,
        3,
        4,
        8,
        16,
        14,
        6,
        2,
        1,
        0,
    ],
    "bar": [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        2,
        3,
        2,
        1,
        1,
        2,
        3,
        6,
        10,
        15,
        18,
        16,
        10,
    ],
    "club": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 3, 8, 14, 20, 24],
    "retail": [0, 0, 0, 0, 0, 0, 0, 0, 1, 3, 6, 8, 10, 9, 7, 6, 5, 4, 2, 1, 0, 0, 0, 0],
}

DAY_MULTIPLIERS: dict[str, list[float]] = {
    "cafe": [0.85, 0.90, 0.90, 0.88, 1.0, 1.25, 1.15],
    "bakery": [0.90, 0.88, 0.88, 0.88, 1.0, 1.30, 1.20],
    "restaurant": [0.80, 0.82, 0.85, 0.88, 1.10, 1.35, 1.25],
    "bar": [0.70, 0.72, 0.75, 0.85, 1.20, 1.60, 1.40],
    "club": [0.30, 0.30, 0.40, 0.60, 1.50, 2.00, 1.70],
    "retail": [0.90, 0.92, 0.92, 0.92, 1.05, 1.40, 0.80],
}

AVG_TXN_VALUES: dict[str, float] = {
    "cafe": 4.80,
    "bakery": 3.20,
    "restaurant": 18.50,
    "bar": 7.40,
    "club": 9.00,
    "retail": 28.00,
}

# ── Demo merchants ─────────────────────────────────────────────────────────────

DEMO_MERCHANTS = [
    {
        "id": "MERCHANT_001",
        "name": "Café Römer",
        "type": "cafe",
        "lat": 48.7758,
        "lon": 9.1829,
        "address": "Königstraße 40, 70173 Stuttgart",
        "grid_cell": "STR-MITTE-047",
    },
    {
        "id": "MERCHANT_002",
        "name": "Bäckerei Wolf",
        "type": "bakery",
        "lat": 48.7771,
        "lon": 9.1793,
        "address": "Marktplatz 6, 70173 Stuttgart",
        "grid_cell": "STR-MITTE-047",
    },
    {
        "id": "MERCHANT_003",
        "name": "Bar Unter",
        "type": "bar",
        "lat": 48.7748,
        "lon": 9.1795,
        "address": "Eberhardstraße 35, 70173 Stuttgart",
        "grid_cell": "STR-MITTE-047",
    },
    {
        "id": "MERCHANT_004",
        "name": "Markthalle Bistro",
        "type": "restaurant",
        "lat": 48.7780,
        "lon": 9.1812,
        "address": "Dorotheenstraße 4, 70173 Stuttgart",
        "grid_cell": "STR-MITTE-047",
    },
    {
        "id": "MERCHANT_005",
        "name": "Club Schräglage",
        "type": "club",
        "lat": 48.7731,
        "lon": 9.1820,
        "address": "Hirschstraße 20, 70173 Stuttgart",
        "grid_cell": "STR-MITTE-047",
    },
]

# ── Demo coupons to pre-seed ──────────────────────────────────────────────────

DEMO_COUPONS = [
    {
        "merchant_id": "MERCHANT_001",
        "coupon_type": "FLASH",
        "config": json.dumps({"discount_pct": 15, "duration_minutes": 20}),
    },
    {
        "merchant_id": "MERCHANT_003",
        "coupon_type": "MILESTONE",
        "config": json.dumps(
            {
                "target_guests": 50,
                "reward_type": "cover_refund",
                "reward_value": 8.0,
                "reward_count": 20,
            }
        ),
    },
    {
        "merchant_id": "MERCHANT_004",
        "coupon_type": "FLASH",
        "config": json.dumps({"discount_pct": 20, "duration_minutes": 30}),
    },
    {
        "merchant_id": "MERCHANT_002",
        "coupon_type": "FLASH",
        "config": json.dumps({"discount_pct": 10, "duration_minutes": 20}),
    },
    {
        "merchant_id": "MERCHANT_005",
        "coupon_type": "TIME_BOUND",
        "config": json.dumps({"discount_pct": 20, "valid_until_time": "23:00"}),
    },
]


def generate_payone_history(
    merchant_id: str,
    merchant_type: str,
    days: int = 28,
    seed: int | None = None,
) -> list[dict]:
    """Generate 28 days of synthetic Payone transaction history (hourly buckets)."""
    if seed is not None:
        np.random.seed(seed)

    base_rates = BASE_HOURLY_RATES[merchant_type]
    day_mults = DAY_MULTIPLIERS[merchant_type]

    records: list[dict] = []
    start = datetime.now() - timedelta(days=days)

    for day_offset in range(days):
        dt = start + timedelta(days=day_offset)
        dow = dt.weekday()
        day_mult = day_mults[dow]

        for hour in range(24):
            base = base_rates[hour] * day_mult

            if base < 0.01:
                txn_count = 0
            else:
                rate_with_noise = max(0, base * (1 + np.random.normal(0, 0.15)))
                txn_count = int(np.random.poisson(rate_with_noise))

            if txn_count > 0:
                avg = AVG_TXN_VALUES.get(merchant_type, 10.0)
                total_volume = sum(
                    max(0.5, np.random.normal(avg, avg * 0.3)) for _ in range(txn_count)
                )
            else:
                total_volume = 0.0

            records.append(
                {
                    "merchant_id": merchant_id,
                    "merchant_type": merchant_type,
                    "timestamp": dt.replace(hour=hour, minute=0, second=0).isoformat(),
                    "hour_of_day": hour,
                    "day_of_week": dow,
                    "hour_of_week": dow * 24 + hour,
                    "txn_count": txn_count,
                    "total_volume_eur": round(total_volume, 2),
                }
            )

    return records


def seed_database(db_path: str | None = None) -> None:
    """Initialize DB schema and seed all demo data."""
    conn = get_connection(db_path)
    init_database(conn=conn)

    # Clear old data
    conn.execute("DELETE FROM payone_transactions")
    conn.execute("DELETE FROM merchant_coupons")
    conn.execute("DELETE FROM merchants")

    # Seed merchants
    for m in DEMO_MERCHANTS:
        conn.execute(
            "INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                m["id"],
                m["name"],
                m["type"],
                m["lat"],
                m["lon"],
                m["address"],
                m["grid_cell"],
            ),
        )

    # Seed transaction history
    total_records = 0
    for m in DEMO_MERCHANTS:
        records = generate_payone_history(
            m["id"],
            m["type"],
            days=28,
            seed=hash(m["id"]) % (2**31),
        )
        conn.executemany(
            "INSERT INTO payone_transactions VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    r["merchant_id"],
                    r["merchant_type"],
                    r["timestamp"],
                    r["hour_of_day"],
                    r["day_of_week"],
                    r["hour_of_week"],
                    r["txn_count"],
                    r["total_volume_eur"],
                )
                for r in records
            ],
        )
        total_records += len(records)

    # Seed coupons
    now = datetime.now().isoformat()
    for c in DEMO_COUPONS:
        conn.execute(
            "INSERT INTO merchant_coupons (merchant_id, coupon_type, config, active, created_at) VALUES (?, ?, ?, 1, ?)",
            (c["merchant_id"], c["coupon_type"], c["config"], now),
        )

    conn.commit()
    conn.close()
    print(
        f"✅ Seeded {len(DEMO_MERCHANTS)} merchants, {total_records} transaction records, {len(DEMO_COUPONS)} coupons"
    )


if __name__ == "__main__":
    seed_database()
