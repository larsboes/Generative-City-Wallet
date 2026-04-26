from __future__ import annotations

from datetime import datetime

from spark.models.context import IntentVector
from spark.services.intent_trust import normalize_intent_vector


def _intent() -> IntentVector:
    return IntentVector.model_validate(
        {
            "grid_cell": "891f8d7a49bffff",
            "movement_mode": "browsing",
            "time_bucket": "friday_evening",
            "weather_need": "neutral",
            "social_preference": "quiet",
            "price_tier": "mid",
            "recent_categories": [],
            "dwell_signal": False,
            "battery_low": False,
            "session_id": "sess-trust-001",
            "activity_signal": "active_recently",
            "activity_source": "strava",
            "activity_confidence": 0.9,
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


def test_normalize_activity_fields_resets_when_source_none():
    intent = _intent().model_copy(
        update={
            "activity_source": "none",
            "activity_signal": "post_workout",
            "activity_confidence": 0.88,
        }
    )
    result = normalize_intent_vector(
        intent,
        now=datetime(2026, 4, 26, 9, 30),
        derived_weather_need="neutral",
    )
    assert result.intent.activity_signal == "none"
    assert result.intent.activity_confidence == 0.0
    signal_row = next(
        item for item in result.provenance if item.field == "activity_signal"
    )
    confidence_row = next(
        item for item in result.provenance if item.field == "activity_confidence"
    )
    assert signal_row.action == "overridden"
    assert confidence_row.action == "overridden"


def test_normalize_activity_confidence_caps_by_source():
    intent = _intent().model_copy(
        update={
            "activity_source": "movement_inferred",
            "activity_signal": "active_recently",
            "activity_confidence": 0.95,
        }
    )
    result = normalize_intent_vector(
        intent,
        now=datetime(2026, 4, 26, 9, 30),
        derived_weather_need="neutral",
    )
    assert result.intent.activity_confidence == 0.7
    confidence_row = next(
        item for item in result.provenance if item.field == "activity_confidence"
    )
    assert confidence_row.action == "overridden"


def test_normalize_activity_signal_consistency_for_no_source():
    intent = _intent().model_copy(
        update={
            "activity_source": "none",
            "activity_signal": "active_recently",
            "activity_confidence": 0.6,
        }
    )
    result = normalize_intent_vector(
        intent,
        now=datetime(2026, 4, 26, 9, 30),
        derived_weather_need="neutral",
    )
    assert result.intent.activity_signal == "none"
    assert result.intent.activity_confidence == 0.0
    signal_row = next(
        item for item in result.provenance if item.field == "activity_signal"
    )
    assert signal_row.action == "overridden"
