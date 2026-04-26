"""
Run one maintenance cycle for Neo4j user graph.

Use this script from cron/CI as a scheduler target.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from spark.config import (
    GRAPH_PREF_DECAY_MAX_GAP_HOURS,
    GRAPH_PREF_DECAY_DEFAULT_RATE,
    GRAPH_PREF_DECAY_STALE_AFTER_DAYS,
    GRAPH_PREF_RETENTION_INTERACTION_DAYS,
    GRAPH_PREF_RETENTION_WALLET_SEED_DAYS,
    GRAPH_RETENTION_DAYS,
)
from spark.graph import close_graph, init_graph
from spark.graph.repository import get_repository
from spark.repositories.graph_event import (
    acquire_graph_event_idempotency_key,
    get_latest_graph_event_timestamp,
)
from spark.repositories.preference_event import (
    cleanup_preference_update_log,
    record_learning_metric,
)
from spark.services.wave import cleanup_expired_waves


def _hours_since(timestamp: str | None) -> float | None:
    if not timestamp:
        return None
    normalized = timestamp.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


async def _run(
    retention_days: int,
    stale_after_days: int,
    decay_rate: float,
    decay_max_gap_hours: int,
) -> dict:
    connected = await init_graph()
    if not connected:
        return {"connected": False, "cleanup": {}, "decay": {}}

    repo = get_repository()
    cleanup = await repo.cleanup_old_data(retention_days=retention_days)
    decay = await repo.decay_stale_preferences(
        stale_after_days=stale_after_days,
        default_decay_rate=decay_rate,
    )
    acquire_graph_event_idempotency_key(
        event_type="maintenance_decay_run",
        session_id=None,
        offer_id=None,
        source="maintenance",
        source_event_id=datetime.now(timezone.utc).isoformat(),
    )
    wallet_seed_pruned = cleanup_preference_update_log(
        retention_days=GRAPH_PREF_RETENTION_WALLET_SEED_DAYS,
        source_prefix="wallet_seed:",
    )
    interaction_pruned = cleanup_preference_update_log(
        retention_days=GRAPH_PREF_RETENTION_INTERACTION_DAYS,
        source_prefix=None,
    )
    last_decay_run = get_latest_graph_event_timestamp(event_type="maintenance_decay_run")
    last_decay_age_hours = _hours_since(last_decay_run)
    decay_gap_alarm = bool(
        last_decay_age_hours is not None and last_decay_age_hours > decay_max_gap_hours
    )
    record_learning_metric(
        metric_name="maintenance_decay_gap_hours",
        metric_value=float(last_decay_age_hours or 0.0),
        metric_group="maintenance",
    )
    if decay_gap_alarm:
        record_learning_metric(
            metric_name="maintenance_decay_gap_alarm",
            metric_value=1.0,
            metric_group="maintenance",
        )
    wave_cleanup = cleanup_expired_waves()
    await close_graph()
    return {
        "connected": True,
        "cleanup": cleanup,
        "decay": decay,
        "retention": {
            "wallet_seed_pruned": wallet_seed_pruned,
            "interaction_pruned": interaction_pruned,
        },
        "health": {
            "last_decay_run": last_decay_run,
            "last_decay_age_hours": last_decay_age_hours,
            "decay_gap_alarm": decay_gap_alarm,
            "decay_max_gap_hours": decay_max_gap_hours,
        },
        "wave_cleanup": {"expired_rows": wave_cleanup},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run graph cleanup + preference decay."
    )
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
    parser.add_argument(
        "--decay-max-gap-hours",
        type=int,
        default=GRAPH_PREF_DECAY_MAX_GAP_HOURS,
        help="Raise health alarm when decay run age exceeds this threshold.",
    )
    args = parser.parse_args()
    result = asyncio.run(
        _run(
            args.retention_days,
            args.stale_after_days,
            args.decay_rate,
            args.decay_max_gap_hours,
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
