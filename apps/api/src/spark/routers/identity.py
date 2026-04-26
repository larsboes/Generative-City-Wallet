from __future__ import annotations

from fastapi import APIRouter

from spark.models.api import ContinuityResetRequest, ContinuityResetResponse
from spark.services.identity_continuity import reset_continuity_identity

router = APIRouter(prefix="/api/identity", tags=["identity"])


@router.post("/continuity/reset", response_model=ContinuityResetResponse)
async def continuity_reset_endpoint(request: ContinuityResetRequest):
    result = reset_continuity_identity(
        session_id=request.session_id,
        continuity_hint=request.continuity_hint,
        opt_out=request.opt_out,
    )
    return ContinuityResetResponse(
        session_id=result.session_id,
        continuity_id=result.continuity_id,
        continuity_hint=result.continuity_hint,
        source=result.source,
        expires_at=result.expires_at_iso,
        reset_applied=result.reset_applied,
        opt_out=result.opt_out,
    )
