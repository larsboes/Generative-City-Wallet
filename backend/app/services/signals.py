from datetime import datetime, timedelta, timezone
import sqlite3

from backend.app.models import DemandContext, DemandSignal, Venue


BASE_HOURLY_RATES: dict[str, list[float]] = {
    "cafe": [0, 0, 0, 0, 0, 0, 0, 0, 0, 39, 42, 44, 42, 36, 38, 40, 42, 46, 51, 50, 44, 37, 39, 35],
    "bakery": [0, 0, 0, 0, 0, 0, 23, 37, 49, 51, 48, 43, 40, 32, 23, 22, 23, 19, 0, 0, 0, 0, 0, 0],
    "restaurant": [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 5, 13, 15, 8, 3, 4, 8, 16, 14, 6, 2, 1, 0],
    "bar": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 2, 1, 1, 2, 3, 6, 10, 15, 18, 16, 10],
    "pub": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 2, 1, 1, 2, 3, 6, 10, 15, 18, 16, 10],
    "biergarten": [0, 0, 0, 0, 0, 0, 0, 0, 0, 13, 20, 27, 32, 35, 37, 43, 54, 64, 72, 72, 59, 39, 26, 4],
    "nightclub": [25, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 3, 8, 14, 20, 24],
    "fast_food": [0, 0, 0, 0, 0, 0, 0, 1, 3, 3, 4, 7, 12, 12, 7, 4, 5, 8, 11, 9, 5, 3, 1, 0],
    "retail": [0, 0, 0, 0, 0, 0, 0, 0, 1, 3, 6, 8, 10, 9, 7, 6, 5, 4, 0, 0, 0, 0, 0, 0],
}

DAY_MULTIPLIERS: dict[str, list[float]] = {
    "cafe": [1.16, 0.98, 0.78, 0.93, 0.98, 1.25, 0.92],
    "bakery": [1.24, 1.03, 1.04, 1.34, 0.55, 1.02, 0.78],
    "restaurant": [0.80, 0.82, 0.85, 0.88, 1.10, 1.35, 1.25],
    "bar": [0.70, 0.72, 0.75, 0.85, 1.20, 1.60, 1.40],
    "pub": [0.70, 0.72, 0.75, 0.85, 1.20, 1.60, 1.40],
    "biergarten": [0.75, 0.84, 0.92, 0.99, 1.12, 1.26, 1.12],
    "nightclub": [0.30, 0.30, 0.40, 0.60, 1.50, 2.00, 1.70],
    "fast_food": [0.85, 0.88, 0.90, 0.92, 1.05, 1.30, 1.05],
    "retail": [0.90, 0.92, 0.92, 0.92, 1.05, 1.40, 0.80],
}

OCCUPANCY_CATEGORIES = {"bar", "pub", "nightclub", "biergarten"}
OCCUPANCY_CALIBRATION: dict[str, tuple[float, float]] = {
    "bar": (0.5, 22.0),
    "pub": (0.5, 22.0),
    "biergarten": (0.5, 28.0),
    "nightclub": (0.0, 35.0),
}


def hour_of_week(dt: datetime) -> int:
    return dt.weekday() * 24 + dt.hour


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return ensure_utc(dt).isoformat()


def normalize_category(category: str | None) -> str:
    if not category:
        return "unknown"
    normalized = category.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "food_court": "fast_food",
        "ice_cream": "cafe",
        "coffee_shop": "cafe",
        "club": "nightclub",
    }
    return aliases.get(normalized, normalized)


def fallback_historical_rate(category: str, dt: datetime) -> float:
    category = normalize_category(category)
    base = BASE_HOURLY_RATES.get(category, BASE_HOURLY_RATES["restaurant"])
    multipliers = DAY_MULTIPLIERS.get(category, DAY_MULTIPLIERS["restaurant"])
    return round(base[dt.hour] * multipliers[dt.weekday()], 3)


def classify_density(current_rate: float, historical_avg: float) -> tuple[float, float, DemandSignal, bool]:
    if historical_avg < 0.5:
        return 1.0, 0.0, "NORMALLY_CLOSED", False

    density_score = max(0.0, current_rate / historical_avg)
    drop_pct = max(0.0, min(1.0, 1 - density_score))

    if drop_pct >= 0.70:
        return density_score, drop_pct, "FLASH", True
    if drop_pct >= 0.50:
        return density_score, drop_pct, "PRIORITY", True
    if drop_pct >= 0.30:
        return density_score, drop_pct, "QUIET", True
    return density_score, drop_pct, "NORMAL", False


def infer_occupancy_pct(category: str, current_txn_rate: float) -> float | None:
    category = normalize_category(category)
    if category not in OCCUPANCY_CATEGORIES:
        return None

    empty_rate, full_rate = OCCUPANCY_CALIBRATION[category]
    if full_rate <= empty_rate:
        return 0.0

    occupancy = (current_txn_rate - empty_rate) / (full_rate - empty_rate)
    return round(max(0.0, min(1.0, occupancy)), 3)


def get_historical_rate(conn: sqlite3.Connection, merchant_id: str, category: str, dt: datetime) -> tuple[float, int]:
    rows = conn.execute(
        """
        SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS transaction_count
        FROM payone_transactions
        WHERE merchant_id = ?
          AND hour_of_week = ?
          AND timestamp < ?
        GROUP BY substr(timestamp, 1, 10)
        """,
        (merchant_id, hour_of_week(dt), iso(dt)),
    ).fetchall()
    if rows:
        sample_count = len(rows)
        avg = sum(float(row["transaction_count"]) for row in rows) / sample_count
        return avg, sample_count
    return fallback_historical_rate(category, dt), 0


def get_current_rate(conn: sqlite3.Connection, merchant_id: str, historical_avg: float, dt: datetime) -> float:
    del historical_avg
    end = ensure_utc(dt)
    start = end - timedelta(hours=1)
    row = conn.execute(
        """
        SELECT COUNT(*) AS transaction_count
        FROM payone_transactions
        WHERE merchant_id = ? AND timestamp >= ? AND timestamp < ?
        """,
        (merchant_id, iso(start), iso(end)),
    ).fetchone()
    return float(row["transaction_count"] or 0)


def predict_occupancy_pct(
    conn: sqlite3.Connection,
    venue: Venue,
    current_occupancy_pct: float | None,
    dt: datetime,
    arrival_offset_minutes: int,
) -> float | None:
    if current_occupancy_pct is None:
        return None

    arrival_dt = dt + timedelta(minutes=arrival_offset_minutes)
    arrival_avg, _ = get_historical_rate(conn, venue.merchant_id, venue.category, arrival_dt)
    historical_arrival_occ = infer_occupancy_pct(venue.category, arrival_avg)
    if historical_arrival_occ is None:
        return current_occupancy_pct

    return round(max(0.0, min(1.0, 0.6 * historical_arrival_occ + 0.4 * current_occupancy_pct)), 3)


def compute_demand_context(
    conn: sqlite3.Connection,
    venue: Venue,
    timestamp: datetime | None = None,
    arrival_offset_minutes: int = 10,
) -> DemandContext:
    dt = ensure_utc(timestamp or datetime.now(timezone.utc))
    rate_window_dt = dt - timedelta(hours=1)
    historical_avg, sample_count = get_historical_rate(conn, venue.merchant_id, venue.category, rate_window_dt)
    current_rate = get_current_rate(conn, venue.merchant_id, historical_avg, dt)
    density_score, drop_pct, signal, eligible = classify_density(current_rate, historical_avg)
    current_occupancy = infer_occupancy_pct(venue.category, current_rate)
    predicted_occupancy = predict_occupancy_pct(
        conn,
        venue,
        current_occupancy,
        dt,
        arrival_offset_minutes,
    )

    confidence = 0.35 if sample_count == 0 else min(1.0, sample_count / 4)
    return DemandContext(
        density_score=round(density_score, 3),
        drop_pct=round(drop_pct, 3),
        signal=signal,
        offer_eligible=eligible,
        current_txn_rate=round(current_rate, 1),
        historical_avg=round(historical_avg, 1),
        confidence=round(confidence, 2),
        current_occupancy_pct=current_occupancy,
        predicted_occupancy_pct=predicted_occupancy,
    )
