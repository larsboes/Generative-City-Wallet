"""
Cypher query strings for the user knowledge graph.

Centralized as a stable import surface for repositories while query sources
are grouped by concern in sibling modules.
"""

from __future__ import annotations

from spark.graph.queries.merchants import UPSERT_MERCHANT
from spark.graph.queries.offers import (
    COUNT_RECENT_OFFERS_FOR_MERCHANT,
    GET_RECENT_OFFERS,
    RECORD_OFFER_OUTCOME,
    WRITE_OFFER,
)
from spark.graph.queries.ops import (
    CLEANUP_OLD_OFFERS,
    CLEANUP_OLD_PREFERENCE_EDGES,
    CLEANUP_STALE_SESSIONS,
    GET_MIGRATION_STATUS,
    GRAPH_STATS,
)
from spark.graph.queries.preferences import (
    DECAY_STALE_PREFERENCES,
    GET_PREFERENCE_SCORES,
    REINFORCE_CATEGORY,
)
from spark.graph.queries.redemptions import WRITE_REDEMPTION, WRITE_WALLET_EVENT
from spark.graph.queries.sessions import COUNT_SESSION_OFFERS, ENSURE_USER_SESSION

__all__ = [
    "CLEANUP_OLD_OFFERS",
    "CLEANUP_OLD_PREFERENCE_EDGES",
    "CLEANUP_STALE_SESSIONS",
    "COUNT_RECENT_OFFERS_FOR_MERCHANT",
    "COUNT_SESSION_OFFERS",
    "DECAY_STALE_PREFERENCES",
    "ENSURE_USER_SESSION",
    "GET_MIGRATION_STATUS",
    "GET_PREFERENCE_SCORES",
    "GET_RECENT_OFFERS",
    "GRAPH_STATS",
    "RECORD_OFFER_OUTCOME",
    "REINFORCE_CATEGORY",
    "UPSERT_MERCHANT",
    "WRITE_OFFER",
    "WRITE_REDEMPTION",
    "WRITE_WALLET_EVENT",
]
