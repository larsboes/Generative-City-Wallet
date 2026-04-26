from __future__ import annotations

import json
from datetime import datetime

from spark.graph.repository import GraphRepository, get_repository
from spark.models.context import DemoOverrides
from spark.repositories.merchants import (
    get_active_coupon_for_merchant,
    get_first_merchant_id,
    get_merchant_by_id,
    list_merchant_ids_by_grid_cell,
)
from spark.services.density import compute_density_signal
from spark.services.weather import classify_vibe_signal, classify_weather_need

# Heuristic scores used when Neo4j is unavailable or returns no rows.
# Same shape as previous mock — keeps offer prompts working unchanged.
DEFAULT_PREFERENCE_SCORES: dict[str, float] = {
    "cafe": 0.82,
    "bakery": 0.60,
    "bar": 0.40,
}

TIME_BUCKETS = [
    (7, 9, "morning_coffee"),
    (9, 11, "mid_morning"),
    (11, 13, "lunch_window"),
    (13, 16, "afternoon_lull"),
    (16, 19, "after_work"),
    (19, 22, "evening"),
    (22, 24, "late_night"),
    (0, 7, "late_night"),
]


def classify_time_bucket(dt: datetime) -> str:
    hour = dt.hour
    dow = dt.strftime("%A").lower()
    for start, end, bucket in TIME_BUCKETS:
        if start <= hour < end:
            return f"{dow}_{bucket}"
    return f"{dow}_late_night"


def get_merchant_info(merchant_id: str, db_path: str | None = None) -> dict | None:
    row = get_merchant_by_id(merchant_id=merchant_id, db_path=db_path)
    if not row:
        return None

    coupon_row = get_active_coupon_for_merchant(
        merchant_id=merchant_id, db_path=db_path
    )
    coupon = None
    if coupon_row:
        config = json.loads(coupon_row["config"])
        coupon = {
            "type": coupon_row["coupon_type"],
            "config": config,
            "max_discount_pct": config.get("discount_pct", 0),
            "valid_window_min": config.get("duration_minutes", 20),
        }

    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "lat": row["lat"],
        "lon": row["lon"],
        "address": row["address"],
        "grid_cell": row["grid_cell"],
        "coupon": coupon,
    }


def select_best_merchant(
    grid_cell: str,
    db_path: str | None = None,
    current_dt: datetime | None = None,
) -> str | None:
    merchant_ids = list_merchant_ids_by_grid_cell(grid_cell=grid_cell, db_path=db_path)
    if not merchant_ids:
        return get_first_merchant_id(db_path=db_path)

    best_id = None
    best_drop = -1.0
    for merchant_id in merchant_ids:
        density = compute_density_signal(
            merchant_id,
            current_dt=current_dt,
            db_path=db_path,
        )
        if density["drop_pct"] > best_drop:
            best_drop = density["drop_pct"]
            best_id = merchant_id
    return best_id


async def load_preference_scores(
    session_id: str,
    repo: GraphRepository | None = None,
) -> dict[str, float]:
    repo = repo or get_repository()
    scores = await repo.get_preference_scores(session_id, limit=10)
    if not scores:
        return dict(DEFAULT_PREFERENCE_SCORES)
    return {s.category: round(s.weight, 3) for s in scores}


def apply_demo_density_overrides(
    density: dict, demo_overrides: DemoOverrides | None
) -> dict:
    if not demo_overrides or demo_overrides.merchant_occupancy_pct is None:
        return density

    updated = density.copy()
    updated["current_occupancy_pct"] = demo_overrides.merchant_occupancy_pct / 100
    updated["density_score"] = max(
        0.05, 1 - (demo_overrides.merchant_occupancy_pct / 100)
    )
    updated["drop_pct"] = 1 - updated["density_score"]
    updated["offer_eligible"] = updated["drop_pct"] >= 0.30
    if updated["drop_pct"] >= 0.70:
        updated["signal"] = "FLASH"
    elif updated["drop_pct"] >= 0.50:
        updated["signal"] = "PRIORITY"
    elif updated["drop_pct"] >= 0.30:
        updated["signal"] = "QUIET"
    else:
        updated["signal"] = "NORMAL"
    return updated


def apply_demo_weather_overrides(
    *,
    weather: dict,
    demo_overrides: DemoOverrides | None,
    current_hour: int,
) -> dict:
    if not demo_overrides:
        return weather

    updated = weather
    if demo_overrides.temp_celsius is not None:
        updated = updated.copy()
        updated["temp_celsius"] = demo_overrides.temp_celsius
        updated["feels_like_celsius"] = demo_overrides.temp_celsius - 3
        updated["weather_need"] = classify_weather_need(
            demo_overrides.temp_celsius, updated.get("weather_condition", "clear")
        )
        updated["vibe_signal"] = classify_vibe_signal(
            updated["weather_need"], demo_overrides.temp_celsius, current_hour
        )

    if demo_overrides.weather_condition is not None:
        updated = updated.copy()
        updated["weather_condition"] = demo_overrides.weather_condition
        updated["weather_need"] = classify_weather_need(
            updated["temp_celsius"], demo_overrides.weather_condition
        )
        updated["vibe_signal"] = classify_vibe_signal(
            updated["weather_need"], updated["temp_celsius"], current_hour
        )

    return updated
