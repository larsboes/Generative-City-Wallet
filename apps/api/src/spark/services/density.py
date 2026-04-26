"""
Payone density signal computation.
Converts raw transaction rate into a normalized signal the offer engine consumes.
"""

from datetime import datetime

from spark.repositories.density import (
    get_historical_avg_at_arrival_hour,
    get_hourly_transaction_stats,
    get_latest_transaction_rate,
    list_merchants_for_density,
)


# ── Occupancy calibration (txn_rate_at_empty, txn_rate_at_capacity, capacity) ─

# Per-type occupancy calibration (txn_rate_at_empty, txn_rate_at_full, capacity).
# OSM merchants don't have individual calibration — infer_occupancy_pct returns None for them.
OCCUPANCY_CALIBRATION_BY_TYPE: dict[str, tuple[float, float, int]] = {
    "bar": (0.5, 22, 120),
    "club": (0.0, 35, 300),
}

OCCUPANCY_CALIBRATION: dict[str, tuple[float, float, int]] = {}


def compute_density_signal(
    merchant_id: str,
    current_txn_rate: float | None = None,
    current_dt: datetime | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Compute normalized density signal for a merchant.

    density_score = current_rate / historical_avg
    < 0.70 = offer-eligible quiet period
    < 0.50 = priority offer window
    < 0.30 = flash offer / emergency fill trigger
    """
    if current_dt is None:
        current_dt = datetime.now()

    hour_of_week = current_dt.weekday() * 24 + current_dt.hour
    avg_txn, sample_count = get_hourly_transaction_stats(
        merchant_id=merchant_id, hour_of_week=hour_of_week, db_path=db_path
    )

    # If no current rate provided, use the most recent matching hour
    if current_txn_rate is None:
        current_txn_rate = get_latest_transaction_rate(
            merchant_id=merchant_id, hour_of_week=hour_of_week, db_path=db_path
        )

    if avg_txn < 0.5:
        return {
            "merchant_id": merchant_id,
            "density_score": 1.0,
            "drop_pct": 0.0,
            "signal": "NORMALLY_CLOSED",
            "offer_eligible": False,
            "historical_avg": 0,
            "current_rate": current_txn_rate,
            "confidence": min(1.0, sample_count / 4),
            "timestamp": current_dt.isoformat(),
        }

    density_score = current_txn_rate / avg_txn
    drop_pct = max(0, 1 - density_score)

    if drop_pct >= 0.70:
        signal = "FLASH"
    elif drop_pct >= 0.50:
        signal = "PRIORITY"
    elif drop_pct >= 0.30:
        signal = "QUIET"
    else:
        signal = "NORMAL"

    eligible = drop_pct >= 0.30

    # Occupancy for bars/clubs
    current_occ = infer_occupancy_pct(merchant_id, current_txn_rate)

    return {
        "merchant_id": merchant_id,
        "density_score": round(density_score, 3),
        "drop_pct": round(drop_pct, 3),
        "signal": signal,
        "offer_eligible": eligible,
        "historical_avg": round(avg_txn, 1),
        "current_rate": round(current_txn_rate, 1),
        "current_occupancy_pct": current_occ,
        "confidence": min(1.0, sample_count / 4),
        "timestamp": current_dt.isoformat(),
    }


def infer_occupancy_pct(
    merchant_id: str, current_txn_rate: float, db_path: str | None = None
) -> float | None:
    """Linearly interpolate between known empty/full txn rates. Clamp [0, 1]."""
    if merchant_id in OCCUPANCY_CALIBRATION:
        calibration = OCCUPANCY_CALIBRATION[merchant_id]
    else:
        merchant_type = _get_merchant_type(merchant_id, db_path)
        calibration = OCCUPANCY_CALIBRATION_BY_TYPE.get(merchant_type)

    if calibration is None:
        return None

    empty_rate, full_rate, _capacity = calibration
    if full_rate <= empty_rate:
        return 0.0

    occ = (current_txn_rate - empty_rate) / (full_rate - empty_rate)
    return round(max(0.0, min(1.0, occ)), 3)


def _get_merchant_type(merchant_id: str, db_path: str | None = None) -> str | None:
    try:
        from spark.db.connection import get_connection
        conn = get_connection(db_path)
        row = conn.execute("SELECT type FROM merchants WHERE id = ?", (merchant_id,)).fetchone()
        conn.close()
        return row["type"] if row else None
    except Exception:
        return None


def predict_occupancy_at(
    merchant_id: str,
    current_occ_pct: float,
    current_dt: datetime,
    arrival_dt: datetime,
    db_path: str | None = None,
) -> float:
    """Predict occupancy at arrival using historical trajectory. 60% hist / 40% current blend."""
    arrival_hour_of_week = arrival_dt.weekday() * 24 + arrival_dt.hour
    hist_at_arrival = get_historical_avg_at_arrival_hour(
        merchant_id=merchant_id,
        arrival_hour_of_week=arrival_hour_of_week,
        db_path=db_path,
    )

    if not hist_at_arrival:
        return current_occ_pct

    hist_occ = infer_occupancy_pct(merchant_id, hist_at_arrival or 0)
    if hist_occ is None:
        return current_occ_pct

    predicted = 0.6 * hist_occ + 0.4 * current_occ_pct
    return round(max(0.0, min(1.0, predicted)), 3)


def get_all_merchants_density(db_path: str | None = None) -> list[dict]:
    """Return density info for all merchants."""
    merchants = list_merchants_for_density(db_path=db_path)

    results = []
    for m in merchants:
        density = compute_density_signal(m["id"], db_path=db_path)
        density["name"] = m["name"]
        density["type"] = m["type"]
        density["lat"] = m["lat"]
        density["lon"] = m["lon"]
        density["address"] = m["address"]
        density["grid_cell"] = m["grid_cell"]
        results.append(density)

    return results
