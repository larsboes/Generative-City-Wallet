#!/usr/bin/env python3
"""
POST a sample IntentVector to the Spark API (composite + optional generate).
Usage:
  uv run python scripts/dev/smoke_intent_vector.py
  SPARK_API_BASE=http://127.0.0.1:8000 uv run python scripts/dev/smoke_intent_vector.py --generate
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

SAMPLE_INTENT = {
    "grid_cell": "STR-MITTE-047",
    "movement_mode": "browsing",
    "time_bucket": "tuesday_lunch",
    "weather_need": "warmth_seeking",
    "social_preference": "quiet",
    "price_tier": "mid",
    "recent_categories": ["cafe"],
    "dwell_signal": False,
    "battery_low": False,
    "session_id": "smoke-intent-vector",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test IntentVector → API")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SPARK_API_BASE", "http://127.0.0.1:8000"),
        help="FastAPI base URL",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Also POST /api/offers/generate (needs full GenerateOfferRequest body)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{base}/api/context/composite", json=SAMPLE_INTENT)
        print("POST /api/context/composite", r.status_code)
        if r.status_code != 200:
            print(r.text[:2000])
            return 1
        data = r.json()
        print(
            json.dumps(
                {
                    "timestamp": data.get("timestamp"),
                    "merchant": data.get("merchant", {}).get("id"),
                },
                indent=2,
            )
        )

        if args.generate:
            merchant_id = (data.get("merchant") or {}).get("id")
            if not merchant_id:
                print(
                    "No merchant in composite response; cannot --generate",
                    file=sys.stderr,
                )
                return 1
            body = {"intent": SAMPLE_INTENT, "merchant_id": merchant_id}
            r2 = client.post(f"{base}/api/offers/generate", json=body)
            print("POST /api/offers/generate", r2.status_code)
            if r2.status_code != 200:
                print(r2.text[:2000])
                return 1
            offer = r2.json()
            print(
                json.dumps(
                    {
                        "offer_id": offer.get("offer_id"),
                        "merchant": offer.get("merchant"),
                    },
                    indent=2,
                )
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
