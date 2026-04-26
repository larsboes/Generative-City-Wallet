import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_BASE = "http://127.0.0.1:8000"
CITY = "München"
HISTORY_DAYS = 28
ARRIVAL_OFFSET_MINUTES = 10
TEST_LIMIT = 10
HISTORY_SEED = 42
LIVE_SEED = 43
OCCUPANCY_CATEGORY_FILTER = "bar,pub,biergarten,nightclub"
VERIFICATION_TRANSACTION_LIMIT = 100
VERIFICATION_HISTORY_DAY_LIMIT = 30

# Pin the test to an hour boundary so the API's rolling "current hour" window
# exactly matches the generated live-update window.
TEST_TIMESTAMP = datetime.now(timezone.utc).replace(
    minute=0, second=0, microsecond=0
) + timedelta(hours=2)
CURRENT_WINDOW_START = TEST_TIMESTAMP - timedelta(hours=1)
HISTORY_START = TEST_TIMESTAMP - timedelta(days=HISTORY_DAYS)
HISTORY_END = CURRENT_WINDOW_START

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH_RAW = (
    os.getenv("SPARK_DB_PATH") or os.getenv("OCCUPANCY_DB_PATH") or "data/spark.db"
)
DB_PATH = Path(DB_PATH_RAW)
if DB_PATH_RAW != ":memory:" and not DB_PATH.is_absolute():
    DB_PATH = REPO_ROOT / DB_PATH
SCHEMA_PATH = REPO_ROOT / "apps" / "api" / "src" / "spark" / "db" / "schema.sql"
VENUE_FIXTURE_PATH = REPO_ROOT / "data" / "munich_venues.json"

OCCUPANCY_CALIBRATION = {
    "bar": (0.5, 22.0),
    "pub": (0.5, 22.0),
    "biergarten": (0.5, 28.0),
    "nightclub": (0.0, 35.0),
}
BASE_HOURLY_RATES = {
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
    "pub": [
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
    "biergarten": [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        13,
        20,
        27,
        32,
        35,
        37,
        43,
        54,
        64,
        72,
        72,
        59,
        39,
        26,
        4,
    ],
    "nightclub": [
        25,
        20,
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
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        3,
        8,
        14,
        20,
        24,
    ],
}
DAY_MULTIPLIERS = {
    "bar": [0.70, 0.72, 0.75, 0.85, 1.20, 1.60, 1.40],
    "pub": [0.70, 0.72, 0.75, 0.85, 1.20, 1.60, 1.40],
    "biergarten": [0.75, 0.84, 0.92, 0.99, 1.12, 1.26, 1.12],
    "nightclub": [0.30, 0.30, 0.40, 0.60, 1.50, 2.00, 1.70],
}


def utc_iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def parse_api_datetime(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def api_url(path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return url


def print_json(title, data):
    print(title)
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    print("-" * 40)


def send_request(url, method="GET", data=None, preview_chars=500):
    headers = {}
    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            print(f"[{method}] {url} -> {status}")
            try:
                parsed = json.loads(body)
                if preview_chars:
                    preview = json.dumps(parsed, indent=2, ensure_ascii=False)
                    print(
                        preview[:preview_chars]
                        + ("...\n" if len(preview) > preview_chars else "\n")
                    )
                print("-" * 40)
                return parsed
            except json.JSONDecodeError:
                if preview_chars:
                    print(body[:preview_chars] + "\n")
                print("-" * 40)
                return None
    except urllib.error.HTTPError as e:
        print(f"[{method}] {url} -> {e.code}")
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(body)
    except Exception as e:
        print(f"[{method}] {url} -> ERROR: {e}")

    print("-" * 40)
    return None


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def hour_of_week(dt):
    return dt.weekday() * 24 + dt.hour


def normalize_category(category):
    normalized = (
        (category or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    )
    return {"club": "nightclub"}.get(normalized, normalized)


def fallback_historical_rate(category, dt):
    category = normalize_category(category)
    base = BASE_HOURLY_RATES.get(category)
    multipliers = DAY_MULTIPLIERS.get(category)
    if not base or not multipliers:
        return None
    return round(base[dt.hour] * multipliers[dt.weekday()], 3)


def parse_category_filter(category_filter):
    return [
        normalize_category(part) for part in category_filter.split(",") if part.strip()
    ]


def count_matching_venues(conn):
    categories = parse_category_filter(OCCUPANCY_CATEGORY_FILTER)
    placeholders = ",".join("?" for _ in categories)
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS venue_count
        FROM venues
        WHERE LOWER(city) = LOWER(?)
          AND category IN ({placeholders})
        """,
        (CITY, *categories),
    ).fetchone()
    return int(row["venue_count"])


def upsert_fixture_venues(conn, venues):
    for venue in venues:
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
                normalize_category(venue["category"]),
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
    conn.commit()


def ensure_test_venues():
    categories = set(parse_category_filter(OCCUPANCY_CATEGORY_FILTER))
    with connect_db() as conn:
        init_schema(conn)
        existing_count = count_matching_venues(conn)
        if existing_count:
            print(f"Found {existing_count} matching venues in {DB_PATH}")
            print("-" * 40)
            return

        if not VENUE_FIXTURE_PATH.exists():
            print(f"Venue fixture not found: {VENUE_FIXTURE_PATH}")
            print("-" * 40)
            return

        fixtures = json.loads(VENUE_FIXTURE_PATH.read_text(encoding="utf-8"))
        matching = [
            venue
            for venue in fixtures
            if venue.get("city", "").casefold() == CITY.casefold()
            and normalize_category(venue.get("category")) in categories
        ]
        upsert_fixture_venues(conn, matching)
        print(f"Seeded {len(matching)} matching venues from {VENUE_FIXTURE_PATH}")
        print("-" * 40)


def infer_occupancy_pct(category, txn_rate):
    calibration = OCCUPANCY_CALIBRATION.get(normalize_category(category))
    if not calibration:
        return None

    empty_rate, full_rate = calibration
    occupancy = (txn_rate - empty_rate) / (full_rate - empty_rate)
    return round(max(0.0, min(1.0, occupancy)), 3)


def historical_day_samples(conn, merchant_id, target_dt, before_dt):
    rows = conn.execute(
        """
        SELECT
            substr(timestamp, 1, 10) AS day,
            COUNT(*) AS transaction_count,
            ROUND(COALESCE(SUM(amount_eur), 0), 2) AS total_revenue_eur,
            MIN(timestamp) AS first_transaction_at,
            MAX(timestamp) AS last_transaction_at
        FROM venue_transactions
        WHERE merchant_id = ?
          AND hour_of_week = ?
          AND timestamp < ?
        GROUP BY substr(timestamp, 1, 10)
        ORDER BY day DESC
        """,
        (merchant_id, hour_of_week(target_dt), utc_iso(before_dt)),
    ).fetchall()
    return [dict(row) for row in rows]


def current_window_summary(conn, merchant_id, start, end):
    summary = conn.execute(
        """
        SELECT COUNT(*) AS transaction_count, ROUND(COALESCE(SUM(amount_eur), 0), 2) AS total_revenue_eur
        FROM venue_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        """,
        (merchant_id, utc_iso(start), utc_iso(end)),
    ).fetchone()

    source_rows = conn.execute(
        """
        SELECT source, COUNT(*) AS transaction_count, ROUND(COALESCE(SUM(amount_eur), 0), 2) AS total_revenue_eur
        FROM venue_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        GROUP BY source
        ORDER BY source
        """,
        (merchant_id, utc_iso(start), utc_iso(end)),
    ).fetchall()

    sample_rows = conn.execute(
        """
        SELECT transaction_id, timestamp, amount_eur, source
        FROM venue_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        ORDER BY timestamp
        LIMIT ?
        """,
        (merchant_id, utc_iso(start), utc_iso(end), VERIFICATION_TRANSACTION_LIMIT),
    ).fetchall()

    return {
        "window_start": utc_iso(start),
        "window_end": utc_iso(end),
        "transaction_count": int(summary["transaction_count"]),
        "total_revenue_eur": float(summary["total_revenue_eur"]),
        "source_breakdown": [dict(row) for row in source_rows],
        "sample_transactions": [dict(row) for row in sample_rows],
        "sample_limit": VERIFICATION_TRANSACTION_LIMIT,
    }


def summarize_historical_samples(samples):
    counts = [int(sample["transaction_count"]) for sample in samples]
    avg = round(sum(counts) / len(counts), 3) if counts else None
    return {
        "sample_count": len(samples),
        "avg_transaction_count": avg,
        "daily_samples": samples[:VERIFICATION_HISTORY_DAY_LIMIT],
        "omitted_daily_sample_count": max(
            0, len(samples) - VERIFICATION_HISTORY_DAY_LIMIT
        ),
    }


def approx_equal(left, right, tolerance=0.001):
    if left is None or right is None:
        return left is right
    return abs(float(left) - float(right)) <= tolerance


def build_forecast_verification_bundle(venue, occupancy_response):
    forecast_dt = parse_api_datetime(occupancy_response["timestamp"])
    current_window_start = forecast_dt - timedelta(hours=1)
    arrival_dt = forecast_dt + timedelta(minutes=ARRIVAL_OFFSET_MINUTES)
    demand = occupancy_response["demand"]
    merchant_id = venue["merchant_id"]

    with connect_db() as conn:
        current_window = current_window_summary(
            conn, merchant_id, current_window_start, forecast_dt
        )
        current_history_samples = historical_day_samples(
            conn, merchant_id, current_window_start, current_window_start
        )
        arrival_history_samples = historical_day_samples(
            conn, merchant_id, arrival_dt, arrival_dt
        )

    current_history = summarize_historical_samples(current_history_samples)
    arrival_history = summarize_historical_samples(arrival_history_samples)
    current_history_avg = current_history["avg_transaction_count"]
    current_history_used_fallback = current_history_avg is None
    if current_history_avg is None:
        current_history_avg = fallback_historical_rate(
            venue["category"], current_window_start
        )
    arrival_history_avg = arrival_history["avg_transaction_count"]
    arrival_history_used_fallback = arrival_history_avg is None
    if arrival_history_avg is None:
        arrival_history_avg = fallback_historical_rate(venue["category"], arrival_dt)
    current_rate = float(current_window["transaction_count"])
    current_occupancy = infer_occupancy_pct(venue["category"], current_rate)
    arrival_historical_occupancy = (
        infer_occupancy_pct(venue["category"], arrival_history_avg)
        if arrival_history_avg is not None
        else None
    )
    recomputed_prediction = (
        round(
            max(
                0.0,
                min(1.0, 0.6 * arrival_historical_occupancy + 0.4 * current_occupancy),
            ),
            3,
        )
        if current_occupancy is not None and arrival_historical_occupancy is not None
        else current_occupancy
    )

    return {
        "purpose": "Raw data and formula checks for verifying the occupancy forecast.",
        "merchant": {
            "merchant_id": merchant_id,
            "name": venue["name"],
            "category": venue["category"],
            "city": venue.get("city"),
        },
        "forecast_request": {
            "timestamp": utc_iso(forecast_dt),
            "arrival_offset_minutes": ARRIVAL_OFFSET_MINUTES,
            "arrival_timestamp": utc_iso(arrival_dt),
            "history_generated_from": utc_iso(HISTORY_START),
            "history_generated_until_exclusive": utc_iso(HISTORY_END),
        },
        "api_forecast": demand,
        "current_window_input": current_window,
        "historical_current_hour_input": {
            "explains_api_field": "demand.historical_avg",
            "target_weekday": current_window_start.weekday(),
            "target_hour": current_window_start.hour,
            "target_hour_of_week": hour_of_week(current_window_start),
            "before_timestamp": utc_iso(current_window_start),
            "effective_avg_transaction_count": current_history_avg,
            "used_fallback_baseline": current_history_used_fallback,
            **current_history,
        },
        "historical_arrival_hour_input": {
            "explains_predicted_occupancy_pct": "0.6 * historical_arrival_occupancy + 0.4 * current_occupancy_pct",
            "target_weekday": arrival_dt.weekday(),
            "target_hour": arrival_dt.hour,
            "target_hour_of_week": hour_of_week(arrival_dt),
            "before_timestamp": utc_iso(arrival_dt),
            "effective_avg_transaction_count": arrival_history_avg,
            "used_fallback_baseline": arrival_history_used_fallback,
            **arrival_history,
        },
        "formula_recheck": {
            "current_txn_rate_from_raw_count": current_rate,
            "current_occupancy_pct_from_raw_count": current_occupancy,
            "historical_arrival_occupancy_pct": arrival_historical_occupancy,
            "predicted_occupancy_formula": "round(clamp(0.6 * historical_arrival_occupancy_pct + 0.4 * current_occupancy_pct), 3)",
            "recomputed_predicted_occupancy_pct": recomputed_prediction,
            "matches_api_historical_avg": approx_equal(
                round(current_history_avg, 1)
                if current_history_avg is not None
                else None,
                demand["historical_avg"],
                tolerance=0.05,
            ),
            "matches_api_current_txn_rate": approx_equal(
                current_rate, demand["current_txn_rate"]
            ),
            "matches_api_current_occupancy_pct": approx_equal(
                current_occupancy, demand["current_occupancy_pct"]
            ),
            "matches_api_predicted_occupancy_pct": approx_equal(
                recomputed_prediction,
                demand["predicted_occupancy_pct"],
            ),
        },
    }


print("Forecast test timestamp")
print_json(
    "Pinned test window",
    {
        "test_timestamp": utc_iso(TEST_TIMESTAMP),
        "current_window_start": utc_iso(CURRENT_WINDOW_START),
        "history_start": utc_iso(HISTORY_START),
        "history_end_exclusive": utc_iso(HISTORY_END),
        "db_path": str(DB_PATH),
    },
)

ensure_test_venues()

print("1. Generate History")
send_request(
    api_url("/api/transactions/generate/history"),
    method="POST",
    data={
        "city": CITY,
        "category": OCCUPANCY_CATEGORY_FILTER,
        "limit": TEST_LIMIT,
        "start": utc_iso(HISTORY_START),
        "end": utc_iso(HISTORY_END),
        "seed": HISTORY_SEED,
    },
)

print("2. Generate Live Update")
send_request(
    api_url("/api/transactions/generate/live-update"),
    method="POST",
    data={
        "city": CITY,
        "category": OCCUPANCY_CATEGORY_FILTER,
        "limit": TEST_LIMIT,
        "timestamp": utc_iso(TEST_TIMESTAMP),
        "seed": LIVE_SEED,
    },
)

endpoints = [
    api_url("/api/health"),
    api_url(
        "/api/venues",
        {"category": OCCUPANCY_CATEGORY_FILTER, "city": CITY, "limit": TEST_LIMIT},
    ),
]

for url in endpoints:
    send_request(url)

print("Fetching venues to extract a valid occupancy-capable merchant ID...")
try:
    data = send_request(
        api_url(
            "/api/venues",
            {"category": OCCUPANCY_CATEGORY_FILTER, "city": CITY, "limit": TEST_LIMIT},
        ),
        preview_chars=1000,
    )
    if data and data.get("venues"):
        venue = data["venues"][0]
        merchant_id = venue["merchant_id"]
        timestamp_params = {
            "timestamp": utc_iso(TEST_TIMESTAMP),
            "arrival_offset_minutes": ARRIVAL_OFFSET_MINUTES,
        }
        print(f"Using dynamically fetched merchant_id: {merchant_id}\n")

        vendor_endpoints = [
            api_url(f"/api/occupancy/{merchant_id}", timestamp_params),
            api_url(
                f"/api/vendors/{merchant_id}/transactions/daily",
                {"date": TEST_TIMESTAMP.date().isoformat()},
            ),
            api_url(
                f"/api/vendors/{merchant_id}/transactions/averages",
                {"lookback_days": HISTORY_DAYS},
            ),
            api_url(f"/api/vendors/{merchant_id}/revenue/last-7-days"),
            api_url(
                f"/api/vendors/{merchant_id}/dashboard/today",
                {"timestamp": utc_iso(TEST_TIMESTAMP), "lookback_days": HISTORY_DAYS},
            ),
            api_url(
                f"/api/vendors/{merchant_id}/transactions/hour-rankings",
                {"lookback_days": HISTORY_DAYS},
            ),
        ]

        occupancy_response = None
        for url in vendor_endpoints:
            response = send_request(url)
            if f"/api/occupancy/{merchant_id}" in url:
                occupancy_response = response

        print("Occupancy Query")
        send_request(
            api_url("/api/occupancy/query"),
            method="POST",
            data={
                "merchant_ids": [merchant_id],
                "timestamp": utc_iso(TEST_TIMESTAMP),
                "arrival_offset_minutes": ARRIVAL_OFFSET_MINUTES,
            },
            preview_chars=1000,
        )

        if occupancy_response:
            print_json(
                "Forecast Verification Bundle",
                build_forecast_verification_bundle(venue, occupancy_response),
            )
        else:
            print(
                "Could not build verification bundle because the occupancy endpoint did not return data."
            )
    else:
        print(
            "No occupancy-capable venues found in the response to use for further tests."
        )
except Exception as e:
    print(f"Failed to fetch venues or build forecast verification bundle: {e}")
