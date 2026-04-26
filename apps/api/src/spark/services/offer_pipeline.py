from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from spark.config import AGENT_ENABLED
from spark.graph.repository import get_repository
from spark.models.api import GenerateOfferRequest
from spark.models.offers import ExplainabilityReason
from spark.repositories.offers_audit import insert_offer_audit_log
from spark.repositories.wave import get_session_wave_bonus_for_merchant
from spark.services.composite import build_composite_state
from spark.services.graph_rules import GraphValidationService
from spark.services.hard_rails import enforce_hard_rails
from spark.services.offer_generator import generate_offer_llm
from spark.services.redemption import generate_qr_payload
from spark.utils.logger import get_logger

logger = get_logger("spark.offers")
OCR_CONFIDENCE_THRESHOLD = 0.6
LLM_RETRY_ATTEMPTS = 3
LLM_RETRY_BASE_DELAY_SEC = 0.3
_OFFER_PIPELINE_METRICS = {
    "llm_calls_total": 0,
    "llm_retries_total": 0,
    "llm_success_on_retry_total": 0,
    "llm_failures_total": 0,
}


def _build_explainability(
    state,
    rule_result,
    agent_reasoning: str | None = None,
    ocr_transit_meta: dict[str, Any] | None = None,
) -> list[ExplainabilityReason]:
    reasons: list[ExplainabilityReason] = []
    if agent_reasoning:
        reasons.append(
            ExplainabilityReason(
                code="agent_reasoning",
                reason=agent_reasoning,
                score=0.9,
                metadata={"source": "strands_agent"},
            )
        )

    top_pref = sorted(
        state.user.preference_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:2]
    for category, weight in top_pref:
        reasons.append(
            ExplainabilityReason(
                code="preference_match",
                reason=f"High affinity for '{category}' from past interactions.",
                score=round(float(weight), 3),
                metadata={"category": category},
            )
        )

    if rule_result.soft_violations:
        v = rule_result.soft_violations[0]
        reasons.append(
            ExplainabilityReason(
                code=v.rule_id,
                reason=v.reason,
                score=0.5,
                metadata=v.metadata,
            )
        )

    if rule_result.metadata.get("graph_available"):
        reasons.append(
            ExplainabilityReason(
                code="graph_rules_passed",
                reason="Deterministic graph guardrails passed for this candidate.",
                score=0.7,
                metadata={
                    "session_offers_24h": rule_result.metadata.get("session_offers_24h"),
                    "merchant_offers_24h": rule_result.metadata.get("merchant_offers_24h"),
                },
            )
        )

    if state.decision_trace and state.decision_trace.trace:
        for item in state.decision_trace.trace[:2]:
            reasons.append(
                ExplainabilityReason(
                    code=item.code,
                    reason=item.reason,
                    score=item.score,
                    metadata=item.metadata,
                )
            )

    if ocr_transit_meta:
        reasons.append(
            ExplainabilityReason(
                code="ocr_transit_input",
                reason="Transit delay context provided from OCR pipeline.",
                score=float(ocr_transit_meta.get("confidence", 0.8)),
                metadata=ocr_transit_meta,
            )
        )

    return reasons[:4]


def _log_offer_audit(
    offer_id,
    state,
    llm_output,
    offer,
    graph_decision: dict | None = None,
    pipeline_source: str = "deterministic",
    agent_reasoning: str | None = None,
):
    try:
        insert_offer_audit_log(
            (
                offer_id,
                state.timestamp,
                state.session_id,
                state.user.intent.grid_cell,
                state.user.intent.movement_mode.value,
                state.user.social_preference.value,
                state.merchant.id,
                state.merchant.demand.signal,
                state.merchant.demand.density_score,
                state.merchant.demand.current_occupancy_pct,
                state.merchant.demand.predicted_occupancy_pct,
                state.conflict_resolution.recommendation,
                state.conflict_resolution.recommendation,
                state.conflict_resolution.framing_band,
                state.merchant.active_coupon.type if state.merchant.active_coupon else None,
                json.dumps(state.merchant.active_coupon.config)
                if state.merchant.active_coupon
                else None,
                llm_output.model_dump_json(),
                offer.model_dump_json(),
                json.dumps(
                    (
                        (offer.audit_info.model_dump(mode="json") if offer.audit_info else {})
                        | {
                            "rails_applied": True,
                            "pipeline": pipeline_source,
                            "agent_reasoning": agent_reasoning,
                            "graph_decision": graph_decision or {},
                            "decision_trace": state.decision_trace.model_dump()
                            if state.decision_trace
                            else {},
                        }
                    )
                ),
                "SENT",
            )
        )
    except Exception as e:
        print(f"⚠️  Audit log write failed: {e}")


def _apply_wave_bonus_to_offer(*, offer, session_id: str, merchant_id: str) -> float:
    bonus_pct = get_session_wave_bonus_for_merchant(
        session_id=session_id,
        merchant_id=merchant_id,
    )
    if bonus_pct <= 0.0:
        return 0.0
    offer.discount.value = round(float(offer.discount.value) * (1.0 + bonus_pct), 2)
    offer.discount.source = "spark_wave_catalyst_bonus"
    return bonus_pct


async def generate_offer_pipeline(request: GenerateOfferRequest) -> Any:
    agent_decision = None
    agent_reasoning = None
    pipeline_source = "deterministic"

    if AGENT_ENABLED:
        try:
            from spark.agents.agent import run_offer_agent

            agent_decision = await run_offer_agent(
                session_id=request.intent.session_id,
                grid_cell=request.intent.grid_cell,
                movement_mode=request.intent.movement_mode.value,
                social_preference=request.intent.social_preference.value,
                price_tier=request.intent.price_tier.value,
                weather_need=request.intent.weather_need.value,
                time_bucket=request.intent.time_bucket,
                recent_categories=request.intent.recent_categories,
                merchant_id=request.merchant_id,
            )

            if agent_decision and not agent_decision.skip:
                request.merchant_id = agent_decision.merchant_id or request.merchant_id
                agent_reasoning = agent_decision.reasoning
                pipeline_source = "agent"
                logger.info(
                    "agent_selected_merchant",
                    extra={
                        "merchant_id": request.merchant_id,
                        "reasoning": agent_reasoning,
                    },
                )
            elif agent_decision and agent_decision.skip:
                return {
                    "offer": None,
                    "reason": agent_decision.reason
                    or "Agent determined no suitable merchant.",
                    "pipeline": "agent",
                    "recheck_in_minutes": 30,
                }
        except Exception as e:
            logger.warning("agent_fallback: %s", e)
            pipeline_source = "deterministic"
            agent_decision = None

    ocr_transit_effective = request.ocr_transit
    if request.ocr_transit and request.ocr_transit.confidence < OCR_CONFIDENCE_THRESHOLD:
        # Low-confidence OCR should not hard-gate deterministic recommendations.
        ocr_transit_effective = None

    state = await build_composite_state(
        request.intent,
        request.merchant_id,
        request.demo_overrides,
        ocr_transit_effective.transit_delay_minutes
        if ocr_transit_effective
        else request.transit_delay_minutes,
        ocr_transit_effective.must_return_by
        if ocr_transit_effective
        else request.must_return_by,
    )

    rules = GraphValidationService()
    rule_result = await rules.validate(
        session_id=state.session_id,
        merchant_id=state.merchant.id,
        merchant_category=state.merchant.category,
    )
    if not rule_result.accepted:
        violation = rule_result.hard_violations[0]
        return {
            "offer": None,
            "reason": violation.reason,
            "rule_id": violation.rule_id,
            "recheck_in_minutes": rule_result.recheck_in_minutes or 30,
            "graph_decision": rule_result.to_audit_dict(),
            "pipeline": pipeline_source,
        }

    if state.conflict_resolution.recommendation == "DO_NOT_RECOMMEND":
        return {
            "offer": None,
            "reason": "Conflict resolution determined not to recommend at this time.",
            "recommendation": state.conflict_resolution.recommendation,
            "recheck_in_minutes": state.decision_trace.recheck_in_minutes
            if state.decision_trace
            else 30,
            "decision_trace": state.decision_trace.model_dump()
            if state.decision_trace
            else None,
            "graph_decision": rule_result.to_audit_dict(),
            "pipeline": pipeline_source,
        }

    offer_id = str(uuid.uuid4())

    if agent_decision and agent_decision.content:
        llm_output = agent_decision.to_llm_offer_output(
            state.conflict_resolution.framing_band or ""
        )
        if llm_output is None:
            llm_output = await _generate_offer_llm_with_retry(state)
    else:
        llm_output = await _generate_offer_llm_with_retry(state)

    offer = enforce_hard_rails(llm_output, state, offer_id)
    wave_bonus_pct = _apply_wave_bonus_to_offer(
        offer=offer,
        session_id=state.session_id,
        merchant_id=state.merchant.id,
    )
    ocr_meta = None
    if request.ocr_transit:
        ocr_meta = request.ocr_transit.model_dump(mode="json")
        ocr_meta["threshold_applied"] = OCR_CONFIDENCE_THRESHOLD
        ocr_meta["used_for_gating"] = bool(ocr_transit_effective)
    offer.explainability = _build_explainability(
        state, rule_result, agent_reasoning, ocr_meta
    )
    if wave_bonus_pct > 0.0:
        offer.explainability = [
            ExplainabilityReason(
                code="spark_wave_catalyst_bonus",
                reason="Active Spark Wave participation increased this offer value.",
                score=wave_bonus_pct,
                metadata={"catalyst_bonus_pct": wave_bonus_pct},
            ),
            *offer.explainability,
        ][:4]
    offer.qr_payload = generate_qr_payload(offer_id, state.session_id)

    _log_offer_audit(
        offer_id,
        state,
        llm_output,
        offer,
        rule_result.to_audit_dict(),
        pipeline_source,
        agent_reasoning,
    )

    repo = get_repository()
    await repo.write_offer(
        offer_id=offer_id,
        session_id=state.session_id,
        merchant_id=state.merchant.id,
        merchant_name=state.merchant.name,
        merchant_category=state.merchant.category,
        framing_band=state.conflict_resolution.framing_band,
        density_signal=state.merchant.demand.signal.value
        if hasattr(state.merchant.demand.signal, "value")
        else str(state.merchant.demand.signal),
        drop_pct=float(state.merchant.demand.drop_pct),
        distance_m=float(state.merchant.distance_m),
        coupon_type=state.merchant.active_coupon.type.value
        if state.merchant.active_coupon and state.merchant.active_coupon.type
        else None,
        discount_pct=float(state.merchant.active_coupon.max_discount_pct or 0),
        timestamp=state.timestamp,
        grid_cell=state.user.intent.grid_cell,
        movement_mode=state.user.intent.movement_mode.value,
        time_bucket=state.user.intent.time_bucket,
        weather_need=state.environment.weather_need,
        vibe_signal=state.environment.vibe_signal,
        temp_c=float(state.environment.temp_celsius),
        social_preference=state.user.social_preference.value,
        occupancy_pct=state.merchant.demand.current_occupancy_pct,
        predicted_occupancy_pct=state.merchant.demand.predicted_occupancy_pct,
    )

    return offer


async def _generate_offer_llm_with_retry(state):
    last_exc: Exception | None = None
    for attempt in range(1, LLM_RETRY_ATTEMPTS + 1):
        try:
            _OFFER_PIPELINE_METRICS["llm_calls_total"] += 1
            result = await generate_offer_llm(state)
            if attempt > 1:
                _OFFER_PIPELINE_METRICS["llm_success_on_retry_total"] += 1
                logger.info(
                    "offer_llm_retry_success attempt=%s/%s",
                    attempt,
                    LLM_RETRY_ATTEMPTS,
                )
            return result
        except Exception as exc:  # defensive retries around transient model errors
            last_exc = exc
            _OFFER_PIPELINE_METRICS["llm_failures_total"] += 1
            if attempt == LLM_RETRY_ATTEMPTS:
                break
            delay = LLM_RETRY_BASE_DELAY_SEC * (2 ** (attempt - 1))
            _OFFER_PIPELINE_METRICS["llm_retries_total"] += 1
            logger.warning(
                "offer_llm_retry attempt=%s/%s delay=%ss err=%s",
                attempt,
                LLM_RETRY_ATTEMPTS,
                round(delay, 2),
                exc,
            )
            await asyncio.sleep(delay)
    raise last_exc if last_exc else RuntimeError("offer LLM generation failed")


def get_offer_pipeline_metrics() -> dict[str, int]:
    return dict(_OFFER_PIPELINE_METRICS)
