"""
Append a local seeded event used by the Spark events provider.

Usage:
  python scripts/dev/ingest_mock_events.py --name "Founder Meetup" --start-at "2026-04-26T19:30:00Z"
  python scripts/dev/ingest_mock_events.py --name "Afterwork" --start-at "2026-04-26T18:00:00Z" --city Stuttgart --file resources/mock_events_stuttgart.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append one event into local seeded events JSON."
    )
    parser.add_argument("--name", required=True, help="Event name")
    parser.add_argument(
        "--start-at",
        required=True,
        help="Event start timestamp in ISO-8601 (UTC), e.g. 2026-04-26T19:30:00Z",
    )
    parser.add_argument(
        "--city", default="Stuttgart", help="Event city (default: Stuttgart)"
    )
    parser.add_argument(
        "--file",
        default="resources/mock_events_stuttgart.json",
        help="Seed events JSON path (default: resources/mock_events_stuttgart.json)",
    )
    args = parser.parse_args()

    path = Path(args.file)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"events": []}

    if isinstance(payload, list):
        events = payload
        payload = {"events": events}
    else:
        events = payload.setdefault("events", [])

    events.append(
        {
            "id": f"seed-{uuid4().hex[:10]}",
            "name": args.name,
            "city": args.city,
            "start_at": args.start_at,
        }
    )

    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Seeded event added to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
