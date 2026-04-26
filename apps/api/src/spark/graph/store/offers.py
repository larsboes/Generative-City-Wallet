from __future__ import annotations

import time
from typing import Optional

from neo4j import AsyncSession

from spark.graph.queries import offers as Q
from spark.graph.client import safe_execute
from spark.graph.models import MerchantOfferStats, RecentOffer


class OfferGraphRepository:
    async def write_offer(
        self,
        *,
        offer_id: str,
        session_id: str,
        merchant_id: str,
        merchant_name: str,
        merchant_category: str,
        framing_band: Optional[str],
        density_signal: Optional[str],
        drop_pct: Optional[float],
        distance_m: Optional[float],
        coupon_type: Optional[str],
        discount_pct: Optional[float],
        timestamp: str,
        grid_cell: Optional[str],
        movement_mode: Optional[str],
        time_bucket: Optional[str],
        weather_need: Optional[str],
        vibe_signal: Optional[str],
        temp_c: Optional[float],
        social_preference: Optional[str],
        occupancy_pct: Optional[float],
        predicted_occupancy_pct: Optional[float],
        now: Optional[float] = None,
    ) -> bool:
        ts = now if now is not None else time.time()

        async def _run(s: AsyncSession) -> bool:
            await s.run(
                Q.WRITE_OFFER,
                offer_id=offer_id,
                session_id=session_id,
                merchant_id=merchant_id,
                merchant_name=merchant_name,
                merchant_category=merchant_category,
                framing_band=framing_band,
                density_signal=density_signal,
                drop_pct=drop_pct,
                distance_m=distance_m,
                coupon_type=coupon_type,
                discount_pct=discount_pct,
                timestamp=timestamp,
                grid_cell=grid_cell,
                movement_mode=movement_mode,
                time_bucket=time_bucket,
                weather_need=weather_need,
                vibe_signal=vibe_signal,
                temp_c=temp_c,
                social_preference=social_preference,
                occupancy_pct=occupancy_pct,
                predicted_occupancy_pct=predicted_occupancy_pct,
                now=ts,
            )
            return True

        return await safe_execute(_run, fallback=False, op_name="write_offer")

    async def record_offer_outcome(
        self,
        *,
        session_id: str,
        offer_id: str,
        status: str,
        now: Optional[float] = None,
    ) -> bool:
        ts = now if now is not None else time.time()

        async def _run(s: AsyncSession) -> bool:
            await s.run(
                Q.RECORD_OFFER_OUTCOME,
                session_id=session_id,
                offer_id=offer_id,
                status=status,
                now=ts,
            )
            return True

        return await safe_execute(_run, fallback=False, op_name="record_offer_outcome")

    async def merchant_offer_stats(
        self,
        *,
        session_id: str,
        merchant_id: str,
        since_unix: float,
    ) -> MerchantOfferStats:
        async def _run(s: AsyncSession) -> MerchantOfferStats:
            res = await s.run(
                Q.COUNT_RECENT_OFFERS_FOR_MERCHANT,
                session_id=session_id,
                merchant_id=merchant_id,
                since_unix=since_unix,
            )
            row = await res.single()
            if row is None:
                return MerchantOfferStats(count=0, last_unix=None)
            return MerchantOfferStats(
                count=int(row["count"] or 0),
                last_unix=row["last_unix"],
            )

        return await safe_execute(
            _run,
            fallback=MerchantOfferStats(count=0, last_unix=None),
            op_name="merchant_offer_stats",
        )

    async def recent_offers(
        self, *, session_id: str, limit: int = 10
    ) -> list[RecentOffer]:
        async def _run(s: AsyncSession) -> list[RecentOffer]:
            res = await s.run(Q.GET_RECENT_OFFERS, session_id=session_id, limit=limit)
            rows = await res.data()
            return [
                RecentOffer(
                    offer_id=r["offer_id"],
                    merchant_id=r["merchant_id"],
                    category=r.get("category"),
                    status=r.get("status"),
                    created_at_unix=r.get("created_at_unix"),
                )
                for r in rows
            ]

        return await safe_execute(_run, fallback=[], op_name="recent_offers")
