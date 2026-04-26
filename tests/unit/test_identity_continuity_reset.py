from __future__ import annotations

from datetime import datetime, timezone

import spark.services.identity_continuity as continuity_module
from spark.services.identity_continuity import reset_continuity_identity


def test_continuity_reset_rotate_returns_new_hint_and_id(monkeypatch):
    monkeypatch.setattr(
        continuity_module,
        "acquire_graph_event_idempotency_key",
        lambda **kwargs: True,  # noqa: ARG005
    )
    result = reset_continuity_identity(
        session_id="sess-reset-001",
        continuity_hint="old-hint",
        opt_out=False,
        now=datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result.session_id == "sess-reset-001"
    assert result.opt_out is False
    assert result.reset_applied is True
    assert result.continuity_hint is not None
    assert result.continuity_hint.startswith("hint_")
    assert result.continuity_id is not None
    assert result.continuity_id.startswith("cid_")


def test_continuity_reset_opt_out_disables_hint_and_id(monkeypatch):
    monkeypatch.setattr(
        continuity_module,
        "acquire_graph_event_idempotency_key",
        lambda **kwargs: True,  # noqa: ARG005
    )
    result = reset_continuity_identity(
        session_id="sess-reset-002",
        continuity_hint="old-hint",
        opt_out=True,
        now=datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result.session_id == "sess-reset-002"
    assert result.opt_out is True
    assert result.reset_applied is True
    assert result.continuity_hint is None
    assert result.continuity_id is None
    assert result.source == "opt_out"
