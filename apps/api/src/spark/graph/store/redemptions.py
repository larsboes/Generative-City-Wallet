from __future__ import annotations

import time

from neo4j import AsyncSession

from spark.graph.queries import redemptions as Q
from spark.graph.client import safe_execute


class RedemptionGraphRepository:
    async def write_redemption(
        self,
        *,
        session_id: str,
        offer_id: str,
        discount_value: float,
        discount_type: str,
        now: float | None = None,
    ) -> bool:
        ts = now if now is not None else time.time()

        async def _run(s: AsyncSession) -> bool:
            await s.run(
                Q.WRITE_REDEMPTION,
                session_id=session_id,
                offer_id=offer_id,
                discount_value=discount_value,
                discount_type=discount_type,
                now=ts,
            )
            return True

        return await safe_execute(_run, fallback=False, op_name="write_redemption")

    async def write_wallet_event(
        self,
        *,
        offer_id: str,
        amount_eur: float,
        now: float | None = None,
    ) -> bool:
        ts = now if now is not None else time.time()

        async def _run(s: AsyncSession) -> bool:
            await s.run(
                Q.WRITE_WALLET_EVENT,
                offer_id=offer_id,
                amount_eur=amount_eur,
                now=ts,
            )
            return True

        return await safe_execute(_run, fallback=False, op_name="write_wallet_event")
