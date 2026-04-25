"""
Run one maintenance cycle for Neo4j user graph.

Use this script from cron/CI as a scheduler target.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from spark.config import (
    GRAPH_PREF_DECAY_DEFAULT_RATE,
    GRAPH_PREF_DECAY_STALE_AFTER_DAYS,
    GRAPH_RETENTION_DAYS,
)
from spark.graph import close_graph, init_graph
from spark.graph.repository import get_repository


async def _run(retention_days: int, stale_after_days: int, decay_rate: float) -> dict:
    connected = await init_graph()
    if not connected:
        return {"connected": False, "cleanup": {}, "decay": {}}

    repo = get_repository()
    cleanup = await repo.cleanup_old_data(retention_days=retention_days)
    decay = await repo.decay_stale_preferences(
        stale_after_days=stale_after_days,
        default_decay_rate=decay_rate,
    )
    await close_graph()
    return {"connected": True, "cleanup": cleanup, "decay": decay}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run graph cleanup + preference decay.")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=GRAPH_RETENTION_DAYS,
        help="Retention for graph artifacts.",
    )
    parser.add_argument(
        "--stale-after-days",
        type=int,
        default=GRAPH_PREF_DECAY_STALE_AFTER_DAYS,
        help="Age threshold before preference decay applies.",
    )
    parser.add_argument(
        "--decay-rate",
        type=float,
        default=GRAPH_PREF_DECAY_DEFAULT_RATE,
        help="Daily linear decay rate for stale preference edges.",
    )
    args = parser.parse_args()
    result = asyncio.run(
        _run(args.retention_days, args.stale_after_days, args.decay_rate)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
