from __future__ import annotations

import time

from neo4j import AsyncSession

from spark.graph import queries as Q
from spark.graph.client import safe_execute
from spark.graph.models import PreferenceScore


class PreferenceGraphRepository:
    async def reinforce_category(
        self,
        *,
        session_id: str,
        category: str,
        delta: float,
        base_weight: float = 0.5,
        source_type: str = "interaction",
        decay_rate: float = 0.01,
        now: float | None = None,
    ) -> float | None:
        ts = now if now is not None else time.time()

        async def _run(s: AsyncSession) -> float | None:
            res = await s.run(
                Q.REINFORCE_CATEGORY,
                session_id=session_id,
                category=category,
                delta=delta,
                base_weight=base_weight,
                source_type=source_type,
                decay_rate=decay_rate,
                now=ts,
            )
            row = await res.single()
            return float(row["weight"]) if row else None

        return await safe_execute(_run, fallback=None, op_name="reinforce_category")

    async def get_preference_scores(
        self,
        session_id: str,
        *,
        limit: int = 10,
    ) -> list[PreferenceScore]:
        async def _run(s: AsyncSession) -> list[PreferenceScore]:
            res = await s.run(
                Q.GET_PREFERENCE_SCORES, session_id=session_id, limit=limit
            )
            rows = await res.data()
            return [
                PreferenceScore(
                    category=r["category"],
                    weight=float(r["weight"] or 0.0),
                    source_type=r.get("source_type"),
                    last_reinforced_unix=r.get("last_reinforced_unix"),
                )
                for r in rows
            ]

        return await safe_execute(_run, fallback=[], op_name="get_preference_scores")

    async def decay_stale_preferences(
        self,
        *,
        stale_after_days: int,
        default_decay_rate: float,
        now_unix: float | None = None,
    ) -> dict[str, float]:
        now_ts = now_unix if now_unix is not None else time.time()
        stale_cutoff = now_ts - (stale_after_days * 24 * 3600)

        async def _run(s: AsyncSession) -> dict[str, float]:
            res = await s.run(
                Q.DECAY_STALE_PREFERENCES,
                stale_cutoff_unix=stale_cutoff,
                now_unix=now_ts,
                default_decay_rate=default_decay_rate,
            )
            row = await res.single()
            return {
                "stale_after_days": float(stale_after_days),
                "default_decay_rate": float(default_decay_rate),
                "edges_touched": float((row and row["edges_touched"]) or 0.0),
            }

        return await safe_execute(
            _run,
            fallback={
                "stale_after_days": float(stale_after_days),
                "default_decay_rate": float(default_decay_rate),
                "edges_touched": 0.0,
            },
            op_name="decay_stale_preferences",
        )

