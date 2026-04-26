from __future__ import annotations

import time

from neo4j import AsyncSession

from spark.graph import queries as Q
from spark.graph.client import safe_execute


class SessionGraphRepository:
    async def ensure_session(
        self, session_id: str, *, now: float | None = None
    ) -> bool:
        if not session_id:
            return False
        ts = now if now is not None else time.time()

        async def _run(s: AsyncSession) -> bool:
            await s.run(Q.ENSURE_USER_SESSION, session_id=session_id, now=ts)
            return True

        return await safe_execute(_run, fallback=False, op_name="ensure_session")

    async def session_offer_count(self, *, session_id: str, since_unix: float) -> int:
        async def _run(s: AsyncSession) -> int:
            res = await s.run(
                Q.COUNT_SESSION_OFFERS,
                session_id=session_id,
                since_unix=since_unix,
            )
            row = await res.single()
            return int(row["count"]) if row else 0

        return await safe_execute(_run, fallback=0, op_name="session_offer_count")

