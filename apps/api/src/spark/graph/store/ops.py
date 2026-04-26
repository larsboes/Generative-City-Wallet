from __future__ import annotations

import time
from typing import Any

from neo4j import AsyncSession

from spark.graph.queries import ops as Q
from spark.graph.client import is_available, safe_execute


class OpsGraphRepository:
    async def stats(self) -> dict[str, Any]:
        async def _run(s: AsyncSession) -> dict[str, Any]:
            res = await s.run(Q.GRAPH_STATS)
            row = await res.single()
            return dict(row) if row else {}

        return await safe_execute(_run, fallback={}, op_name="stats")

    async def cleanup_old_data(
        self, *, retention_days: int, now_unix: float | None = None
    ) -> dict[str, int]:
        cutoff_unix = (now_unix if now_unix is not None else time.time()) - (
            retention_days * 24 * 3600
        )

        async def _run(s: AsyncSession) -> dict[str, int]:
            offers_res = await s.run(Q.CLEANUP_OLD_OFFERS, cutoff_unix=cutoff_unix)
            offers_row = await offers_res.single()
            sessions_res = await s.run(
                Q.CLEANUP_STALE_SESSIONS, cutoff_unix=cutoff_unix
            )
            sessions_row = await sessions_res.single()
            pref_res = await s.run(
                Q.CLEANUP_OLD_PREFERENCE_EDGES, cutoff_unix=cutoff_unix
            )
            pref_row = await pref_res.single()

            return {
                "retention_days": int(retention_days),
                "offers_deleted": int((offers_row and offers_row["offers_deleted"]) or 0),
                "contexts_deleted": int((offers_row and offers_row["contexts_deleted"]) or 0),
                "redemptions_deleted": int((offers_row and offers_row["redemptions_deleted"]) or 0),
                "wallet_events_deleted": int((offers_row and offers_row["wallet_events_deleted"]) or 0),
                "sessions_deleted": int((sessions_row and sessions_row["sessions_deleted"]) or 0),
                "preference_edges_deleted": int((pref_row and pref_row["preference_edges_deleted"]) or 0),
            }

        return await safe_execute(
            _run,
            fallback={
                "retention_days": int(retention_days),
                "offers_deleted": 0,
                "contexts_deleted": 0,
                "redemptions_deleted": 0,
                "wallet_events_deleted": 0,
                "sessions_deleted": 0,
                "preference_edges_deleted": 0,
            },
            op_name="cleanup_old_data",
        )

    async def migration_status(self) -> list[dict[str, Any]]:
        async def _run(s: AsyncSession) -> list[dict[str, Any]]:
            res = await s.run(Q.GET_MIGRATION_STATUS)
            rows = await res.data()
            return [
                {
                    "id": r["id"],
                    "description": r.get("description"),
                    "applied_at_unix": r.get("applied_at_unix"),
                }
                for r in rows
            ]

        return await safe_execute(_run, fallback=[], op_name="migration_status")

    @staticmethod
    def is_available() -> bool:
        return is_available()

