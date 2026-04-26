from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GraphHealthResponse(BaseModel):
    available: bool
    metrics: dict[str, Any]


class GraphStatsResponse(BaseModel):
    available: bool
    stats: dict[str, Any]


class GraphPreferenceScoreItem(BaseModel):
    category: str
    weight: float
    source_type: str | None = None
    last_reinforced_unix: float | None = None
    decay_rate: float | None = None
    source_confidence: float | None = None
    artifact_count: int | None = None


class SessionPreferencesResponse(BaseModel):
    session_id: str
    available: bool
    scores: list[GraphPreferenceScoreItem]
    attribution: list[dict[str, Any]] = Field(default_factory=list)


class RecentOfferItem(BaseModel):
    offer_id: str
    merchant_id: str
    category: str | None = None
    status: str | None = None
    created_at_unix: float | None = None


class SessionRecentOffersResponse(BaseModel):
    session_id: str
    available: bool
    offers: list[RecentOfferItem]


class GraphCleanupResponse(BaseModel):
    available: bool
    cleanup: dict[str, int]


class GraphDecayResponse(BaseModel):
    available: bool
    decay: dict[str, float]


class GraphMigrationsResponse(BaseModel):
    available: bool
    migrations: list[dict[str, Any]]
