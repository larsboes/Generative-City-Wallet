from __future__ import annotations

from neo4j import AsyncSession

from spark.graph.queries import merchants as Q
from spark.graph.client import safe_execute


class MerchantGraphRepository:
    async def upsert_merchant(
        self,
        merchant_id: str,
        name: str,
        category: str,
        grid_cell: str,
        address: str | None = None,
    ) -> bool:
        async def _run(s: AsyncSession) -> bool:
            await s.run(
                Q.UPSERT_MERCHANT,
                merchant_id=merchant_id,
                name=name,
                category=category,
                grid_cell=grid_cell,
                address=address,
            )
            return True

        return await safe_execute(_run, fallback=False, op_name="upsert_merchant")

