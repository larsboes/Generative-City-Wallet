from __future__ import annotations

import asyncio
from types import SimpleNamespace

from spark.models.api import GenerateOfferRequest
from spark.services.location_cells import latlon_to_h3
from spark.services.offer_pipeline import generate_offer_pipeline

TEST_CELL = latlon_to_h3(48.137154, 11.576124)


def _request(confidence: float) -> GenerateOfferRequest:
    return GenerateOfferRequest.model_validate(
        {
            "intent": {
                "grid_cell": TEST_CELL,
                "movement_mode": "browsing",
                "time_bucket": "tuesday_lunch",
                "weather_need": "neutral",
                "social_preference": "quiet",
                "price_tier": "mid",
                "recent_categories": [],
                "dwell_signal": False,
                "battery_low": False,
                "session_id": "sess-ocr-confidence",
            },
            "ocr_transit": {
                "city": "Berlin",
                "district": "Kreuzberg",
                "line": "U1",
                "station": "Kottbusser Tor",
                "transit_delay_minutes": 8,
                "must_return_by": "2026-04-26T10:15:00Z",
                "confidence": confidence,
            },
        }
    )


def test_low_confidence_ocr_not_used_for_gating(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_build_composite_state(
        intent,
        merchant_id,
        demo_overrides,
        transit_delay_minutes,
        must_return_by,
    ):
        captured["transit_delay_minutes"] = transit_delay_minutes
        captured["must_return_by"] = must_return_by
        return SimpleNamespace(
            session_id=intent.session_id,
            merchant=SimpleNamespace(id="MERCHANT_001", category="cafe"),
            conflict_resolution=SimpleNamespace(recommendation="DO_NOT_RECOMMEND"),
            decision_trace=None,
        )

    class FakeRules:
        async def validate(self, **kwargs):  # noqa: ANN003
            return SimpleNamespace(
                accepted=True,
                hard_violations=[],
                soft_violations=[],
                metadata={},
                to_audit_dict=lambda: {},
            )

    monkeypatch.setattr(
        "spark.services.offer_pipeline.build_composite_state",
        fake_build_composite_state,
    )
    monkeypatch.setattr(
        "spark.services.offer_pipeline.GraphValidationService", FakeRules
    )

    result = asyncio.run(generate_offer_pipeline(_request(confidence=0.4)))
    assert result["offer"] is None
    assert captured["transit_delay_minutes"] is None
    assert captured["must_return_by"] is None


def test_high_confidence_ocr_used_for_gating(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_build_composite_state(
        intent,
        merchant_id,
        demo_overrides,
        transit_delay_minutes,
        must_return_by,
    ):
        captured["transit_delay_minutes"] = transit_delay_minutes
        captured["must_return_by"] = must_return_by
        return SimpleNamespace(
            session_id=intent.session_id,
            merchant=SimpleNamespace(id="MERCHANT_001", category="cafe"),
            conflict_resolution=SimpleNamespace(recommendation="DO_NOT_RECOMMEND"),
            decision_trace=None,
        )

    class FakeRules:
        async def validate(self, **kwargs):  # noqa: ANN003
            return SimpleNamespace(
                accepted=True,
                hard_violations=[],
                soft_violations=[],
                metadata={},
                to_audit_dict=lambda: {},
            )

    monkeypatch.setattr(
        "spark.services.offer_pipeline.build_composite_state",
        fake_build_composite_state,
    )
    monkeypatch.setattr(
        "spark.services.offer_pipeline.GraphValidationService", FakeRules
    )

    result = asyncio.run(generate_offer_pipeline(_request(confidence=0.95)))
    assert result["offer"] is None
    assert captured["transit_delay_minutes"] == 8
    assert captured["must_return_by"] == "2026-04-26T10:15:00Z"
