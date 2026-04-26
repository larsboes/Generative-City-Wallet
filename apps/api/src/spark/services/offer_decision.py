"""
Deterministic offer decision engine.

This module owns the canonical rule-first selection pipeline:
hard blocks -> candidate scoring -> threshold -> anti-spam checks -> decision trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from spark.db.connection import get_connection
from spark.services.conflict import resolve_conflict
from spark.services.density import compute_density_signal

MIN_SCORE_THRESHOLD = 30.0


@dataclass(frozen=True)
class DecisionTraceStep:
    code: str
    reason: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MerchantDecision:
    merchant_id: str
    score: float
    conflict_recommendation: str
    conflict_framing_band: str | None
    trace: list[DecisionTraceStep]


@dataclass(frozen=True)
class OfferDecisionResult:
    recommendation: str
    selected_merchant_id: str | None
    selected_merchant_score: float
    recheck_in_minutes: int | None
    trace: list[DecisionTraceStep]
    candidate_scores: list[dict[str, Any]]
    conflict_framing_band: str | None


def decide_offer(
    *,
    session_id: str,
    grid_cell: str,
    movement_mode: str,
    social_preference: str,
    weather_need: str,
    preference_scores: dict[str, float],
    db_path: str | None = None,
    now: datetime | None = None,
) -> OfferDecisionResult:
    current_dt = now or datetime.now()
    hard_block = _check_hard_blocks(
        session_id=session_id,
        movement_mode=movement_mode,
        db_path=db_path,
        now=current_dt,
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

    candidates = _list_candidate_merchants(grid_cell=grid_cell, db_path=db_path)
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
            merchant_id=candidate["id"],
            merchant_category=candidate["type"],
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
            recheck_in_minutes=30,
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
            recheck_in_minutes=30,
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
    recheck_minutes = None if final_recommendation != "DO_NOT_RECOMMEND" else 30
    return OfferDecisionResult(
        recommendation=final_recommendation,
        selected_merchant_id=best.merchant_id if final_recommendation != "DO_NOT_RECOMMEND" else None,
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
    db_path: str | None,
    now: datetime,
) -> DecisionTraceStep | None:
    if movement_mode == "exercising":
        return DecisionTraceStep(
            code="movement_hard_block",
            reason="Offers are blocked while user is exercising.",
            metadata={"movement_mode": movement_mode, "recheck_in_minutes": 10},
        )

    conn = get_connection(db_path)
    try:
        unresolved = conn.execute(
            """
            SELECT offer_id FROM offer_audit_log
            WHERE session_id = ?
              AND status IN ('SENT', 'ACCEPTED')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if unresolved:
            return DecisionTraceStep(
                code="single_offer_guard",
                reason="Session has an unresolved active offer; one-offer policy blocks new offer.",
                metadata={"active_offer_id": unresolved["offer_id"], "recheck_in_minutes": 20},
            )

        today_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM offer_audit_log
            WHERE session_id = ?
              AND datetime(created_at) >= datetime(?)
            """,
            (session_id, (now - timedelta(hours=24)).isoformat()),
        ).fetchone()
        if today_count and int(today_count["c"]) >= 3:
            return DecisionTraceStep(
                code="daily_cap_reached",
                reason="Session hit max offers per rolling 24h window.",
                metadata={"max_offers": 3, "recheck_in_minutes": 180},
            )

    finally:
        conn.close()
    return None


def _list_candidate_merchants(*, grid_cell: str, db_path: str | None) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, type FROM merchants WHERE grid_cell = ?",
            (grid_cell,),
        ).fetchall()
        if rows:
            return [dict(r) for r in rows]
        fallback = conn.execute("SELECT id, type FROM merchants LIMIT 5").fetchall()
        return [dict(r) for r in fallback]
    finally:
        conn.close()


def _score_merchant_candidate(
    *,
    merchant_id: str,
    merchant_category: str,
    social_preference: str,
    weather_need: str,
    preference_scores: dict[str, float],
    current_dt: datetime,
    db_path: str | None,
) -> MerchantDecision | None:
    density = compute_density_signal(merchant_id, current_dt=current_dt, db_path=db_path)
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

    # In current MVP we don't have precise per-session distance in backend;
    # keep deterministic default for ranking stability.
    distance_points = 25.0
    score += distance_points
    trace.append(
        DecisionTraceStep(
            code="distance_proxy",
            reason="Default in-range distance contributes 25 points.",
            score=distance_points,
            metadata={"distance_m_assumed": 80},
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

    weather_alignment = _weather_alignment(weather_need=weather_need, merchant_category=merchant_category)
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
        return 0.9 if merchant_category in warm_categories | nightlife_categories else 0.5
    return 0.5
