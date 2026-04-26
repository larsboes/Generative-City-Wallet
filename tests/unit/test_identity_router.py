from __future__ import annotations

import asyncio
from types import SimpleNamespace

from spark.models.api import ContinuityResetRequest
import spark.routers.identity as identity_router


def test_identity_router_reset_rotate_path():
    response = asyncio.run(
        identity_router.continuity_reset_endpoint(
            ContinuityResetRequest(
                session_id="sess-router-001",
                continuity_hint="prev-hint",
                opt_out=False,
            )
        )
    )
    assert response.session_id == "sess-router-001"
    assert response.opt_out is False
    assert response.continuity_id is not None
    assert response.continuity_hint is not None
    assert response.expires_at.endswith("Z")


def test_identity_router_opt_out_path():
    called = {"purged": False}

    async def _purge_session_data(*, session_id: str):
        called["purged"] = session_id == "sess-router-002"
        return {"sessions_deleted": 1}

    fake_repo = SimpleNamespace(
        is_available=lambda: True,
        purge_session_data=_purge_session_data,
    )
    original_get_repository = identity_router.get_repository
    identity_router.get_repository = lambda: fake_repo
    response = asyncio.run(
        identity_router.continuity_reset_endpoint(
            ContinuityResetRequest(
                session_id="sess-router-002",
                continuity_hint="prev-hint",
                opt_out=True,
            )
        )
    )
    identity_router.get_repository = original_get_repository
    assert response.session_id == "sess-router-002"
    assert response.opt_out is True
    assert response.continuity_id is None
    assert response.continuity_hint is None
    assert response.source == "opt_out"
    assert called["purged"] is True
