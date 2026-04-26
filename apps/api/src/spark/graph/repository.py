"""
GraphRepository facade — high-level read/write API over Neo4j.

Internally delegates to concern-specific repository modules. Public callers
can continue using `GraphRepository` while the package stays decomposed.
"""

from __future__ import annotations

from typing import Optional

from spark.graph.client import is_available
from spark.graph.models import MerchantOfferStats, PreferenceScore, RecentOffer
from spark.graph.store.merchants import MerchantGraphRepository
from spark.graph.store.offers import OfferGraphRepository
from spark.graph.store.ops import OpsGraphRepository
from spark.graph.store.preferences import PreferenceGraphRepository
from spark.graph.store.redemptions import RedemptionGraphRepository
from spark.graph.store.sessions import SessionGraphRepository


class GraphRepository:
    """High-level domain facade over Neo4j. All sub-repositories fail soft."""

    def __init__(self) -> None:
        self._sessions = SessionGraphRepository()
        self._merchants = MerchantGraphRepository()
        self._offers = OfferGraphRepository()
        self._preferences = PreferenceGraphRepository()
        self._redemptions = RedemptionGraphRepository()
        self._ops = OpsGraphRepository()

    async def ensure_session(
        self, session_id: str, *, now: Optional[float] = None
    ) -> bool:
        return await self._sessions.ensure_session(session_id, now=now)

    async def session_offer_count(self, *, session_id: str, since_unix: float) -> int:
        return await self._sessions.session_offer_count(
            session_id=session_id, since_unix=since_unix
        )

    async def upsert_merchant(
        self,
        merchant_id: str,
        name: str,
        category: str,
        grid_cell: str,
        address: Optional[str] = None,
    ) -> bool:
        return await self._merchants.upsert_merchant(
            merchant_id=merchant_id,
            name=name,
            category=category,
            grid_cell=grid_cell,
            address=address,
        )

    async def write_offer(self, **kwargs) -> bool:
        return await self._offers.write_offer(**kwargs)

    async def record_offer_outcome(
        self,
        *,
        session_id: str,
        offer_id: str,
        status: str,
        now: Optional[float] = None,
    ) -> bool:
        return await self._offers.record_offer_outcome(
            session_id=session_id, offer_id=offer_id, status=status, now=now
        )

    async def merchant_offer_stats(
        self,
        *,
        session_id: str,
        merchant_id: str,
        since_unix: float,
    ) -> MerchantOfferStats:
        return await self._offers.merchant_offer_stats(
            session_id=session_id, merchant_id=merchant_id, since_unix=since_unix
        )

    async def recent_offers(
        self, *, session_id: str, limit: int = 10
    ) -> list[RecentOffer]:
        return await self._offers.recent_offers(session_id=session_id, limit=limit)

    async def write_redemption(
        self,
        *,
        session_id: str,
        offer_id: str,
        discount_value: float,
        discount_type: str,
        now: Optional[float] = None,
    ) -> bool:
        return await self._redemptions.write_redemption(
            session_id=session_id,
            offer_id=offer_id,
            discount_value=discount_value,
            discount_type=discount_type,
            now=now,
        )

    async def write_wallet_event(
        self,
        *,
        offer_id: str,
        amount_eur: float,
        now: Optional[float] = None,
    ) -> bool:
        return await self._redemptions.write_wallet_event(
            offer_id=offer_id, amount_eur=amount_eur, now=now
        )

    async def reinforce_category(
        self,
        *,
        session_id: str,
        category: str,
        delta: float,
        base_weight: float = 0.5,
        source_type: str = "interaction",
        decay_rate: float = 0.01,
        now: Optional[float] = None,
    ) -> Optional[float]:
        return await self._preferences.reinforce_category(
            session_id=session_id,
            category=category,
            delta=delta,
            base_weight=base_weight,
            source_type=source_type,
            decay_rate=decay_rate,
            now=now,
        )

    async def get_preference_scores(
        self, session_id: str, *, limit: int = 10
    ) -> list[PreferenceScore]:
        return await self._preferences.get_preference_scores(
            session_id=session_id, limit=limit
        )

    async def decay_stale_preferences(
        self,
        *,
        stale_after_days: int,
        default_decay_rate: float,
        now_unix: Optional[float] = None,
    ) -> dict[str, float]:
        return await self._preferences.decay_stale_preferences(
            stale_after_days=stale_after_days,
            default_decay_rate=default_decay_rate,
            now_unix=now_unix,
        )

    async def stats(self) -> dict:
        return await self._ops.stats()

    async def cleanup_old_data(
        self, *, retention_days: int, now_unix: Optional[float] = None
    ) -> dict[str, int]:
        return await self._ops.cleanup_old_data(
            retention_days=retention_days, now_unix=now_unix
        )

    async def migration_status(self) -> list[dict]:
        return await self._ops.migration_status()

    @staticmethod
    def is_available() -> bool:
        return is_available()


_repository: Optional[GraphRepository] = None


def get_repository() -> GraphRepository:
    global _repository
    if _repository is None:
        _repository = GraphRepository()
    return _repository


__all__ = [
    "GraphRepository",
    "MerchantOfferStats",
    "PreferenceScore",
    "RecentOffer",
    "get_repository",
]
