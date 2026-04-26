"""
Graph admin / debug endpoints.

Useful for the demo dashboard and operational checks. Read-only.
"""

from fastapi import APIRouter

from spark.models.api import WalletSeedRequest
from spark.repositories.redemption import get_recent_preference_update_events
from spark.config import (
    GRAPH_PREF_DECAY_DEFAULT_RATE,
    GRAPH_PREF_DECAY_STALE_AFTER_DAYS,
    GRAPH_RETENTION_DAYS,
)
from spark.graph import get_metrics, is_available
from spark.graph.repository import get_repository
from spark.models.graph_api import (
    GraphCleanupResponse,
    GraphDecayResponse,
    GraphHealthResponse,
    GraphMigrationsResponse,
    GraphStatsResponse,
    SessionPreferencesResponse,
    SessionRecentOffersResponse,
)
from spark.services.wallet_seed import apply_wallet_seed_preferences

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/health", response_model=GraphHealthResponse)
async def graph_health():
    """Lightweight health check + Neo4j metrics snapshot."""
    return {
        "available": is_available(),
        "metrics": get_metrics(),
    }


@router.get("/stats", response_model=GraphStatsResponse)
async def graph_stats():
    """Aggregate node/edge counts (used by ops dashboards)."""
    repo = get_repository()
    return {"available": is_available(), "stats": await repo.stats()}


@router.get("/sessions/{session_id}/preferences", response_model=SessionPreferencesResponse)
async def session_preferences(
    session_id: str, limit: int = 10, include_attribution: bool = False, event_limit: int = 10
):
    """Top preference scores for a given user session — for explainability."""
    repo = get_repository()
    scores = await repo.get_preference_scores(session_id, limit=limit)
    response = {
        "session_id": session_id,
        "available": is_available(),
        "scores": [
            {
                "category": s.category,
                "weight": round(s.weight, 3),
                "source_type": s.source_type,
                "last_reinforced_unix": s.last_reinforced_unix,
                "decay_rate": s.decay_rate,
                "source_confidence": s.source_confidence,
                "artifact_count": s.artifact_count,
            }
            for s in scores
        ],
    }
    if include_attribution:
        response["attribution"] = get_recent_preference_update_events(
            session_id=session_id,
            limit=max(1, min(event_limit, 100)),
        )
    return response


@router.get("/sessions/{session_id}/recent-offers", response_model=SessionRecentOffersResponse)
async def session_recent_offers(session_id: str, limit: int = 10):
    """Most recent offers for a user (graph view, for debugging the rules engine)."""
    repo = get_repository()
    offers = await repo.recent_offers(session_id=session_id, limit=limit)
    return {
        "session_id": session_id,
        "available": is_available(),
        "offers": [
            {
                "offer_id": o.offer_id,
                "merchant_id": o.merchant_id,
                "category": o.category,
                "status": o.status,
                "created_at_unix": o.created_at_unix,
            }
            for o in offers
        ],
    }


@router.post("/sessions/{session_id}/wallet-seed")
async def wallet_seed(session_id: str, request: WalletSeedRequest):
    """
    Seed category preferences from user-approved wallet artifacts.

    This is idempotent per (session_id, category) and uses `source_type=wallet_seed`
    with higher decay for cold-start priors.
    """
    result = await apply_wallet_seed_preferences(
        session_id=session_id,
        seeds=request.seeds,
    )
    return {
        "available": is_available(),
        "result": result.model_dump(mode="json"),
    }


@router.post("/cleanup", response_model=GraphCleanupResponse)
async def run_graph_cleanup(retention_days: int = GRAPH_RETENTION_DAYS):
    """Delete graph session/offer artifacts older than retention window."""
    repo = get_repository()
    stats = await repo.cleanup_old_data(retention_days=retention_days)
    return {
        "available": is_available(),
        "cleanup": stats,
    }


@router.post("/decay-preferences", response_model=GraphDecayResponse)
async def run_preference_decay(
    stale_after_days: int = GRAPH_PREF_DECAY_STALE_AFTER_DAYS,
    default_decay_rate: float = GRAPH_PREF_DECAY_DEFAULT_RATE,
):
    repo = get_repository()
    decay = await repo.decay_stale_preferences(
        stale_after_days=stale_after_days,
        default_decay_rate=default_decay_rate,
    )
    return {"available": is_available(), "decay": decay}


@router.get("/migrations", response_model=GraphMigrationsResponse)
async def graph_migrations():
    repo = get_repository()
    return {"available": is_available(), "migrations": await repo.migration_status()}
