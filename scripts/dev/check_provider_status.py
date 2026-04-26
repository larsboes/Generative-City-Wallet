"""
Quick local check for external context providers.

Usage:
  python scripts/dev/check_provider_status.py
  python scripts/dev/check_provider_status.py --base-url http://localhost:8000 --grid-cell STR-MITTE-047
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def _status_label(is_live: bool) -> str:
    return "LIVE" if is_live else "FALLBACK"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Spark external provider status from one endpoint."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Spark backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--grid-cell",
        default="STR-MITTE-047",
        help="Grid cell to inspect (default: STR-MITTE-047)",
    )
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/api/context/provider-status"
    try:
        resp = httpx.get(url, params={"grid_cell": args.grid_cell}, timeout=5.0)
        resp.raise_for_status()
    except Exception as exc:
        print(f"ERROR: failed to fetch provider status from {url}: {exc}")
        return 1

    payload = resp.json()
    weather = payload.get("weather", {})
    external = payload.get("external", {}) or {}
    place = external.get("place", {}) or {}
    events = external.get("events", {}) or {}

    weather_live = bool(weather.get("provider_available"))
    places_live = bool(place.get("provider_available"))
    events_live = bool(events.get("provider_available"))

    print("Spark External Provider Status")
    print(f"- Grid Cell: {payload.get('grid_cell')}")
    print(
        f"- Weather: {_status_label(weather_live)} "
        f"(source={weather.get('source')}, cache_hit={weather.get('cache_hit')}, "
        f"weather_need={weather.get('weather_need')}, temp_c={weather.get('temp_celsius')})"
    )
    print(
        f"- Places:  {_status_label(places_live)} "
        f"(source={place.get('source')}, nearby_count={place.get('nearby_place_count')}, "
        f"avg_busyness={place.get('avg_busyness')}, top={place.get('popular_place_name')})"
    )
    print(
        f"- Events:  {_status_label(events_live)} "
        f"(source={events.get('source')}, tonight={events.get('events_tonight_count')}, "
        f"nearest={events.get('nearest_event_name')}, cache_hit={events.get('cache_hit')}, "
        f"error_reason={events.get('error_reason')}, http_status={events.get('http_status')})"
    )

    print("\nRaw JSON:")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
