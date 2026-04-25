"""
Offer generation endpoint — the core pipeline.
IntentVector → CompositeState → GraphValidation → Gemini Flash
              → Hard Rails → SQLite audit → KG write → OfferObject
"""

import json
import uuid

from fastapi import APIRouter

from src.backend.db.connection import get_connection
from src.backend.graph.repository import get_repository
from src.backend.models.contracts import GenerateOfferRequest
from src.backend.services.composite import build_composite_state
from src.backend.services.graph_rules import GraphValidationService
from src.backend.services.hard_rails import enforce_hard_rails
from src.backend.services.offer_generator import generate_offer_llm
from src.backend.services.redemption import generate_qr_payload

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.post("/generate")
async def generate_offer(request: GenerateOfferRequest):
    """
    Full offer generation pipeline:

    1. Build composite context state (now graph-aware)
    2. Run deterministic graph-rule gate (anti-spam, fatigue, cooldown)
    3. Skip if conflict resolution says DO_NOT_RECOMMEND
    4. Call Gemini Flash (or smart fallback)
    5. Enforce hard rails
    6. Persist QR + SQLite audit
    7. Project the offer into the user knowledge graph (best-effort)
    """
    # 1. Build composite state
    state = await build_composite_state(
        request.intent,
        request.merchant_id,
        request.demo_overrides,
    )

    # 2. Graph-rule gate — runs before any LLM call.
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
        }

    # 3. Conflict-resolution gate (existing rules engine)
    if state.conflict_resolution.recommendation == "DO_NOT_RECOMMEND":
        return {
            "offer": None,
            "reason": "Conflict resolution determined not to recommend at this time.",
            "recommendation": state.conflict_resolution.recommendation,
            "recheck_in_minutes": 30,
            "graph_decision": rule_result.to_audit_dict(),
        }

    # 4. Generate offer via LLM
    offer_id = str(uuid.uuid4())
    llm_output = await generate_offer_llm(state)

    # 5. Enforce hard rails
    offer = enforce_hard_rails(llm_output, state, offer_id)

    # 6. Generate QR payload
    offer.qr_payload = generate_qr_payload(offer_id, state.session_id)

    # 7. SQLite audit (source of truth) — keep first
    _log_offer_audit(offer_id, state, llm_output, offer, rule_result.to_audit_dict())

    # 8. Project into knowledge graph (best-effort, never raises)
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


def _log_offer_audit(offer_id, state, llm_output, offer, graph_decision: dict | None = None):
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
                state.merchant.active_coupon.type if state.merchant.active_coupon else None,
                json.dumps(state.merchant.active_coupon.config) if state.merchant.active_coupon else None,
                llm_output.model_dump_json(),
                offer.model_dump_json(),
                json.dumps({"rails_applied": True, "graph_decision": graph_decision or {}}),
                "SENT",
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  Audit log write failed: {e}")
