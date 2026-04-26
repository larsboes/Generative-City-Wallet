"""
Composite context state builder.
Assembles all signals into a single CompositeContextState for the LLM.
Supports demo overrides from the Context Slider.
"""

from datetime import datetime

from spark.graph.repository import GraphRepository, get_repository
from spark.models.common import ConflictRecommendation
from spark.models.context import (
    ActiveCoupon,
    CompositeContextState,
    ConflictResolutionContext,
    DecisionTraceItem,
    DemoOverrides,
    EnvironmentContext,
    IntentVector,
    MerchantContext,
    MerchantDemand,
    OfferDecisionTrace,
    UserContext,
)
from spark.services.composite_helpers import (
    DEFAULT_PREFERENCE_SCORES as HELPER_DEFAULT_PREFERENCE_SCORES,
    apply_demo_density_overrides,
    apply_demo_weather_overrides,
    classify_time_bucket as helper_classify_time_bucket,
    get_merchant_info,
    load_preference_scores,
    select_best_merchant,
)
from spark.services.conflict import resolve_conflict
from spark.services.density import compute_density_signal
from spark.services.distance import estimate_distance_m
from spark.services.offer_decision import decide_offer
from spark.services.weather import get_stuttgart_weather

DEFAULT_PREFERENCE_SCORES = HELPER_DEFAULT_PREFERENCE_SCORES


def classify_time_bucket(dt: datetime) -> str:
    return helper_classify_time_bucket(dt)


async def build_composite_state(
    intent: IntentVector,
    merchant_id: str | None = None,
    demo_overrides: DemoOverrides | None = None,
    transit_delay_minutes: int | None = None,
    must_return_by: str | None = None,
    db_path: str | None = None,
    graph_repo: GraphRepository | None = None,
) -> CompositeContextState:
    """
    Assemble all signals into a CompositeContextState.
    Supports demo overrides for the Context Slider.
    """
    now = demo_overrides.current_dt if demo_overrides and demo_overrides.current_dt else datetime.now()
    repo = graph_repo or get_repository()

    # Touch the user session in the graph (idempotent, fail-soft).
    await repo.ensure_session(intent.session_id)

    # ── Preference scores from the user knowledge graph ─────────────────────
    preference_scores = await load_preference_scores(intent.session_id, repo)

    effective_transit_delay = transit_delay_minutes
    effective_must_return_by = must_return_by
    if demo_overrides:
        if demo_overrides.transit_delay_minutes is not None:
            effective_transit_delay = demo_overrides.transit_delay_minutes
        if demo_overrides.must_return_by is not None:
            effective_must_return_by = demo_overrides.must_return_by

    # Auto-select merchant through deterministic decision pipeline.
    decision = decide_offer(
        session_id=intent.session_id,
        grid_cell=intent.grid_cell,
        movement_mode=intent.movement_mode.value,
        social_preference=intent.social_preference.value,
        weather_need=intent.weather_need.value,
        preference_scores=preference_scores,
        transit_delay_minutes=effective_transit_delay,
        must_return_by=effective_must_return_by,
        db_path=db_path,
        now=now,
    )
    if merchant_id is None:
        merchant_id = decision.selected_merchant_id
    if not merchant_id:
        merchant_id = select_best_merchant(intent.grid_cell, db_path, current_dt=now)

    # ── Merchant info ──────────────────────────────────────────────────────────
    merchant_info = get_merchant_info(merchant_id, db_path)
    if not merchant_info:
        fallback_merchant_id = select_best_merchant(
            intent.grid_cell,
            db_path,
            current_dt=now,
        )
        if fallback_merchant_id:
            merchant_id = fallback_merchant_id
            merchant_info = get_merchant_info(merchant_id, db_path)
    if not merchant_info:
        raise ValueError(f"Merchant {merchant_id} not found")

    # ── Density ────────────────────────────────────────────────────────────────
    density = compute_density_signal(merchant_id, current_dt=now, db_path=db_path)

    density = apply_demo_density_overrides(density, demo_overrides)

    # ── Weather ────────────────────────────────────────────────────────────────
    weather = await get_stuttgart_weather()

    weather = apply_demo_weather_overrides(
        weather=weather, demo_overrides=demo_overrides, current_hour=now.hour
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

    # Keep decision recommendation as the canonical gate. Conflict resolver
    # provides framing vocab for LLM rails.
    recommendation = decision.recommendation
    if recommendation not in {
        ConflictRecommendation.RECOMMEND.value,
        ConflictRecommendation.RECOMMEND_WITH_FRAMING.value,
        ConflictRecommendation.DO_NOT_RECOMMEND.value,
    }:
        recommendation = conflict.recommendation

    # ── Assemble ───────────────────────────────────────────────────────────────
    distance_m = estimate_distance_m(
        user_grid_cell=intent.grid_cell,
        merchant_grid_cell=merchant_info.get("grid_cell"),
        merchant_id=merchant_id,
    )

    active_coupon = ActiveCoupon(
        type=coupon["type"] if coupon else None,
        max_discount_pct=coupon.get("max_discount_pct", 0) if coupon else 0,
        valid_window_min=coupon.get("valid_window_min", 20) if coupon else 20,
        config=coupon.get("config") if coupon else None,
    )

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
                signal=density["signal"],  # type: ignore[reportArgumentType]
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
            recommendation=recommendation,  # type: ignore[reportArgumentType]
            framing_band=conflict.framing_band,
            allowed_vocabulary=conflict.allowed_vocabulary,
            banned_vocabulary=conflict.banned_vocabulary,
        ),
        decision_trace=OfferDecisionTrace(
            recommendation=recommendation,  # type: ignore[reportArgumentType]
            selected_merchant_id=decision.selected_merchant_id,
            selected_merchant_score=decision.selected_merchant_score,
            recheck_in_minutes=decision.recheck_in_minutes,
            candidate_scores=decision.candidate_scores,
            trace=[
                DecisionTraceItem(
                    code=step.code,
                    reason=step.reason,
                    score=step.score,
                    metadata=step.metadata,
                )
                for step in decision.trace
            ],
        ),
    )
