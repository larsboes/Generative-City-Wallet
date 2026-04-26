"""
Tests for the composite state builder's graph integration.

Validates that:
- When the graph has preferences, they are used in CompositeContextState.user.preference_scores.
- When the graph is empty / unavailable, the heuristic fallback is used.
- Graph fallback never breaks the existing offer endpoint.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from spark.graph.repository import (
    MerchantOfferStats,
    PreferenceScore,
    RecentOffer,
)
from spark.models.context import IntentVector
from spark.services import composite as composite_module


class StubRepository:
    """A test double for GraphRepository — drives both preference branches."""

    def __init__(self, *, available: bool, prefs: list[PreferenceScore] | None = None):
        self._available = available
        self._prefs = prefs or []
        self.write_calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return self._available

    async def ensure_session(self, session_id: str, **_: Any) -> bool:
        return self._available

    async def get_preference_scores(self, session_id: str, *, limit: int = 10):
        return self._prefs

    async def session_offer_count(self, **_: Any) -> int:
        return 0

    async def merchant_offer_stats(self, **_: Any) -> MerchantOfferStats:
        return MerchantOfferStats(count=0, last_unix=None)

    async def recent_offers(self, **_: Any) -> list[RecentOffer]:
        return []

    async def write_offer(self, **kwargs: Any) -> bool:
        self.write_calls.append(kwargs)
        return self._available


@pytest.fixture
def intent() -> IntentVector:
    return IntentVector(
        grid_cell="STR-MITTE-047",
        movement_mode="browsing",
        time_bucket="tuesday_lunch",
        weather_need="warmth_seeking",
        social_preference="quiet",
        price_tier="mid",
        recent_categories=["cafe"],
        dwell_signal=False,
        battery_low=False,
        session_id="sess-test-composite",
        activity_signal="active_recently",
        activity_source="movement_inferred",
        activity_confidence=0.95,
    )


async def test_composite_uses_graph_preferences_when_available(intent, monkeypatch):
    prefs = [
        PreferenceScore(category="cafe", weight=0.91, source_type="redemption"),
        PreferenceScore(category="bakery", weight=0.42, source_type="interaction"),
    ]
    repo = StubRepository(available=True, prefs=prefs)

    state = await composite_module.build_composite_state(
        intent=intent,
        merchant_id="MERCHANT_001",
        graph_repo=repo,  # type: ignore[arg-type]
    )

    assert state.user.preference_scores == {"cafe": 0.91, "bakery": 0.42}
    assert state.user.continuity_id is not None
    assert state.user.continuity_id.startswith("cid_")
    assert state.user.continuity_source in {"hinted_pseudonym", "session_fallback"}
    assert state.user.continuity_expires_at is not None
    assert any(p.field == "continuity_id" for p in state.user.intent_provenance)
    assert any(p.field == "activity_signal" for p in state.user.intent_provenance)
    assert any(p.field == "activity_confidence" for p in state.user.intent_provenance)
    assert state.user.intent.activity_confidence == 0.7
    trust_step = next(
        item
        for item in (state.decision_trace.trace if state.decision_trace else [])
        if item.code == "intent_trust_normalization"
    )
    fields = trust_step.metadata.get("fields", {})
    assert "activity_signal" in fields
    assert "activity_confidence" in fields


async def test_composite_falls_back_when_graph_empty(intent):
    repo = StubRepository(available=True, prefs=[])

    state = await composite_module.build_composite_state(
        intent=intent,
        merchant_id="MERCHANT_001",
        graph_repo=repo,  # type: ignore[arg-type]
    )

    assert state.user.preference_scores == composite_module.DEFAULT_PREFERENCE_SCORES
    assert state.external is not None
    assert isinstance(state.external.place.provider_available, bool)
    assert isinstance(state.external.events.provider_available, bool)


async def test_composite_falls_back_when_graph_unavailable(intent):
    repo = StubRepository(available=False, prefs=[])

    state = await composite_module.build_composite_state(
        intent=intent,
        merchant_id="MERCHANT_001",
        graph_repo=repo,  # type: ignore[arg-type]
    )

    assert state.user.preference_scores == composite_module.DEFAULT_PREFERENCE_SCORES


def test_offer_endpoint_works_without_neo4j(monkeypatch):
    """End-to-end: the offer endpoint should still work when Neo4j is down."""
    # Force the graph layer into an unavailable state.
    from spark.graph import client as graph_client

    monkeypatch.setattr(graph_client, "_driver", None)
    monkeypatch.setattr(graph_client, "_unavailable", True)

    from spark.main import app

    with TestClient(app) as client:
        payload = {
            "intent": {
                "grid_cell": "STR-MITTE-047",
                "movement_mode": "browsing",
                "time_bucket": "tuesday_lunch",
                "weather_need": "warmth_seeking",
                "social_preference": "quiet",
                "price_tier": "mid",
                "recent_categories": [],
                "dwell_signal": False,
                "battery_low": False,
                "session_id": "test-fallback-001",
            },
            "merchant_id": "MERCHANT_001",
        }
        resp = client.post("/api/offers/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        # Either a real offer or a structured DO_NOT_RECOMMEND, never a 500.
        assert "offer_id" in data or "reason" in data
