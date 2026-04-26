from __future__ import annotations

from datetime import datetime

from spark.models.context import IntentVector
from spark.services.intent_trust import normalize_intent_vector


def _intent() -> IntentVector:
    return IntentVector.model_validate(
        {
            "grid_cell": "STR-MITTE-047",
            "movement_mode": "browsing",
            "time_bucket": "friday_evening",
            "weather_need": "neutral",
            "social_preference": "quiet",
            "price_tier": "mid",
            "recent_categories": [],
            "dwell_signal": False,
            "battery_low": False,
            "session_id": "sess-trust-001",
        }
    )


def test_normalize_overrides_time_bucket_and_weather_need():
    result = normalize_intent_vector(
        _intent(),
        now=datetime(2026, 4, 26, 9, 30),
        derived_weather_need="warmth_seeking",
    )

    assert result.intent.time_bucket == "sunday_mid_morning"
    assert result.intent.weather_need.value == "warmth_seeking"

    time_row = next(item for item in result.provenance if item.field == "time_bucket")
    weather_row = next(item for item in result.provenance if item.field == "weather_need")
    assert time_row.action == "overridden"
    assert time_row.policy == "authoritative"
    assert weather_row.action == "overridden"
    assert weather_row.policy == "advisory"


def test_normalize_keeps_client_weather_need_when_server_signal_missing():
    result = normalize_intent_vector(
        _intent(),
        now=datetime(2026, 4, 26, 9, 30),
        derived_weather_need=None,
    )

    weather_row = next(item for item in result.provenance if item.field == "weather_need")
    assert result.intent.weather_need.value == "neutral"
    assert weather_row.action == "accepted"
    assert weather_row.source == "client_intent_fallback"
