"""
GraphRepository — high-level read/write API over Neo4j.

All methods are fail-soft: on any driver error or when Neo4j is
unavailable they return a sensible empty/false fallback so the offer
pipeline can still produce results from SQLite + heuristics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

from neo4j import AsyncSession

from spark.graph import queries as Q
from spark.graph.client import is_available, safe_execute


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PreferenceScore:
    category: str
    weight: float
    source_type: Optional[str] = None
    last_reinforced_unix: Optional[float] = None


@dataclass(frozen=True)
class RecentOffer:
    offer_id: str
    merchant_id: str
    category: Optional[str]
    status: Optional[str]
    created_at_unix: Optional[float]


@dataclass(frozen=True)
class MerchantOfferStats:
    count: int
    last_unix: Optional[float]


# ── Repository ────────────────────────────────────────────────────────────────


class GraphRepository:
    """High-level domain methods over Neo4j. All methods fail soft."""

    # ── User session ─────────────────────────────────────────────────────────

    async def ensure_session(
        self, session_id: str, *, now: Optional[float] = None
    ) -> bool:
        if not session_id:
            return False
        ts = now if now is not None else time.time()

        async def _run(s: AsyncSession) -> bool:
            await s.run(Q.ENSURE_USER_SESSION, session_id=session_id, now=ts)
            return True

        return await safe_execute(_run, fallback=False, op_name="ensure_session")

    # ── Merchant catalogue ───────────────────────────────────────────────────

    async def upsert_merchant(
        self,
        merchant_id: str,
        name: str,
        category: str,
        grid_cell: str,
        address: Optional[str] = None,
    ) -> bool:
        async def _run(s: AsyncSession) -> bool:
            await s.run(
                Q.UPSERT_MERCHANT,
                merchant_id=merchant_id,
                name=name,
                category=category,
                grid_cell=grid_cell,
                address=address,
            )
            return True

        return await safe_execute(_run, fallback=False, op_name="upsert_merchant")

    # ── Offer write path ─────────────────────────────────────────────────────

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

    # ── Redemption + wallet ──────────────────────────────────────────────────

    async def write_redemption(
        self,
        *,
        session_id: str,
        offer_id: str,
        discount_value: float,
        discount_type: str,
        now: Optional[float] = None,
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
        now: Optional[float] = None,
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

    # ── Preference reinforcement ─────────────────────────────────────────────

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
        """Apply +/- delta to a (UserSession)-[:PREFERS]->(MerchantCategory) edge.

        Returns the new weight, or None on failure / unavailable graph.
        """
        ts = now if now is not None else time.time()

        async def _run(s: AsyncSession) -> Optional[float]:
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

    # ── Read path ────────────────────────────────────────────────────────────

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

    # ── Admin / debug ────────────────────────────────────────────────────────

    async def stats(self) -> dict[str, Any]:
        async def _run(s: AsyncSession) -> dict[str, Any]:
            res = await s.run(Q.GRAPH_STATS)
            row = await res.single()
            return dict(row) if row else {}

        return await safe_execute(_run, fallback={}, op_name="stats")

    async def cleanup_old_data(
        self, *, retention_days: int, now_unix: Optional[float] = None
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
                "offers_deleted": int(
                    (offers_row and offers_row["offers_deleted"]) or 0  # type: ignore[reportArgumentType]
                ),
                "contexts_deleted": int(
                    (offers_row and offers_row["contexts_deleted"]) or 0  # type: ignore[reportArgumentType]
                ),
                "redemptions_deleted": int(
                    (offers_row and offers_row["redemptions_deleted"]) or 0  # type: ignore[reportArgumentType]
                ),
                "wallet_events_deleted": int(
                    (offers_row and offers_row["wallet_events_deleted"]) or 0  # type: ignore[reportArgumentType]
                ),
                "sessions_deleted": int(
                    (sessions_row and sessions_row["sessions_deleted"]) or 0  # type: ignore[reportArgumentType]
                ),
                "preference_edges_deleted": int(
                    (pref_row and pref_row["preference_edges_deleted"]) or 0  # type: ignore[reportArgumentType]
                ),
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

    async def decay_stale_preferences(
        self,
        *,
        stale_after_days: int,
        default_decay_rate: float,
        now_unix: Optional[float] = None,
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
                "edges_touched": float((row and row["edges_touched"]) or 0.0),  # type: ignore[reportArgumentType]
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


# ── Module-level singleton accessor ──────────────────────────────────────────

_repository: Optional[GraphRepository] = None


def get_repository() -> GraphRepository:
    """Return the process-wide GraphRepository (lazy-initialized)."""
    global _repository
    if _repository is None:
        _repository = GraphRepository()
    return _repository
