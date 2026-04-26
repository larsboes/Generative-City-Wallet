from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from spark.config import PROJECT_ROOT

DEFAULT_URL = "https://api.lu.ma/discover/get-paginated-events"


def _extract_events(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
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

    location = raw.get("location")
    city_from_location = location.get("city") if isinstance(location, dict) else None
    city = raw.get("city") or city_from_location or fallback_city

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
    return sorted(merged.values(), key=lambda e: str(e.get("start_at", "")))


def _resolve_seed_path(seed_file: str) -> Path:
    path = Path(seed_file)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def load_discover_seed_events(
    *,
    lat: float,
    lng: float,
    radius: int = 50000,
    period: str = "future",
    pages: int = 1,
    timeout: float = 8.0,
    city: str = "Stuttgart",
    seed_file: str = "resources/mock_events_stuttgart.json",
    replace_discover: bool = False,
    cookie: str = "",
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    origin: str = "https://lu.ma",
    referer: str = "https://lu.ma/discover",
    dry_run: bool = False,
) -> dict[str, Any]:
    seed_path = _resolve_seed_path(seed_file)
    seed_path.parent.mkdir(parents=True, exist_ok=True)

    fetched_events: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(max(pages, 1)):
        params: dict[str, Any] = {
            "lat": lat,
            "lng": lng,
            "radius": radius,
            "period": period,
        }
        if cursor:
            params["pagination_cursor"] = cursor
        url = f"{DEFAULT_URL}?{urlencode(params)}"
        headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
            "Origin": origin,
            "Referer": referer,
        }
        if cookie:
            headers["Cookie"] = cookie
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        page_events = _extract_events(payload)
        for raw in page_events:
            normalized = _normalize_event(raw, city)
            if normalized:
                fetched_events.append(normalized)

        cursor = _extract_cursor(payload)
        if not cursor:
            break

    dedup_incoming = list({e["id"]: e for e in fetched_events}.values())
    seed = _load_seed(seed_path)
    existing = seed["events"]
    if replace_discover:
        existing = [e for e in existing if not str(e.get("id", "")).startswith("luma-discover-")]

    merged = _merge_events(existing, dedup_incoming)
    summary = {
        "fetched": len(fetched_events),
        "normalized_unique": len(dedup_incoming),
        "seed_total_after_merge": len(merged),
        "seed_file": str(seed_path),
        "dry_run": dry_run,
    }

    if dry_run:
        return summary

    seed["events"] = merged
    seed_path.write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Load Luma Discover events into local seed JSON (demo-only).")
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
    parser.add_argument("--cookie", default="", help="Optional Cookie header copied from browser session")
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

    summary = load_discover_seed_events(
        lat=args.lat,
        lng=args.lng,
        radius=args.radius,
        period=args.period,
        pages=args.pages,
        timeout=args.timeout,
        city=args.city,
        seed_file=args.seed_file,
        replace_discover=args.replace_discover,
        cookie=args.cookie,
        user_agent=args.user_agent,
        origin=args.origin,
        referer=args.referer,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
