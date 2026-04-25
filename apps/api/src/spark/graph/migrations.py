"""
Graph migrations and schema version tracking.

Each migration is idempotent and tracked in Neo4j as (:GraphMigration {id}).
"""

from __future__ import annotations

import time

from neo4j import AsyncSession

MIGRATIONS: list[tuple[str, str, str]] = [
    (
        "001_prefers_default_decay_rate",
        "Set default decay_rate on PREFERS edges",
        """
        MATCH ()-[p:PREFERS]->()
        WHERE p.decay_rate IS NULL
        SET p.decay_rate = 0.01
        RETURN count(p) AS updated
        """,
    ),
    (
        "002_context_snapshot_offer_id",
        "Backfill ContextSnapshot.offer_id from connected Offer",
        """
        MATCH (o:Offer)-[:GENERATED_IN]->(ctx:ContextSnapshot)
        WHERE ctx.offer_id IS NULL
        SET ctx.offer_id = o.offer_id
        RETURN count(ctx) AS updated
        """,
    ),
]


async def apply_migrations(s: AsyncSession) -> dict[str, int]:
    applied = 0
    skipped = 0
    now = time.time()

    for migration_id, description, cypher in MIGRATIONS:
        check = await s.run(
            "MATCH (m:GraphMigration {id: $id}) RETURN m.id AS id",
            id=migration_id,
        )
        row = await check.single()
        if row:
            skipped += 1
            continue

        await s.run(cypher)
        await s.run(
            """
            CREATE (m:GraphMigration {
              id: $id,
              description: $description,
              applied_at_unix: $now
            })
            """,
            id=migration_id,
            description=description,
            now=now,
        )
        await s.run(
            """
            MERGE (meta:GraphMeta {key: 'schema_version'})
            SET meta.value = $id,
                meta.updated_at_unix = $now
            """,
            id=migration_id,
            now=now,
        )
        applied += 1

    return {"applied": applied, "skipped": skipped, "total": len(MIGRATIONS)}
