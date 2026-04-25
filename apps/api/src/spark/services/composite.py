"""
Composite context state builder.
Assembles all signals into a single CompositeContextState for the LLM.
Supports demo overrides from the Context Slider.
"""

import json
from datetime import datetime

from spark.db.connection import get_connection
from spark.graph.repository import GraphRepository, get_repository
from spark.models.contracts import (
    ActiveCoupon,
    CompositeContextState,
    ConflictResolutionContext,
    EnvironmentContext,
    IntentVector,
    MerchantContext,
    MerchantDemand,
    UserContext,
    DemoOverrides,
)
from spark.services.density import compute_density_signal
from spark.services.conflict import resolve_conflict
from spark.services.weather import get_stuttgart_weather


# Heuristic scores used when Neo4j is unavailable or returns no rows.
# Same shape as previous mock — keeps offer prompts working unchanged.
DEFAULT_PREFERENCE_SCORES: dict[str, float] = {
    "cafe": 0.82,
    "bakery": 0.60,
    "bar": 0.40,
}


# ── Time bucket classification ─────────────────────────────────────────────────

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


def _get_merchant_info(merchant_id: str, db_path: str | None = None) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT id, name, type, lat, lon, address, grid_cell FROM merchants WHERE id = ?",
        (merchant_id,),
    ).fetchone()
    if not row:
        conn.close()
        return None

    # Get active coupon
    coupon_row = conn.execute(
        "SELECT coupon_type, config FROM merchant_coupons WHERE merchant_id = ? AND active = 1 LIMIT 1",
        (merchant_id,),
    ).fetchone()
    conn.close()

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


def _select_best_merchant(grid_cell: str, db_path: str | None = None) -> str | None:
    """Auto-select the best merchant for a grid cell (highest density drop)."""
    conn = get_connection(db_path)
    merchants = conn.execute(
        "SELECT id FROM merchants WHERE grid_cell = ?", (grid_cell,)
    ).fetchall()
    conn.close()

    if not merchants:
        # Fallback — just pick the first merchant
        conn2 = get_connection(db_path)
        first = conn2.execute("SELECT id FROM merchants LIMIT 1").fetchone()
        conn2.close()
        return first["id"] if first else None

    best_id = None
    best_drop = -1.0
    for m in merchants:
        density = compute_density_signal(m["id"], db_path=db_path)
        if density["drop_pct"] > best_drop:
            best_drop = density["drop_pct"]
            best_id = m["id"]

    return best_id


async def _load_preference_scores(
    session_id: str,
    repo: GraphRepository | None = None,
) -> dict[str, float]:
    """
    Pull category preference scores from the user knowledge graph.

    Falls back to the heuristic dict when Neo4j is unavailable or has
    no edges yet (cold-start). Always returns a dict the LLM prompt
    can serialize.
    """
    repo = repo or get_repository()
    scores = await repo.get_preference_scores(session_id, limit=10)
    if not scores:
        return dict(DEFAULT_PREFERENCE_SCORES)
    return {s.category: round(s.weight, 3) for s in scores}


async def build_composite_state(
    intent: IntentVector,
    merchant_id: str | None = None,
    demo_overrides: DemoOverrides | None = None,
    db_path: str | None = None,
    graph_repo: GraphRepository | None = None,
) -> CompositeContextState:
    """
    Assemble all signals into a CompositeContextState.
    Supports demo overrides for the Context Slider.
    """
    now = datetime.now()
    repo = graph_repo or get_repository()

    # Touch the user session in the graph (idempotent, fail-soft).
    await repo.ensure_session(intent.session_id)

    # Auto-select merchant if not specified
    if not merchant_id:
        merchant_id = _select_best_merchant(intent.grid_cell, db_path)
    if not merchant_id:
        merchant_id = "MERCHANT_001"  # ultimate fallback

    # ── Merchant info ──────────────────────────────────────────────────────────
    merchant_info = _get_merchant_info(merchant_id, db_path)
    if not merchant_info:
        raise ValueError(f"Merchant {merchant_id} not found")

    # ── Density ────────────────────────────────────────────────────────────────
    density = compute_density_signal(merchant_id, db_path=db_path)

    # Apply demo override for occupancy
    if demo_overrides and demo_overrides.merchant_occupancy_pct is not None:
        # Reverse-engineer txn_rate from occupancy override
        density["current_occupancy_pct"] = demo_overrides.merchant_occupancy_pct / 100
        # Adjust density_score based on override
        density["density_score"] = max(
            0.05, 1 - (demo_overrides.merchant_occupancy_pct / 100)
        )
        density["drop_pct"] = 1 - density["density_score"]
        density["offer_eligible"] = density["drop_pct"] >= 0.30
        if density["drop_pct"] >= 0.70:
            density["signal"] = "FLASH"
        elif density["drop_pct"] >= 0.50:
            density["signal"] = "PRIORITY"
        elif density["drop_pct"] >= 0.30:
            density["signal"] = "QUIET"
        else:
            density["signal"] = "NORMAL"

    # ── Weather ────────────────────────────────────────────────────────────────
    weather = await get_stuttgart_weather()

    # Apply demo overrides
    if demo_overrides:
        if demo_overrides.temp_celsius is not None:
            weather = weather.copy()
            weather["temp_celsius"] = demo_overrides.temp_celsius
            weather["feels_like_celsius"] = demo_overrides.temp_celsius - 3
            from spark.services.weather import (
                classify_weather_need,
                classify_vibe_signal,
            )

            weather["weather_need"] = classify_weather_need(
                demo_overrides.temp_celsius, weather.get("weather_condition", "clear")
            )
            weather["vibe_signal"] = classify_vibe_signal(
                weather["weather_need"], demo_overrides.temp_celsius, now.hour
            )
        if demo_overrides.weather_condition is not None:
            weather = weather.copy()
            weather["weather_condition"] = demo_overrides.weather_condition
            from spark.services.weather import (
                classify_weather_need,
                classify_vibe_signal,
            )

            weather["weather_need"] = classify_weather_need(
                weather["temp_celsius"], demo_overrides.weather_condition
            )
            weather["vibe_signal"] = classify_vibe_signal(
                weather["weather_need"], weather["temp_celsius"], now.hour
            )

    # ── Social preference (may be overridden) ──────────────────────────────────
    social_pref = intent.social_preference
    if demo_overrides and demo_overrides.social_preference is not None:
        social_pref = demo_overrides.social_preference

    # ── Conflict resolution ────────────────────────────────────────────────────
    coupon = merchant_info.get("coupon")
    conflict = resolve_conflict(
        merchant_id=merchant_id,
        user_social_pref=social_pref.value
        if hasattr(social_pref, "value")
        else social_pref,
        current_txn_rate=density["current_rate"],
        current_dt=now,
        active_coupon=coupon,
        db_path=db_path,
    )

    # ── Time bucket ────────────────────────────────────────────────────────────
    if demo_overrides and demo_overrides.time_bucket:
        pass

    # ── Assemble ───────────────────────────────────────────────────────────────
    # Simple distance estimate (stub — in production, use Haversine from user grid cell)
    distance_m = 80.0  # Default for demo

    active_coupon = ActiveCoupon(
        type=coupon["type"] if coupon else None,
        max_discount_pct=coupon.get("max_discount_pct", 0) if coupon else 0,
        valid_window_min=coupon.get("valid_window_min", 20) if coupon else 20,
        config=coupon.get("config") if coupon else None,
    )

    # ── Preference scores from the user knowledge graph ─────────────────────
    preference_scores = await _load_preference_scores(intent.session_id, repo)

    return CompositeContextState(
        timestamp=now.isoformat(),
        session_id=intent.session_id,
        user=UserContext(
            intent=intent,
            preference_scores=preference_scores,
            social_preference=social_pref,
            price_tier=intent.price_tier,
        ),
        merchant=MerchantContext(
            id=merchant_id,
            name=merchant_info["name"],
            category=merchant_info["type"],
            distance_m=distance_m,
            address=merchant_info["address"],
            demand=MerchantDemand(
                density_score=density["density_score"],
                drop_pct=density["drop_pct"],
                signal=density["signal"],
                offer_eligible=density["offer_eligible"],
                current_occupancy_pct=density.get("current_occupancy_pct"),
                predicted_occupancy_pct=density.get("predicted_occupancy_pct"),
            ),
            active_coupon=active_coupon,
            tone_preference="cozy" if merchant_info["type"] == "cafe" else None,
        ),
        environment=EnvironmentContext(
            weather_condition=weather["weather_condition"],
            temp_celsius=weather["temp_celsius"],
            feels_like_celsius=weather["feels_like_celsius"],
            weather_need=weather["weather_need"],
            vibe_signal=weather["vibe_signal"],
        ),
        conflict_resolution=ConflictResolutionContext(
            recommendation=conflict.recommendation,
            framing_band=conflict.framing_band,
            allowed_vocabulary=conflict.allowed_vocabulary,
            banned_vocabulary=conflict.banned_vocabulary,
        ),
    )
