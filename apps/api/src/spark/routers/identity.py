from __future__ import annotations

from fastapi import APIRouter, Depends

from spark.graph.repository import get_repository
from spark.models.api import (
    ClearProfileRequest,
    ClearProfileResponse,
    ContinuityResetRequest,
    ContinuityResetResponse,
)
from spark.repositories.identity import unlink_session
from spark.routers.errors import require_admin
from spark.services.identity_continuity import reset_continuity_identity

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])


@router.post("/continuity/reset", response_model=ContinuityResetResponse, dependencies=[Depends(require_admin)])
async def continuity_reset_endpoint(request: ContinuityResetRequest):
    result = reset_continuity_identity(
        session_id=request.session_id,
        continuity_hint=request.continuity_hint,
        opt_out=request.opt_out,
    )
    if request.opt_out:
        # Best-effort graph clear-down for opt-out; endpoint remains non-blocking
        # if graph is unavailable.
        repo = get_repository()
        if repo.is_available():
            await repo.purge_session_data(session_id=request.session_id)
    return ContinuityResetResponse(
        session_id=result.session_id,
        continuity_id=result.continuity_id,
        continuity_hint=result.continuity_hint,
        source=result.source,
        expires_at=result.expires_at_iso,
        reset_applied=result.reset_applied,
        opt_out=result.opt_out,
    )


@router.post(
    "/profile/clear",
    response_model=ClearProfileResponse,
    dependencies=[Depends(require_admin)],
)
async def clear_identity_profile(request: ClearProfileRequest):
    """Erase all behavioral data for a session from Neo4j and unlink continuity identity."""
    repo = get_repository()
    graph_result = await repo.clear_session_data(request.session_id)
    unlink_session(request.session_id)
    return ClearProfileResponse(
        session_id=request.session_id,
        graph_cleared=graph_result,
        identity_unlinked=True,
    )
