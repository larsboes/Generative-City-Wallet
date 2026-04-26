"""
Offer generation endpoint — the core pipeline.

HYBRID ARCHITECTURE:
  Agent path:  IntentVector → GraphValidation → StrAnds OfferAgent (tools)
               → Hard Rails → SQLite audit → KG write → OfferObject
  Fallback:    IntentVector → CompositeState → GraphValidation → Gemini Flash
               → Hard Rails → SQLite audit → KG write → OfferObject
"""

import json
import logging
import uuid

from fastapi import APIRouter

from spark.config import AGENT_ENABLED
from spark.db.connection import get_connection
from spark.graph.repository import get_repository
from spark.models.contracts import ExplainabilityReason, GenerateOfferRequest
from spark.services.composite import build_composite_state
from spark.services.graph_rules import GraphValidationService
from spark.services.hard_rails import enforce_hard_rails
from spark.services.offer_generator import generate_offer_llm
from spark.services.redemption import generate_qr_payload

logger = logging.getLogger("spark.offers")
router = APIRouter(prefix="/api/offers", tags=["offers"])


def _build_explainability(
    state, rule_result, agent_reasoning: str | None = None
) -> list[ExplainabilityReason]:
    reasons: list[ExplainabilityReason] = []

    # Agent reasoning (when available)
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
                    "session_offers_24h": rule_result.metadata.get(
                        "session_offers_24h"
                    ),
                    "merchant_offers_24h": rule_result.metadata.get(
                        "merchant_offers_24h"
                    ),
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

    return reasons[:4]


@router.post("/generate")
async def generate_offer(request: GenerateOfferRequest):
    """
    Hybrid offer generation pipeline:

    1. Try Strands OfferAgent (if AGENT_ENABLED + API key present)
       - Agent calls tools to reason about merchant selection + framing
       - Falls back to deterministic pipeline on any failure
    2. Build composite context state (graph-aware)
    3. Run deterministic graph-rule gate (anti-spam, fatigue, cooldown)
    4. Call Gemini Flash or smart fallback (if agent didn't run)
    5. Enforce hard rails — DB always wins
    6. Persist QR + SQLite audit + KG projection
    """
    agent_decision = None
    agent_reasoning = None
    pipeline_source = "deterministic"

    # ── AGENT PATH (try first if enabled) ──────────────────────────────────
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

            if agent_decision and not agent_decision.get("skip"):
                # Agent succeeded — override merchant selection
                request.merchant_id = agent_decision.get(
                    "merchant_id", request.merchant_id
                )
                agent_reasoning = agent_decision.get("reasoning")
                pipeline_source = "agent"
                logger.info(
                    "agent_selected_merchant",
                    extra={
                        "merchant_id": request.merchant_id,
                        "reasoning": agent_reasoning,
                    },
                )
            elif agent_decision and agent_decision.get("skip"):
                return {
                    "offer": None,
                    "reason": agent_decision.get(
                        "reason", "Agent determined no suitable merchant."
                    ),
                    "pipeline": "agent",
                    "recheck_in_minutes": 30,
                }
        except Exception as e:
            logger.warning("agent_fallback: %s", e)
            pipeline_source = "deterministic"
            agent_decision = None

    # ── DETERMINISTIC PIPELINE (always runs for graph rules + hard rails) ──
    # 1. Build composite state (uses agent's merchant_id if selected)
    state = await build_composite_state(
        request.intent,
        request.merchant_id,
        request.demo_overrides,
    )

    # 2. Graph-rule gate — runs before any content generation
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

    # 3. Conflict-resolution gate
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

    # 4. Generate offer content
    offer_id = str(uuid.uuid4())

    if agent_decision and agent_decision.get("content"):
        # Agent provided content + GenUI → wrap as LLMOfferOutput
        from spark.models.contracts import LLMOfferOutput

        llm_output = LLMOfferOutput(
            content=agent_decision["content"],
            genui=agent_decision.get(
                "genui",
                {
                    "color_palette": "warm_amber",
                    "typography_weight": "medium",
                    "background_style": "gradient",
                    "imagery_prompt": "contextual offer card",
                    "urgency_style": "gentle_pulse",
                    "card_mood": "cozy",
                },
            ),
            framing_band_used=state.conflict_resolution.framing_band or "",
        )
    else:
        # Deterministic fallback — direct LLM call
        llm_output = await generate_offer_llm(state)

    # 5. Enforce hard rails — DB ALWAYS WINS
    offer = enforce_hard_rails(llm_output, state, offer_id)
    offer.explainability = _build_explainability(state, rule_result, agent_reasoning)

    # 6. Generate QR payload
    offer.qr_payload = generate_qr_payload(offer_id, state.session_id)

    # 7. SQLite audit (source of truth)
    _log_offer_audit(
        offer_id,
        state,
        llm_output,
        offer,
        rule_result.to_audit_dict(),
        pipeline_source,
        agent_reasoning,
    )

    # 8. Project into knowledge graph (best-effort)
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


def _log_offer_audit(
    offer_id,
    state,
    llm_output,
    offer,
    graph_decision: dict | None = None,
    pipeline_source: str = "deterministic",
    agent_reasoning: str | None = None,
):
    """Write offer details to audit log."""
    try:
        conn = get_connection()
        conn.execute(
            """INSERT INTO offer_audit_log (
                offer_id, created_at, session_id, grid_cell, movement_mode,
                social_preference, merchant_id, density_signal, density_score,
                current_occupancy_pct, predicted_occupancy_pct,
                conflict_check, conflict_resolution, framing_band,
                coupon_type, coupon_config,
                llm_raw_output, final_offer, rails_audit, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                state.merchant.active_coupon.type
                if state.merchant.active_coupon
                else None,
                json.dumps(state.merchant.active_coupon.config)
                if state.merchant.active_coupon
                else None,
                llm_output.model_dump_json(),
                offer.model_dump_json(),
                json.dumps(
                    {
                        "rails_applied": True,
                        "pipeline": pipeline_source,
                        "agent_reasoning": agent_reasoning,
                        "graph_decision": graph_decision or {},
                        "decision_trace": state.decision_trace.model_dump()
                        if state.decision_trace
                        else {},
                    }
                ),
                "SENT",
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  Audit log write failed: {e}")
