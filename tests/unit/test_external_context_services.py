from __future__ import annotations

from pathlib import Path

import pytest

from spark.services import events, places, weather


@pytest.mark.asyncio
async def test_places_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(places, "GOOGLE_MAPS_API_KEY", "")
    places._cache.clear()
    places._cache_ts.clear()
    result = await places.get_places_context("891f8d7a49bffff")
    assert result["source"] == "fallback_defaults"
    assert result["provider_available"] is False


@pytest.mark.asyncio
async def test_luma_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(events, "LUMA_API_KEY", "")
    monkeypatch.setattr(
        events, "LUMA_SEED_EVENTS_PATH", "resources/does-not-exist.json"
    )
    events._cache = {}
    events._cache_ts = {}
    events._seed_events = None
    result = await events.get_luma_event_context("891f8d7a49bffff")
    assert result["source"] == "fallback_defaults"
    assert result["provider_available"] is False
    assert result["error_reason"] == "missing_api_key"


@pytest.mark.asyncio
async def test_luma_seeded_context_without_api_key(monkeypatch):
    monkeypatch.setattr(events, "LUMA_API_KEY", "")
    monkeypatch.setattr(
        events,
        "LUMA_SEED_EVENTS_PATH",
        "resources/mock_events_munich.json",
    )
    events._cache = {}
    events._cache_ts = {}
    events._seed_events = None
    assert (Path(events.PROJECT_ROOT) / events.LUMA_SEED_EVENTS_PATH).exists()
    result = await events.get_luma_event_context("891f8d7a49bffff")
    assert result["source"] in ("seeded_local", "fallback_defaults")


@pytest.mark.asyncio
async def test_weather_cache_hit_metadata(monkeypatch):
    monkeypatch.setattr(weather, "OPENWEATHER_API_KEY", "")
    weather._cache = {}
    weather._cache_ts = 0
    first = await weather.get_city_weather()
    second = await weather.get_city_weather()
    assert first["source"] == "fallback_defaults"
    assert second["cache_hit"] is True


def test_places_new_response_summary():
    payload = [
        {
            "displayName": {"text": "Cafe A"},
            "rating": 4.6,
            "userRatingCount": 1200,
        },
        {
            "displayName": {"text": "Bar B"},
            "rating": 4.2,
            "userRatingCount": 400,
        },
    ]
    result = places._summarize_places(payload)
    assert result["source"] == "google_places_new"
    assert result["provider_available"] is True
    assert result["nearby_place_count"] == 2
    assert result["popular_place_name"] == "Cafe A"
    assert result["avg_rating"] == 4.4
