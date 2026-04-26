from __future__ import annotations

import asyncio

from spark.models.api import ContinuityResetRequest
from spark.routers.identity import continuity_reset_endpoint


def test_identity_router_reset_rotate_path():
    response = asyncio.run(
        continuity_reset_endpoint(
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
    response = asyncio.run(
        continuity_reset_endpoint(
            ContinuityResetRequest(
                session_id="sess-router-002",
                continuity_hint="prev-hint",
                opt_out=True,
            )
        )
    )
    assert response.session_id == "sess-router-002"
    assert response.opt_out is True
    assert response.continuity_id is None
    assert response.continuity_hint is None
    assert response.source == "opt_out"
