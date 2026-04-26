from __future__ import annotations

import asyncio

from spark.db.connection import get_connection, init_database
from spark.models.api import WalletSeedItem
from spark.services.wallet_seed import apply_wallet_seed_preferences


def test_wallet_seed_idempotency_key_insert_once(tmp_path):
    db_path = str(tmp_path / "wallet_seed.db")
    init_database(db_path)

    class FakeRepo:
        async def ensure_session(self, session_id: str):  # noqa: ANN001
            return True

        @staticmethod
        def is_available() -> bool:
            return True

        async def reinforce_category(self, **kwargs):  # noqa: ANN003
            return 0.3

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        seeds = [WalletSeedItem(category="cafe", weight=0.4)]
        first = asyncio.run(
            apply_wallet_seed_preferences(
                session_id="sess-wallet-1",
                seeds=seeds,
                db_path=db_path,
            )
        )
        second = asyncio.run(
            apply_wallet_seed_preferences(
                session_id="sess-wallet-1",
                seeds=seeds,
                db_path=db_path,
            )
        )
    finally:
        wallet_seed_module.get_repository = original_get_repo  # type: ignore[assignment]

    assert first.applied == 1
    assert second.applied == 0
    assert second.skipped == 1

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM graph_event_log WHERE event_type = ?",
            ("wallet_seed:cafe",),
        ).fetchone()
        assert row is not None
        assert row["c"] == 1
    finally:
        conn.close()
