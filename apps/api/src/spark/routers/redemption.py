"""
Redemption and wallet endpoints.
"""

from typing import Any, cast

from fastapi import APIRouter

from spark.models.conflict import ConflictResolveRequest, ConflictResolveResponse
from spark.models.redemption import (
    OfferOutcomeResponse,
    RedemptionConfirmResponse,
    RedemptionValidationRequest,
    RedemptionValidationResponse,
    WalletResponse,
)
from spark.services.conflict import resolve_conflict
from spark.services.redemption import (
    confirm_redemption,
    get_wallet,
    lookup_merchant_category_for_offer,
    project_offer_outcome_to_graph,
    project_redemption_to_graph,
    validate_qr,
)

router = APIRouter(prefix="/api", tags=["redemption"])


@router.post("/redemption/validate", response_model=RedemptionValidationResponse)
async def validate_endpoint(
    request: RedemptionValidationRequest,
) -> RedemptionValidationResponse:
    """Merchant scans QR — validate and return discount info."""
    return cast(Any, validate_qr(request.qr_payload, request.merchant_id))


@router.post("/redemption/confirm", response_model=RedemptionConfirmResponse)
async def confirm_endpoint(offer_id: str) -> RedemptionConfirmResponse:
    """Confirm redemption — credit cashback and reinforce KG preferences."""
    result = confirm_redemption(offer_id)
    if result.get("success"):
        category = lookup_merchant_category_for_offer(offer_id)
        await project_redemption_to_graph(
            session_id=result["session_id"],
            offer_id=offer_id,
            discount_value=result.get("amount_eur", 0.0),
            discount_type="percentage",
            amount_eur=result.get("amount_eur", 0.0),
            merchant_category=category,
        )
    return RedemptionConfirmResponse(**result)


@router.post("/offers/{offer_id}/outcome", response_model=OfferOutcomeResponse)
async def offer_outcome_endpoint(
    offer_id: str, status: str, session_id: str
) -> OfferOutcomeResponse:
    """
    Record a non-redemption outcome (ACCEPTED, DECLINED, EXPIRED) for an offer.

    Updates the SQLite audit log and applies the corresponding feedback
    edge in the user knowledge graph.
    """
    status = status.upper()
    if status not in {"ACCEPTED", "DECLINED", "EXPIRED"}:
        return OfferOutcomeResponse(success=False, error="INVALID_STATUS")

    category = lookup_merchant_category_for_offer(offer_id)
    updated = await project_offer_outcome_to_graph(
        session_id=session_id,
        offer_id=offer_id,
        status=status,
        merchant_category=category,
    )
    if not updated:
        return OfferOutcomeResponse(
            success=False, offer_id=offer_id, error="OFFER_NOT_FOUND"
        )
    return OfferOutcomeResponse(success=True, offer_id=offer_id, status=status)


@router.get("/wallet/{session_id}", response_model=WalletResponse)
async def wallet_endpoint(session_id: str) -> WalletResponse:
    """Get wallet balance and transaction history."""
    return WalletResponse(**get_wallet(session_id))


@router.post("/conflict/resolve", response_model=ConflictResolveResponse)
async def conflict_endpoint(request: ConflictResolveRequest) -> ConflictResolveResponse:
    """
    Standalone conflict resolution endpoint.
    Useful for dashboard integration and debugging.
    """
    result = resolve_conflict(
        merchant_id=request.merchant_id,
        user_social_pref=request.user_social_pref.value,
        current_txn_rate=request.current_txn_rate,
        current_dt=request.current_dt,
        active_coupon=request.active_coupon,
    )
    return ConflictResolveResponse(
        recommendation=result.recommendation,
        framing_band=result.framing_band,
        coupon_mechanism=result.coupon_mechanism,
        reason=result.reason,
        recheck_in_minutes=result.recheck_in_minutes,
    )
