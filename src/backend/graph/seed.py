"""
Project SQLite merchant catalogue into Neo4j.

Runs once at startup so the graph has a complete merchant + category
view that mirrors the source-of-truth in SQLite. Idempotent — safe to
run on every boot.
"""

from __future__ import annotations

import logging

from src.backend.db.connection import get_connection
from src.backend.graph.repository import get_repository

logger = logging.getLogger("spark.graph.seed")


async def sync_merchants_from_sqlite(db_path: str | None = None) -> int:
    """Project all merchants from SQLite into Neo4j. Returns count synced."""
    repo = get_repository()
    if not repo.is_available():
        return 0

    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, name, type, address, grid_cell FROM merchants"
        ).fetchall()
    finally:
        conn.close()

    synced = 0
    for row in rows:
        ok = await repo.upsert_merchant(
            merchant_id=row["id"],
            name=row["name"],
            category=row["type"],
            grid_cell=row["grid_cell"],
            address=row["address"],
        )
        if ok:
            synced += 1

    logger.info("Synced %d/%d merchants to Neo4j", synced, len(rows))
    return synced
