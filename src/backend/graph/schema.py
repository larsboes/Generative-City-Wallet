"""
Neo4j schema bootstrap — constraints and indexes.

Run once at startup via `safe_execute(ensure_schema, ...)`. Statements
are idempotent (`IF NOT EXISTS`).

Node labels:
- :UserSession            (key: session_id)
- :Merchant               (key: id)
- :MerchantCategory       (key: name)
- :Attribute              (key: name)
- :Offer                  (key: offer_id)
- :Redemption             (key: offer_id — 1:1 with offer)
- :WalletEvent            (key: offer_id — 1:1 with redemption)
- :ContextSnapshot        (no key — attached via :GENERATED_IN)
"""

from __future__ import annotations

from neo4j import AsyncSession

CONSTRAINTS_AND_INDEXES: list[str] = [
    # ── Uniqueness constraints (also create backing indexes automatically) ──
    "CREATE CONSTRAINT user_session_id IF NOT EXISTS "
    "FOR (u:UserSession) REQUIRE u.session_id IS UNIQUE",
    "CREATE CONSTRAINT merchant_id IF NOT EXISTS "
    "FOR (m:Merchant) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT category_name IF NOT EXISTS "
    "FOR (c:MerchantCategory) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT attribute_name IF NOT EXISTS "
    "FOR (a:Attribute) REQUIRE a.name IS UNIQUE",
    "CREATE CONSTRAINT offer_id IF NOT EXISTS "
    "FOR (o:Offer) REQUIRE o.offer_id IS UNIQUE",
    "CREATE CONSTRAINT redemption_offer_id IF NOT EXISTS "
    "FOR (r:Redemption) REQUIRE r.offer_id IS UNIQUE",
    # ── Lookup indexes ─────────────────────────────────────────────────────
    "CREATE INDEX offer_created_at IF NOT EXISTS "
    "FOR (o:Offer) ON (o.created_at_unix)",
    "CREATE INDEX merchant_grid IF NOT EXISTS "
    "FOR (m:Merchant) ON (m.grid_cell)",
    "CREATE INDEX merchant_category IF NOT EXISTS "
    "FOR (m:Merchant) ON (m.category)",
]


async def ensure_schema(s: AsyncSession) -> None:
    for stmt in CONSTRAINTS_AND_INDEXES:
        await s.run(stmt)
