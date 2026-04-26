from __future__ import annotations

import time
from typing import Any

import httpx

from spark.config import (
    CONTEXT_PROVIDER_TIMEOUT_SECONDS,
    GOOGLE_MAPS_API_KEY,
    PLACES_CACHE_TTL_SECONDS,
)

_cache: dict[str, dict[str, Any]] = {}
_cache_ts: dict[str, float] = {}

_FALLBACK = {
    "source": "fallback_defaults",
    "provider_available": False,
    "nearby_place_count": 0,
    "avg_rating": None,
    "avg_busyness": None,
    "popular_place_name": None,
}

_MUNICH_CENTER = (48.137154, 11.576124)


def _grid_to_lat_lon(grid_cell: str) -> tuple[float, float]:
    try:
        import h3
        return h3.cell_to_latlng(grid_cell)
    except Exception:
        return _MUNICH_CENTER


def _map_to_busyness(place: dict[str, Any]) -> float:
    # A lightweight proxy; Places API (New) does not expose true live occupancy.
    ratings_total = float(place.get("userRatingCount", 0))
    return max(0.0, min(1.0, ratings_total / 2000.0))


def _summarize_places(places: list[dict[str, Any]]) -> dict[str, Any]:
    places = places[:10]
    ratings = [float(item.get("rating", 0.0)) for item in places if item.get("rating")]
    busyness = [_map_to_busyness(item) for item in places]
    sorted_by_popularity = sorted(
        places, key=lambda p: float(p.get("userRatingCount", 0)), reverse=True
    )
    top_name = None
    if sorted_by_popularity:
        display = sorted_by_popularity[0].get("displayName", {})
        top_name = display.get("text") or sorted_by_popularity[0].get("name")

    return {
        "source": "google_places_new",
        "provider_available": True,
        "nearby_place_count": len(places),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "avg_busyness": round(sum(busyness) / len(busyness), 3) if busyness else None,
        "popular_place_name": top_name,
    }


async def get_places_context(grid_cell: str) -> dict[str, Any]:
    now = time.time()
    if (
        grid_cell in _cache
        and (now - _cache_ts.get(grid_cell, 0.0)) < PLACES_CACHE_TTL_SECONDS
    ):
        return _cache[grid_cell]

    if not GOOGLE_MAPS_API_KEY:
        result = {**_FALLBACK}
        _cache[grid_cell] = result
        _cache_ts[grid_cell] = now
        return result

    lat, lon = _grid_to_lat_lon(grid_cell)
    try:
        async with httpx.AsyncClient(timeout=CONTEXT_PROVIDER_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                "https://places.googleapis.com/v1/places:searchNearby",
                headers={
                    "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": ",".join(
                        [
                            "places.displayName",
                            "places.rating",
                            "places.userRatingCount",
                            "places.types",
                        ]
                    ),
                },
                json={
                    "includedTypes": ["restaurant", "cafe", "bar"],
                    "maxResultCount": 10,
                    "locationRestriction": {
                        "circle": {
                            "center": {"latitude": lat, "longitude": lon},
                            "radius": 300.0,
                        }
                    },
                },
            )
            resp.raise_for_status()
            payload = resp.json()

        result = _summarize_places(payload.get("places", []))
    except Exception:
        result = {**_FALLBACK}

    _cache[grid_cell] = result
    _cache_ts[grid_cell] = now
    return result
