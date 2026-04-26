"""
Domain interfaces (Abstract Base Classes).

These define the contracts that services depend on.
Infrastructure (SQLite, Neo4j) provides the concrete implementations.
The domain layer MUST NOT import from routers, services, or repositories.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


# ── Value objects returned by interfaces ──────────────────────────────────────
# Defined here so interfaces stay self-contained (no spark imports).


@dataclass(frozen=True)
class SessionState:
    """Offer-decision session state returned by IOfferDecisionRepository."""

    unresolved_offer_id: str | None
    offers_last_24h: int


@dataclass(frozen=True)
class CandidateMerchant:
    """A merchant candidate for the offer-decision pipeline."""

    merchant_id: str
    merchant_category: str
    merchant_grid_cell: str | None = None
    merchant_lat: float | None = None
    merchant_lon: float | None = None


# ── Repository interfaces ─────────────────────────────────────────────────────


class IOfferDecisionRepository(ABC):
    """Contract for the offer-decision persistence layer."""

    @abstractmethod
    def get_session_state(
        self, *, session_id: str, now: datetime
    ) -> SessionState: ...

    @abstractmethod
    def list_candidate_merchants(
        self, *, grid_cell: str
    ) -> list[CandidateMerchant]: ...


class IDensityRepository(ABC):
    """Contract for density/transaction data access."""

    @abstractmethod
    def get_hourly_transaction_stats(
        self, merchant_id: str, hour_of_week: int
    ) -> tuple[float, int]: ...

    @abstractmethod
    def get_latest_transaction_rate(
        self, merchant_id: str, hour_of_week: int
    ) -> float: ...

    @abstractmethod
    def get_historical_avg_at_arrival_hour(
        self, merchant_id: str, arrival_hour_of_week: int
    ) -> float | None: ...

    @abstractmethod
    def list_merchants_for_density(self) -> list[dict[str, Any]]: ...


class IVenueRepository(ABC):
    """Contract for venue persistence operations."""

    @abstractmethod
    def get_venue_row(self, merchant_id: str) -> Any: ...

    @abstractmethod
    def list_venue_rows(
        self,
        *,
        categories: list[str] | None = None,
        city: str | None = None,
        query_limit: int = 100,
    ) -> list[Any]: ...


class IGraphRepository(ABC):
    """Contract for the knowledge-graph facade (Neo4j or in-memory)."""

    @abstractmethod
    async def ensure_session(
        self, session_id: str, *, now: Optional[float] = None
    ) -> bool: ...

    @abstractmethod
    async def get_preference_scores(
        self, session_id: str, *, limit: int = 10
    ) -> list[Any]: ...
