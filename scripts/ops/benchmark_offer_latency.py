"""
Benchmark `/api/offers/generate` latency and report p95.

Runs two benchmark passes by default:
1) Neo4j enabled
2) Neo4j disabled (fallback path)

Each pass starts a fresh local API process with the requested env.
"""

from __future__ import annotations

import argparse
import os
import statistics
import subprocess
import time
import uuid
from typing import Any

import httpx

from spark.services.location_cells import latlon_to_h3


def _payload(index: int) -> dict[str, Any]:
    return {
        "intent": {
            "grid_cell": latlon_to_h3(48.137154, 11.576124),
            "movement_mode": "browsing",
            "time_bucket": "tuesday_lunch",
            "weather_need": "warmth_seeking",
            "social_preference": "quiet",
            "price_tier": "mid",
            "recent_categories": ["cafe"],
            "dwell_signal": False,
            "battery_low": False,
            "session_id": f"bench-{index}-{uuid.uuid4()}",
        },
        "merchant_id": "MERCHANT_001",
    }


def _p95(samples_ms: list[float]) -> float:
    if not samples_ms:
        return 0.0
    sorted_samples = sorted(samples_ms)
    idx = int(0.95 * (len(sorted_samples) - 1))
    return sorted_samples[idx]


def _wait_until_healthy(base_url: str, timeout_s: float) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            resp = httpx.get(f"{base_url}/api/health", timeout=1.5)
            if resp.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("API did not become healthy in time.")


def _run_pass(
    *,
    neo4j_enabled: bool,
    requests: int,
    warmup: int,
    port: int,
    startup_timeout_s: float,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["NEO4J_ENABLED"] = "true" if neo4j_enabled else "false"
    env.setdefault("NEO4J_STARTUP_TIMEOUT_S", "2.0")
    base_url = f"http://127.0.0.1:{port}"

    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "spark.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
    )
    try:
        _wait_until_healthy(base_url, timeout_s=startup_timeout_s)
        latencies_ms: list[float] = []
        ok = 0
        failed = 0

        with httpx.Client(timeout=20.0) as client:
            for i in range(warmup):
                client.post(f"{base_url}/api/offers/generate", json=_payload(i))

            for i in range(requests):
                body = _payload(i + warmup)
                start = time.perf_counter()
                try:
                    resp = client.post(f"{base_url}/api/offers/generate", json=body)
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    latencies_ms.append(elapsed_ms)
                    if resp.status_code == 200:
                        ok += 1
                    else:
                        failed += 1
                except Exception:
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    latencies_ms.append(elapsed_ms)
                    failed += 1

        return {
            "neo4j_enabled": neo4j_enabled,
            "requests": requests,
            "ok": ok,
            "failed": failed,
            "avg_ms": round(statistics.mean(latencies_ms), 2) if latencies_ms else 0.0,
            "p50_ms": round(statistics.median(latencies_ms), 2)
            if latencies_ms
            else 0.0,
            "p95_ms": round(_p95(latencies_ms), 2),
            "max_ms": round(max(latencies_ms), 2) if latencies_ms else 0.0,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark offer endpoint p95 latency."
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=80,
        help="Measured requests per pass (default: 80)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Warmup requests per pass (default: 5)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8010,
        help="Port for temporary benchmark server (default: 8010)",
    )
    parser.add_argument(
        "--startup-timeout-s",
        type=float,
        default=12.0,
        help="Server startup timeout per pass (default: 12s)",
    )
    args = parser.parse_args()

    print("Running benchmark pass: Neo4j enabled")
    enabled = _run_pass(
        neo4j_enabled=True,
        requests=args.requests,
        warmup=args.warmup,
        port=args.port,
        startup_timeout_s=args.startup_timeout_s,
    )
    print("Running benchmark pass: Neo4j disabled")
    disabled = _run_pass(
        neo4j_enabled=False,
        requests=args.requests,
        warmup=args.warmup,
        port=args.port,
        startup_timeout_s=args.startup_timeout_s,
    )

    print("\n=== Offer Latency Benchmark ===")
    for row in (enabled, disabled):
        mode = "neo4j_on" if row["neo4j_enabled"] else "neo4j_off"
        print(
            f"{mode}: req={row['requests']} ok={row['ok']} fail={row['failed']} "
            f"avg={row['avg_ms']}ms p50={row['p50_ms']}ms p95={row['p95_ms']}ms max={row['max_ms']}ms"
        )
    delta = round(enabled["p95_ms"] - disabled["p95_ms"], 2)
    print(f"p95 delta (on - off): {delta}ms")


if __name__ == "__main__":
    main()
