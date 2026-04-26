from __future__ import annotations

from fastapi.testclient import TestClient

from spark.main import app


def test_identity_continuity_reset_rotate_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/identity/continuity/reset",
            json={
                "session_id": "sess-int-identity-001",
                "continuity_hint": "old-hint",
                "opt_out": False,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "sess-int-identity-001"
    assert body["opt_out"] is False
    assert body["continuity_id"].startswith("cid_")
    assert body["continuity_hint"].startswith("hint_")
    assert body["source"] in {"hinted_pseudonym", "session_fallback"}
    assert body["expires_at"].endswith("Z")
    assert body["reset_applied"] is True


def test_identity_continuity_reset_opt_out_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/identity/continuity/reset",
            json={
                "session_id": "sess-int-identity-002",
                "continuity_hint": "old-hint",
                "opt_out": True,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "sess-int-identity-002"
    assert body["opt_out"] is True
    assert body["continuity_id"] is None
    assert body["continuity_hint"] is None
    assert body["source"] == "opt_out"
    assert body["expires_at"].endswith("Z")
