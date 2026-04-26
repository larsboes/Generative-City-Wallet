"""
Deterministic offer decision engine.

This module owns the canonical rule-first selection pipeline:
hard blocks -> candidate scoring -> threshold -> anti-spam checks -> decision trace.
"""

from __future__ import annotations

from datetime import datetime

from spark.models.decision import DecisionTraceStep, MerchantDecision, OfferDecisionResult
from spark.repositories.offer_decision import OfferDecisionRepository
from spark.services.conflict import resolve_conflict
from spark.services.distance import distance_points, estimate_distance_m
from spark.services.density import compute_density_signal

MIN_SCORE_THRESHOLD = 30.0
POST_WORKOUT_RECOVERY_CATEGORIES = {
    "healthy_cafe",
    "juice_bar",
    "smoothie_bar",
    "cafe",
    "bakery",
}
POST_WORKOUT_SUPPRESSED_CATEGORIES = {"bar", "club", "nightclub"}
CYCLING_RECOVERY_CATEGORIES = {"juice_bar", "smoothie_bar", "healthy_cafe", "cafe"}
CYCLING_SUPPRESSED_CATEGORIES = {"club", "nightclub"}
TRANSIT_WAITING_FAST_CATEGORIES = {"cafe", "bakery", "juice_bar"}
TRANSIT_WAITING_SUPPRESSED_CATEGORIES = {"club", "nightclub", "restaurant"}


def decide_offer(
    *,
    session_id: str,
    grid_cell: str,
    movement_mode: str,
    social_preference: str,
    weather_need: str,
    preference_scores: dict[str, float],
    transit_delay_minutes: int | None = None,
    must_return_by: str | None = None,
    db_path: str | None = None,
    now: datetime | None = None,
) -> OfferDecisionResult:
    current_dt = now or datetime.now()
    repo = OfferDecisionRepository(db_path)
    hard_block = _check_hard_blocks(
        session_id=session_id,
        movement_mode=movement_mode,
        transit_delay_minutes=transit_delay_minutes,
        must_return_by=must_return_by,
        now=current_dt,
        repo=repo,
    )
    if hard_block:
        return OfferDecisionResult(
            recommendation="DO_NOT_RECOMMEND",
            selected_merchant_id=None,
            selected_merchant_score=0.0,
            recheck_in_minutes=hard_block.metadata.get("recheck_in_minutes", 30),
            trace=[hard_block],
            candidate_scores=[],
            conflict_framing_band=None,
        )

    candidates = repo.list_candidate_merchants(grid_cell=grid_cell)
    if not candidates:
        return OfferDecisionResult(
            recommendation="DO_NOT_RECOMMEND",
            selected_merchant_id=None,
            selected_merchant_score=0.0,
            recheck_in_minutes=30,
            trace=[
                DecisionTraceStep(
                    code="no_candidates",
                    reason="No merchants available in the current grid cell.",
                )
            ],
            candidate_scores=[],
            conflict_framing_band=None,
        )

    merchant_decisions: list[MerchantDecision] = []
    for candidate in candidates:
        merchant_decision = _score_merchant_candidate(
            merchant_id=candidate.merchant_id,
            merchant_category=candidate.merchant_category,
            user_grid_cell=grid_cell,
            merchant_grid_cell=candidate.merchant_grid_cell,
            movement_mode=movement_mode,
            social_preference=social_preference,
            weather_need=weather_need,
            preference_scores=preference_scores,
            current_dt=current_dt,
            db_path=db_path,
        )
        if merchant_decision is not None:
            merchant_decisions.append(merchant_decision)

    if not merchant_decisions:
        return OfferDecisionResult(
            recommendation="DO_NOT_RECOMMEND",
            selected_merchant_id=None,
            selected_merchant_score=0.0,
            recheck_in_minutes=_movement_recheck_minutes(
                movement_mode=movement_mode, default_minutes=30
            ),
            trace=[
                DecisionTraceStep(
                    code="all_candidates_filtered",
                    reason="All candidate merchants failed conflict or anti-spam rules.",
                )
            ],
            candidate_scores=[],
            conflict_framing_band=None,
        )

    merchant_decisions.sort(key=lambda m: m.score, reverse=True)
    best = merchant_decisions[0]
    candidate_scores = [
        {
            "merchant_id": md.merchant_id,
            "score": round(md.score, 3),
            "recommendation": md.conflict_recommendation,
            "framing_band": md.conflict_framing_band,
        }
        for md in merchant_decisions
    ]

    if best.score < MIN_SCORE_THRESHOLD:
        return OfferDecisionResult(
            recommendation="DO_NOT_RECOMMEND",
            selected_merchant_id=None,
            selected_merchant_score=round(best.score, 3),
            recheck_in_minutes=_movement_recheck_minutes(
                movement_mode=movement_mode, default_minutes=30
            ),
            trace=[
                DecisionTraceStep(
                    code="below_threshold",
                    reason=f"Best merchant score {best.score:.1f} is below threshold {MIN_SCORE_THRESHOLD:.1f}.",
                    score=best.score,
                    metadata={"threshold": MIN_SCORE_THRESHOLD},
                )
            ]
            + best.trace,
            candidate_scores=candidate_scores,
            conflict_framing_band=best.conflict_framing_band,
        )

    final_recommendation = (
        best.conflict_recommendation
        if best.conflict_recommendation in {"RECOMMEND", "RECOMMEND_WITH_FRAMING"}
        else "DO_NOT_RECOMMEND"
    )
    recheck_minutes = (
        None
        if final_recommendation != "DO_NOT_RECOMMEND"
        else _movement_recheck_minutes(movement_mode=movement_mode, default_minutes=30)
    )
    return OfferDecisionResult(
        recommendation=final_recommendation,
        selected_merchant_id=best.merchant_id
        if final_recommendation != "DO_NOT_RECOMMEND"
        else None,
        selected_merchant_score=round(best.score, 3),
        recheck_in_minutes=recheck_minutes,
        trace=best.trace,
        candidate_scores=candidate_scores,
        conflict_framing_band=best.conflict_framing_band,
    )


def _check_hard_blocks(
    *,
    session_id: str,
    movement_mode: str,
    transit_delay_minutes: int | None,
    must_return_by: str | None,
    now: datetime,
    repo: OfferDecisionRepository,
) -> DecisionTraceStep | None:
    if movement_mode == "exercising":
        return DecisionTraceStep(
            code="movement_hard_block",
            reason="Offers are blocked while user is exercising.",
            metadata={"movement_mode": movement_mode, "recheck_in_minutes": 10},
        )

    if transit_delay_minutes is not None:
        # Conservative deterministic gate for OCR transit window:
        # require enough time to walk + purchase + return.
        min_round_trip_minutes = 14
        if transit_delay_minutes < min_round_trip_minutes:
            return DecisionTraceStep(
                code="transit_window_block",
                reason="Transit delay window is too short for safe round-trip purchase.",
                metadata={
                    "transit_delay_minutes": transit_delay_minutes,
                    "min_round_trip_minutes": min_round_trip_minutes,
                    "must_return_by": must_return_by,
                    "recheck_in_minutes": max(3, transit_delay_minutes),
                },
            )

    session_state = repo.get_session_state(
        session_id=session_id, now=now
    )
    if session_state.unresolved_offer_id:
        recheck_in_minutes = _movement_recheck_minutes(
            movement_mode=movement_mode, default_minutes=20
        )
        return DecisionTraceStep(
            code="single_offer_guard",
            reason="Session has an unresolved active offer; one-offer policy blocks new offer.",
            metadata={
                "active_offer_id": session_state.unresolved_offer_id,
                "recheck_in_minutes": recheck_in_minutes,
            },
        )

    if session_state.offers_last_24h >= 3:
        return DecisionTraceStep(
            code="daily_cap_reached",
            reason="Session hit max offers per rolling 24h window.",
            metadata={"max_offers": 3, "recheck_in_minutes": 180},
        )
    return None


def _score_merchant_candidate(
    *,
    merchant_id: str,
    merchant_category: str,
    user_grid_cell: str,
    merchant_grid_cell: str | None,
    movement_mode: str,
    social_preference: str,
    weather_need: str,
    preference_scores: dict[str, float],
    current_dt: datetime,
    db_path: str | None,
) -> MerchantDecision | None:
    density = compute_density_signal(
        merchant_id, current_dt=current_dt, db_path=db_path
    )
    conflict = resolve_conflict(
        merchant_id=merchant_id,
        user_social_pref=social_preference,
        current_txn_rate=density["current_rate"],
        current_dt=current_dt,
        active_coupon=None,
        db_path=db_path,
    )
    if conflict.recommendation == "DO_NOT_RECOMMEND":
        return None

    score = 0.0
    trace: list[DecisionTraceStep] = []

    density_drop = max(0.0, 1.0 - float(density["density_score"]))
    density_score = density_drop * 40.0
    score += density_score
    trace.append(
        DecisionTraceStep(
            code="density_drop",
            reason=f"Density drop contributes {density_score:.1f} points.",
            score=round(density_score, 3),
            metadata={"drop_pct": round(density_drop, 3)},
        )
    )

    distance_m = estimate_distance_m(
        user_grid_cell=user_grid_cell,
        merchant_grid_cell=merchant_grid_cell,
        merchant_id=merchant_id,
    )
    distance_score = distance_points(distance_m)
    score += distance_score
    trace.append(
        DecisionTraceStep(
            code="distance_proxy",
            reason="Estimated distance contributes deterministic distance points.",
            score=distance_score,
            metadata={
                "distance_m_estimated": round(distance_m, 1),
                "user_grid_cell": user_grid_cell,
                "merchant_grid_cell": merchant_grid_cell,
            },
        )
    )

    pref_weight = preference_scores.get(merchant_category, 0.5)
    pref_points = max(0.0, min(pref_weight, 1.0)) * 20.0
    score += pref_points
    trace.append(
        DecisionTraceStep(
            code="preference_match",
            reason=f"Preference match for category '{merchant_category}'.",
            score=round(pref_points, 3),
            metadata={"preference_weight": round(pref_weight, 3)},
        )
    )

    weather_alignment = _weather_alignment(
        weather_need=weather_need, merchant_category=merchant_category
    )
    weather_points = weather_alignment * 10.0
    score += weather_points
    trace.append(
        DecisionTraceStep(
            code="weather_alignment",
            reason="Weather-category alignment contribution.",
            score=round(weather_points, 3),
            metadata={"alignment": round(weather_alignment, 3)},
        )
    )

    movement_points, movement_reason = _movement_category_adjustment(
        movement_mode=movement_mode,
        merchant_category=merchant_category,
    )
    if movement_points != 0.0:
        score += movement_points
        trace.append(
            DecisionTraceStep(
                code="movement_category_adjustment",
                reason=movement_reason,
                score=round(movement_points, 3),
                metadata={
                    "movement_mode": movement_mode,
                    "merchant_category": merchant_category,
                },
            )
        )

    trace.append(
        DecisionTraceStep(
            code="conflict_resolution",
            reason=conflict.reason,
            metadata={
                "recommendation": conflict.recommendation,
                "framing_band": conflict.framing_band,
            },
        )
    )

    return MerchantDecision(
        merchant_id=merchant_id,
        score=score,
        conflict_recommendation=conflict.recommendation,
        conflict_framing_band=conflict.framing_band,
        trace=trace,
    )


def _weather_alignment(*, weather_need: str, merchant_category: str) -> float:
    warm_categories = {"cafe", "bakery"}
    cool_categories = {"smoothie_bar", "juice_bar", "healthy_cafe"}
    nightlife_categories = {"bar", "club", "nightclub"}
    if weather_need == "warmth_seeking":
        return 1.0 if merchant_category in warm_categories else 0.4
    if weather_need == "refreshment_seeking":
        return 1.0 if merchant_category in cool_categories else 0.4
    if weather_need == "shelter_seeking":
        return (
            0.9 if merchant_category in warm_categories | nightlife_categories else 0.5
        )
    return 0.5


def _movement_category_adjustment(
    *, movement_mode: str, merchant_category: str
) -> tuple[float, str]:
    """
    Deterministic movement-aware weighting.

    Post-workout users should see recovery-oriented options and avoid nightlife.
    """
    if movement_mode == "post_workout":
        if merchant_category in POST_WORKOUT_RECOVERY_CATEGORIES:
            return 18.0, "Post-workout recovery category boost applied."
        if merchant_category in POST_WORKOUT_SUPPRESSED_CATEGORIES:
            return -14.0, "Post-workout nightlife suppression applied."
        return 0.0, "Post-workout neutral category."

    if movement_mode == "cycling":
        if merchant_category in CYCLING_RECOVERY_CATEGORIES:
            return 10.0, "Cycling recovery category boost applied."
        if merchant_category in CYCLING_SUPPRESSED_CATEGORIES:
            return -8.0, "Cycling nightlife suppression applied."
        return 0.0, "Cycling neutral category."

    if movement_mode == "transit_waiting":
        if merchant_category in TRANSIT_WAITING_FAST_CATEGORIES:
            return 8.0, "Transit-waiting quick-stop category boost applied."
        if merchant_category in TRANSIT_WAITING_SUPPRESSED_CATEGORIES:
            return -10.0, "Transit-waiting long-visit category suppression applied."
        return 0.0, "Transit-waiting neutral category."

    return 0.0, "No movement-specific category adjustment."


def _movement_recheck_minutes(*, movement_mode: str, default_minutes: int) -> int:
    """
    Adapt retry cadence to movement transitions.

    Post-workout windows are short-lived, so recheck sooner than default.
    """
    if movement_mode == "post_workout":
        return max(5, min(default_minutes, 12))
    if movement_mode == "cycling":
        return max(7, min(default_minutes, 15))
    if movement_mode == "transit_waiting":
        return max(3, min(default_minutes, 8))
    return default_minutes
