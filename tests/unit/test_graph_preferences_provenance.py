from __future__ import annotations

import asyncio

from spark.graph.models import PreferenceScore
from spark.routers.graph import session_preferences


def test_session_preferences_exposes_provenance_fields(monkeypatch):
    class FakeRepo:
        async def get_preference_scores(self, session_id: str, *, limit: int = 10):
            return [
                PreferenceScore(
                    category="cafe",
                    weight=0.62,
                    source_type="wallet_seed:wallet_pass",
                    last_reinforced_unix=1714100000.0,
                    decay_rate=0.04,
                    source_confidence=0.78,
                    artifact_count=3,
                )
            ]

    monkeypatch.setattr("spark.routers.graph.get_repository", lambda: FakeRepo())
    monkeypatch.setattr("spark.routers.graph.is_available", lambda: True)
    monkeypatch.setattr(
        "spark.routers.graph.get_recent_preference_update_events",
        lambda session_id, limit=10: [
            {
                "session_id": session_id,
                "category": "cafe",
                "source_type": "wallet_seed:wallet_pass",
                "event_type": "wallet_seed:wallet_pass:cafe",
                "event_key": "evt-1",
                "delta": 0.15,
                "outcome": "applied",
                "created_at": "2026-04-26T00:00:00+00:00",
            }
        ],
    )

    result = asyncio.run(
        session_preferences(
            "sess-provenance", limit=5, include_attribution=True, event_limit=5
        )
    )
    assert result["available"] is True
    assert result["scores"][0]["source_type"] == "wallet_seed:wallet_pass"
    assert result["scores"][0]["decay_rate"] == 0.04
    assert result["scores"][0]["source_confidence"] == 0.78
    assert result["scores"][0]["artifact_count"] == 3
    assert result["attribution"][0]["outcome"] == "applied"
