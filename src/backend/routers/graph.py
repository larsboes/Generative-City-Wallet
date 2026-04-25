"""
Graph admin / debug endpoints.

Useful for the demo dashboard and operational checks. Read-only.
"""

from fastapi import APIRouter

from src.backend.graph import get_metrics, is_available
from src.backend.graph.repository import get_repository

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/health")
async def graph_health():
    """Lightweight health check + Neo4j metrics snapshot."""
    return {
        "available": is_available(),
        "metrics": get_metrics(),
    }


@router.get("/stats")
async def graph_stats():
    """Aggregate node/edge counts (used by ops dashboards)."""
    repo = get_repository()
    return {"available": is_available(), "stats": await repo.stats()}


@router.get("/sessions/{session_id}/preferences")
async def session_preferences(session_id: str, limit: int = 10):
    """Top preference scores for a given user session — for explainability."""
    repo = get_repository()
    scores = await repo.get_preference_scores(session_id, limit=limit)
    return {
        "session_id": session_id,
        "available": is_available(),
        "scores": [
            {
                "category": s.category,
                "weight": round(s.weight, 3),
                "source_type": s.source_type,
                "last_reinforced_unix": s.last_reinforced_unix,
            }
            for s in scores
        ],
    }


@router.get("/sessions/{session_id}/recent-offers")
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
