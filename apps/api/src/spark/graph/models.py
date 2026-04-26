"""Typed graph DTOs used by Neo4j repositories and graph-aware services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PreferenceScore:
    category: str
    weight: float
    source_type: Optional[str] = None
    last_reinforced_unix: Optional[float] = None
    decay_rate: Optional[float] = None
    source_confidence: Optional[float] = None
    artifact_count: Optional[int] = None


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

