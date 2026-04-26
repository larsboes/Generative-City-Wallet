from __future__ import annotations

from typing import Any

from pydantic import BaseModel


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


class SessionPreferencesResponse(BaseModel):
    session_id: str
    available: bool
    scores: list[GraphPreferenceScoreItem]


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
