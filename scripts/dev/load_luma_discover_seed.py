"""
Load events from Luma Discover endpoint into local seed JSON.

This is a demo-only loader for non-official endpoint usage.
It keeps runtime integration stable by writing into local seeded events.

Usage:
  python scripts/dev/load_luma_discover_seed.py --lat 48.7758 --lng 9.1829 --radius 50000
  python scripts/dev/load_luma_discover_seed.py --lat 48.7758 --lng 9.1829 --pages 2 --city Stuttgart
  python scripts/dev/load_luma_discover_seed.py --lat 48.7758 --lng 9.1829 --cookie "session=..."
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_URL = "https://api.lu.ma/discover/get-paginated-events"


def _extract_events(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        # Accept multiple likely shapes to stay resilient for demo usage.
        for key in ("entries", "events", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def _extract_cursor(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("pagination_cursor", "next_cursor", "cursor", "next"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _to_iso_utc(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    text = str(value).strip()
    if not text:
        return None
    # Keep already-ISO values; normalize trailing Z handling downstream.
    return text


def _normalize_event(raw: dict[str, Any], fallback_city: str) -> dict[str, Any] | None:
    event_id = raw.get("id") or raw.get("event_id") or raw.get("api_id")
    name = raw.get("name") or raw.get("title")
    start_at = (
        _to_iso_utc(raw.get("start_at"))
        or _to_iso_utc(raw.get("start_time"))
        or _to_iso_utc(raw.get("startDate"))
    )

    if not event_id or not name or not start_at:
        return None

    city = (
        raw.get("city")
        or (raw.get("location") or {}).get("city") if isinstance(raw.get("location"), dict) else None
    ) or fallback_city

    return {
        "id": f"luma-discover-{event_id}",
        "name": str(name),
        "city": str(city),
        "start_at": str(start_at),
    }


def _load_seed(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"events": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {"events": payload}
    if isinstance(payload, dict):
        if not isinstance(payload.get("events"), list):
            payload["events"] = []
        return payload
    return {"events": []}


def _merge_events(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for event in existing:
        event_id = str(event.get("id", "")).strip()
        if event_id:
            merged[event_id] = event
    for event in incoming:
        merged[event["id"]] = event
    return sorted(
        merged.values(),
        key=lambda e: str(e.get("start_at", "")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Load Luma Discover events into local seed JSON.")
    parser.add_argument("--lat", required=True, type=float, help="Latitude")
    parser.add_argument("--lng", required=True, type=float, help="Longitude")
    parser.add_argument("--radius", type=int, default=50000, help="Search radius in meters (default: 50000)")
    parser.add_argument("--period", default="future", choices=["future", "past"], help="Event period (default: future)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to fetch (default: 1)")
    parser.add_argument("--timeout", type=float, default=8.0, help="HTTP timeout seconds (default: 8.0)")
    parser.add_argument("--city", default="Stuttgart", help="Fallback city for normalized events")
    parser.add_argument("--seed-file", default="resources/mock_events_stuttgart.json", help="Seed JSON file path")
    parser.add_argument("--replace-discover", action="store_true", help="Remove prior luma-discover-* events before merge")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and parse without writing file")
    parser.add_argument(
        "--cookie",
        default="",
        help="Optional Cookie header copied from browser session (for 403-protected discover endpoint)",
    )
    parser.add_argument(
        "--user-agent",
        default=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        help="User-Agent header to mimic browser traffic",
    )
    parser.add_argument("--origin", default="https://lu.ma", help="Origin header (default: https://lu.ma)")
    parser.add_argument("--referer", default="https://lu.ma/discover", help="Referer header (default: https://lu.ma/discover)")
    args = parser.parse_args()

    seed_path = Path(args.seed_file)
    seed_path.parent.mkdir(parents=True, exist_ok=True)

    fetched_events: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(max(args.pages, 1)):
        params: dict[str, Any] = {
            "lat": args.lat,
            "lng": args.lng,
            "radius": args.radius,
            "period": args.period,
        }
        if cursor:
            params["pagination_cursor"] = cursor
        url = f"{DEFAULT_URL}?{urlencode(params)}"
        headers = {
            "Accept": "application/json",
            "User-Agent": args.user_agent,
            "Origin": args.origin,
            "Referer": args.referer,
        }
        if args.cookie:
            headers["Cookie"] = args.cookie
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=args.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        page_events = _extract_events(payload)
        for raw in page_events:
            normalized = _normalize_event(raw, args.city)
            if normalized:
                fetched_events.append(normalized)

        cursor = _extract_cursor(payload)
        if not cursor:
            break

    # Deduplicate incoming by id.
    dedup_incoming = list({e["id"]: e for e in fetched_events}.values())

    seed = _load_seed(seed_path)
    existing = seed["events"]
    if args.replace_discover:
        existing = [e for e in existing if not str(e.get("id", "")).startswith("luma-discover-")]

    merged = _merge_events(existing, dedup_incoming)
    seed["events"] = merged

    if args.dry_run:
        print(
            json.dumps(
                {
                    "fetched": len(fetched_events),
                    "normalized_unique": len(dedup_incoming),
                    "seed_total_after_merge": len(merged),
                    "seed_file": str(seed_path),
                },
                indent=2,
            )
        )
        return 0

    seed_path.write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")
    print(f"Loaded {len(dedup_incoming)} discover events into {seed_path} (total events: {len(merged)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
