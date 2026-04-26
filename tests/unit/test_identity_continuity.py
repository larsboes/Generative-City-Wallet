from __future__ import annotations

from datetime import datetime, timezone

from spark.services.identity_continuity import resolve_continuity_identity


def test_continuity_identity_uses_hint_when_provided():
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
    result = resolve_continuity_identity(
        session_id="sess-001",
        continuity_hint="user-stable-hint",
        now=now,
    )
    assert result.continuity_id.startswith("cid_")
    assert result.source == "hinted_pseudonym"
    assert result.expires_at_iso == "2026-05-26T12:00:00Z"


def test_continuity_identity_falls_back_to_session_id():
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
    result = resolve_continuity_identity(
        session_id="sess-002",
        continuity_hint=None,
        now=now,
    )
    assert result.continuity_id.startswith("cid_")
    assert result.source == "session_fallback"
    assert result.expires_at_iso == "2026-05-26T12:00:00Z"
