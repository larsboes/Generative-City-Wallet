"""
Spark — Neo4j user knowledge graph layer.

The graph captures pseudonymous session interactions: offers received,
outcomes (accepted/declined/expired/redeemed), reinforced category and
attribute preferences, merchant catalogue, and context snapshots.

All public callers should go through `GraphRepository`. Direct Cypher
should not appear outside this package.
"""

from src.backend.graph.client import (
    close_graph,
    get_metrics,
    init_graph,
    is_available,
)
from src.backend.graph.repository import GraphRepository, get_repository

__all__ = [
    "GraphRepository",
    "close_graph",
    "get_metrics",
    "get_repository",
    "init_graph",
    "is_available",
]
