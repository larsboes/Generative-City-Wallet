"""
OpenWeatherMap integration for Stuttgart.
Falls back to realistic Stuttgart defaults when no API key is set.
"""

import time
from datetime import datetime

import httpx

from spark.config import (
    CONTEXT_PROVIDER_TIMEOUT_SECONDS,
    OPENWEATHER_API_KEY,
    STUTTGART_CITY_ID,
    WEATHER_CACHE_TTL_SECONDS,
)

# ── In-memory cache ───────────────────────────────────────────────────────────

_cache: dict[str, dict] = {}
_cache_ts: float = 0


# ── Stuttgart fallback defaults (realistic spring day) ─────────────────────────

STUTTGART_DEFAULTS = {
    "weather_condition": "overcast",
    "temp_celsius": 11.0,
    "feels_like_celsius": 8.0,
    "weather_need": "warmth_seeking",
    "vibe_signal": "cozy",
    "humidity": 72,
    "wind_speed": 3.2,
    "source": "fallback_defaults",
    "provider_available": False,
    "cache_hit": False,
}


def classify_weather_need(temp: float, condition: str, humidity: int = 50) -> str:
    """Map weather conditions to user needs."""
    condition_lower = condition.lower()

    if (
        "rain" in condition_lower
        or "drizzle" in condition_lower
        or "thunderstorm" in condition_lower
    ):
        return "shelter_seeking"
    if temp < 12:
        return "warmth_seeking"
    if temp > 25 or (temp > 22 and humidity > 60):
        return "refreshment_seeking"
    return "neutral"


def classify_vibe_signal(weather_need: str, temp: float, hour: int) -> str:
    """Derive vibe signal from weather + time."""
    if weather_need == "warmth_seeking":
        return "cozy"
    if weather_need == "refreshment_seeking":
        return "energetic" if hour < 17 else "refreshing"
    if hour >= 18:
        return "energetic"
    return "neutral"


async def get_stuttgart_weather() -> dict:
    """Fetch current Stuttgart weather. Returns cached result within TTL."""
    global _cache, _cache_ts

    now = time.time()
    if _cache and (now - _cache_ts) < WEATHER_CACHE_TTL_SECONDS:
        return {**_cache, "cache_hit": True}

    if not OPENWEATHER_API_KEY:
        _cache = STUTTGART_DEFAULTS.copy()
        _cache_ts = now
        return _cache

    try:
        async with httpx.AsyncClient(
            timeout=CONTEXT_PROVIDER_TIMEOUT_SECONDS
        ) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "id": STUTTGART_CITY_ID,
                    "appid": OPENWEATHER_API_KEY,
                    "units": "metric",
                    "lang": "de",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        condition = data["weather"][0]["main"]
        wind_speed = data.get("wind", {}).get("speed", 0)
        hour = datetime.now().hour

        weather_need = classify_weather_need(temp, condition, humidity)
        vibe_signal = classify_vibe_signal(weather_need, temp, hour)

        result = {
            "weather_condition": condition.lower(),
            "temp_celsius": round(temp, 1),
            "feels_like_celsius": round(feels_like, 1),
            "weather_need": weather_need,
            "vibe_signal": vibe_signal,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "source": "openweathermap",
            "provider_available": True,
            "cache_hit": False,
        }

        _cache = result
        _cache_ts = now
        return result

    except Exception:
        # Fallback to defaults on any API error
        _cache = STUTTGART_DEFAULTS.copy()
        _cache_ts = now
        return _cache
