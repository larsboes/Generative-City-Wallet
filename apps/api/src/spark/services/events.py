from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from spark.config import (
    CONTEXT_PROVIDER_TIMEOUT_SECONDS,
    LUMA_API_KEY,
    LUMA_BASE_URL,
    LUMA_CACHE_TTL_SECONDS,
    LUMA_SEED_EVENTS_PATH,
    PROJECT_ROOT,
)

_cache: dict[str, dict[str, Any]] = {}
_cache_ts: dict[str, float] = {}
_seed_events: list[dict[str, Any]] | None = None

_FALLBACK = {
    "source": "fallback_defaults",
    "provider_available": False,
    "events_tonight_count": 0,
    "nearest_event_name": None,
    "cache_hit": False,
    "error_reason": None,
    "http_status": None,
}


def _city_for_grid(grid_cell: str) -> str:
    return "München"


def _resolve_seed_path() -> Path:
    candidate = Path(LUMA_SEED_EVENTS_PATH)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _load_seed_events() -> list[dict[str, Any]]:
    global _seed_events
    if _seed_events is not None:
        return _seed_events

    path = _resolve_seed_path()
    if not path.exists():
        _seed_events = []
        return _seed_events

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_events = (
            payload.get("events", payload) if isinstance(payload, dict) else payload
        )
        if not isinstance(raw_events, list):
            _seed_events = []
            return _seed_events
        _seed_events = [e for e in raw_events if isinstance(e, dict)]
        return _seed_events
    except Exception:
        _seed_events = []
        return _seed_events


def _events_for_today(events: list[dict[str, Any]], city: str) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    city_lower = city.lower()
    tonight: list[dict[str, Any]] = []
    for event in events:
        event_city = str(event.get("city", "")).lower()
        if event_city and event_city != city_lower:
            continue

        starts_at = event.get("start_at")
        if not starts_at:
            continue
        try:
            dt = datetime.fromisoformat(str(starts_at).replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.date() == today:
            tonight.append(event)
    return tonight


async def get_luma_event_context(grid_cell: str) -> dict[str, Any]:
    now = time.time()
    if (
        grid_cell in _cache
        and (now - _cache_ts.get(grid_cell, 0.0)) < LUMA_CACHE_TTL_SECONDS
    ):
        return {**_cache[grid_cell], "cache_hit": True}

    city = _city_for_grid(grid_cell)
    if not LUMA_API_KEY:
        seeded_events = _load_seed_events()
        tonight = _events_for_today(seeded_events, city)
        if tonight:
            result = {
                "source": "seeded_local",
                "provider_available": True,
                "events_tonight_count": len(tonight),
                "nearest_event_name": tonight[0].get("name"),
                "cache_hit": False,
                "error_reason": None,
                "http_status": None,
            }
        else:
            result = {**_FALLBACK, "error_reason": "missing_api_key"}
        _cache[grid_cell] = result
        _cache_ts[grid_cell] = now
        return result

    try:
        async with httpx.AsyncClient(
            timeout=CONTEXT_PROVIDER_TIMEOUT_SECONDS
        ) as client:
            resp = await client.get(
                f"{LUMA_BASE_URL}/events",
                params={"city": city, "limit": 20},
                headers={"x-luma-api-key": LUMA_API_KEY, "x-api-key": LUMA_API_KEY},
            )
            resp.raise_for_status()
            payload = resp.json()

        events = payload.get("events", [])
        if not isinstance(events, list):
            raise ValueError("Luma response missing 'events' list")
        tonight = _events_for_today(events, city)

        result = {
            "source": "luma",
            "provider_available": True,
            "events_tonight_count": len(tonight),
            "nearest_event_name": tonight[0].get("name") if tonight else None,
            "cache_hit": False,
            "error_reason": None,
            "http_status": resp.status_code,
        }
    except Exception as exc:
        status = (
            exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        )
        result = {
            **_FALLBACK,
            "error_reason": exc.__class__.__name__,
            "http_status": status,
        }

    _cache[grid_cell] = result
    _cache_ts[grid_cell] = now
    return result
