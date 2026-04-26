from __future__ import annotations

import asyncio

from spark.db.connection import get_connection, init_database
from spark.models.api import WalletSeedItem
from spark.services.wallet_seed import apply_wallet_seed_preferences


def test_wallet_seed_idempotency_key_insert_once(tmp_path):
    db_path = str(tmp_path / "wallet_seed.db")
    init_database(db_path)

    captured_calls: list[dict] = []

    class FakeRepo:
        async def ensure_session(self, session_id: str):  # noqa: ANN001
            return True

        @staticmethod
        def is_available() -> bool:
            return True

        async def reinforce_category(self, **kwargs):  # noqa: ANN003
            captured_calls.append(kwargs)
            return 0.3

        async def get_preference_scores(self, session_id: str, limit: int = 25):  # noqa: ANN001
            return []

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        seeds = [
            WalletSeedItem(
                category="cafe",
                weight=0.4,
                source_type="wallet_pass",
                source_confidence=0.8,
                artifact_count=2,
            )
        ]
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
    assert first.avg_quality_multiplier > 0.0
    assert first.normalized_source_types == ["wallet_pass"]
    assert first.governance_confidence_caps["wallet_pass"] == 0.95
    assert second.applied == 0
    assert second.skipped == 1
    assert second.duplicates == 1
    assert second.avg_quality_multiplier == 0.0
    assert second.normalized_source_types == ["wallet_pass"]

    assert captured_calls
    assert captured_calls[0]["source_type"] == "wallet_seed:wallet_pass"
    assert captured_calls[0]["source_confidence"] == 0.8
    assert captured_calls[0]["artifact_count"] == 2

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM graph_event_log WHERE event_type = ?",
            ("wallet_seed:wallet_pass:cafe",),
        ).fetchone()
        assert row is not None
        assert row["c"] == 1
    finally:
        conn.close()


def test_wallet_seed_uses_source_specific_decay_and_quality(tmp_path):
    db_path = str(tmp_path / "wallet_seed_decay.db")
    init_database(db_path)
    captured_calls: list[dict] = []

    class FakeRepo:
        async def ensure_session(self, session_id: str):  # noqa: ANN001
            return True

        @staticmethod
        def is_available() -> bool:
            return True

        async def reinforce_category(self, **kwargs):  # noqa: ANN003
            captured_calls.append(kwargs)
            return 0.4

        async def get_preference_scores(self, session_id: str, limit: int = 25):  # noqa: ANN001
            return []

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        result = asyncio.run(
            apply_wallet_seed_preferences(
                session_id="sess-wallet-quality",
                seeds=[
                    WalletSeedItem(
                        category="cafe",
                        weight=0.5,
                        source_type="wallet_pass",
                        source_confidence=0.9,
                        artifact_count=3,
                    ),
                    WalletSeedItem(
                        category="bar",
                        weight=0.5,
                        source_type="receipt_ocr",
                        source_confidence=0.5,
                        artifact_count=1,
                    ),
                ],
                db_path=db_path,
            )
        )
    finally:
        wallet_seed_module.get_repository = original_get_repo  # type: ignore[assignment]

    assert result.applied == 2
    assert result.avg_quality_multiplier > 0.0
    assert result.normalized_source_types == ["receipt_ocr", "wallet_pass"]
    assert result.governance_confidence_caps["manual_import"] == 0.75
    assert len(captured_calls) == 2
    by_category = {c["category"]: c for c in captured_calls}
    assert by_category["cafe"]["decay_rate"] < by_category["bar"]["decay_rate"]
    assert by_category["cafe"]["delta"] > by_category["bar"]["delta"]


def test_wallet_seed_longitudinal_damping_and_source_normalization(tmp_path):
    db_path = str(tmp_path / "wallet_seed_longitudinal.db")
    init_database(db_path)
    captured_calls: list[dict] = []

    conn = get_connection(db_path)
    try:
        for idx in range(6):
            conn.execute(
                """
                INSERT INTO graph_event_log (idempotency_key, event_type, session_id, offer_id, source)
                VALUES (?, ?, ?, NULL, ?)
                """,
                (
                    f"seed-history-{idx}",
                    "wallet_seed:manual_import:historic",
                    "sess-wallet-history",
                    "wallet_seed",
                ),
            )
        conn.commit()
    finally:
        conn.close()

    class FakeRepo:
        async def ensure_session(self, session_id: str):  # noqa: ANN001
            return True

        @staticmethod
        def is_available() -> bool:
            return True

        async def reinforce_category(self, **kwargs):  # noqa: ANN003
            captured_calls.append(kwargs)
            return 0.4

        async def get_preference_scores(self, session_id: str, limit: int = 25):  # noqa: ANN001
            return []

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        asyncio.run(
            apply_wallet_seed_preferences(
                session_id="sess-wallet-history",
                seeds=[
                    WalletSeedItem(
                        category="fresh",
                        weight=0.6,
                        source_type="unknown_source",
                        source_confidence=1.0,
                        artifact_count=20,
                    )
                ],
                db_path=db_path,
            )
        )
    finally:
        wallet_seed_module.get_repository = original_get_repo  # type: ignore[assignment]

    assert captured_calls
    call = captured_calls[0]
    # Unknown source is normalized by governance to manual_import.
    assert call["source_type"] == "wallet_seed:manual_import"
    # Governance applies max artifact cap for normalized source.
    assert call["artifact_count"] == 6
    # Unknown source confidence is clamped by manual_import governance ceiling.
    assert call["source_confidence"] == 0.75
    # Longitudinal damping should keep delta conservative despite high raw weight.
    assert call["delta"] < 0.21


def test_wallet_seed_receipt_ocr_confidence_is_capped_by_governance(tmp_path):
    db_path = str(tmp_path / "wallet_seed_confidence_cap.db")
    init_database(db_path)
    captured_calls: list[dict] = []

    class FakeRepo:
        async def ensure_session(self, session_id: str):  # noqa: ANN001
            return True

        @staticmethod
        def is_available() -> bool:
            return True

        async def reinforce_category(self, **kwargs):  # noqa: ANN003
            captured_calls.append(kwargs)
            return 0.3

        async def get_preference_scores(self, session_id: str, limit: int = 25):  # noqa: ANN001
            return []

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        asyncio.run(
            apply_wallet_seed_preferences(
                session_id="sess-wallet-cap",
                seeds=[
                    WalletSeedItem(
                        category="bar",
                        weight=0.5,
                        source_type="receipt_ocr",
                        source_confidence=0.99,
                        artifact_count=3,
                    )
                ],
                db_path=db_path,
            )
        )
    finally:
        wallet_seed_module.get_repository = original_get_repo  # type: ignore[assignment]

    assert captured_calls
    assert captured_calls[0]["source_type"] == "wallet_seed:receipt_ocr"
    assert captured_calls[0]["source_confidence"] == 0.8


def test_wallet_seed_skips_when_graph_unavailable(tmp_path):
    db_path = str(tmp_path / "wallet_seed_unavailable.db")
    init_database(db_path)

    class FakeRepo:
        @staticmethod
        def is_available() -> bool:
            return False

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        result = asyncio.run(
            apply_wallet_seed_preferences(
                session_id="sess-wallet-unavailable",
                seeds=[
                    WalletSeedItem(
                        category="cafe",
                        weight=0.4,
                        source_type="wallet_pass",
                        source_confidence=0.8,
                        artifact_count=2,
                    )
                ],
                db_path=db_path,
            )
        )
    finally:
        wallet_seed_module.get_repository = original_get_repo  # type: ignore[assignment]

    assert result.applied == 0
    assert result.skipped == 1
    assert result.avg_quality_multiplier == 0.0
    assert result.normalized_source_types == []
    assert result.governance_confidence_caps == {}

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM graph_event_log WHERE event_type LIKE ?",
            ("wallet_seed:%",),
        ).fetchone()
        assert row is not None
        assert row["c"] == 0
    finally:
        conn.close()


def test_wallet_seed_longitudinal_history_reduces_delta_monotonically(tmp_path):
    db_path = str(tmp_path / "wallet_seed_monotonic_history.db")
    init_database(db_path)

    def _seed_history(session_id: str, count: int) -> None:
        conn = get_connection(db_path)
        try:
            for idx in range(count):
                conn.execute(
                    """
                    INSERT INTO graph_event_log (
                        idempotency_key, event_type, session_id, offer_id, source
                    ) VALUES (?, ?, ?, NULL, ?)
                    """,
                    (
                        f"history-{session_id}-{idx}",
                        "wallet_seed:wallet_pass:historic",
                        session_id,
                        "wallet_seed",
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    _seed_history("sess-wallet-history-0", 0)
    _seed_history("sess-wallet-history-3", 3)
    _seed_history("sess-wallet-history-8", 8)

    captured_calls: list[dict] = []

    class FakeRepo:
        async def ensure_session(self, session_id: str):  # noqa: ANN001
            return True

        @staticmethod
        def is_available() -> bool:
            return True

        async def reinforce_category(self, **kwargs):  # noqa: ANN003
            captured_calls.append(kwargs)
            return 0.5

        async def get_preference_scores(self, session_id: str, limit: int = 25):  # noqa: ANN001
            return []

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        for session_id in (
            "sess-wallet-history-0",
            "sess-wallet-history-3",
            "sess-wallet-history-8",
        ):
            asyncio.run(
                apply_wallet_seed_preferences(
                    session_id=session_id,
                    seeds=[
                        WalletSeedItem(
                            category=f"cafe_{session_id}",
                            weight=0.5,
                            source_type="wallet_pass",
                            source_confidence=0.9,
                            artifact_count=3,
                        )
                    ],
                    db_path=db_path,
                )
            )
    finally:
        wallet_seed_module.get_repository = original_get_repo  # type: ignore[assignment]

    assert len(captured_calls) == 3
    deltas = [float(call["delta"]) for call in captured_calls]
    assert deltas[0] > deltas[1] > deltas[2]


def test_wallet_seed_sequential_imports_dampen_delta_within_same_session(tmp_path):
    db_path = str(tmp_path / "wallet_seed_sequential_timeline.db")
    init_database(db_path)
    captured_calls: list[dict] = []

    class FakeRepo:
        async def ensure_session(self, session_id: str):  # noqa: ANN001
            return True

        @staticmethod
        def is_available() -> bool:
            return True

        async def reinforce_category(self, **kwargs):  # noqa: ANN003
            captured_calls.append(kwargs)
            return 0.45

        async def get_preference_scores(self, session_id: str, limit: int = 25):  # noqa: ANN001
            return []

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        session_id = "sess-wallet-sequential"
        for idx in range(4):
            asyncio.run(
                apply_wallet_seed_preferences(
                    session_id=session_id,
                    seeds=[
                        WalletSeedItem(
                            category=f"timeline_{idx}",
                            weight=0.55,
                            source_type="wallet_pass",
                            source_confidence=0.9,
                            artifact_count=3,
                        )
                    ],
                    db_path=db_path,
                )
            )
    finally:
        wallet_seed_module.get_repository = original_get_repo  # type: ignore[assignment]

    assert len(captured_calls) == 4
    deltas = [float(call["delta"]) for call in captured_calls]
    assert deltas[0] > deltas[1] > deltas[2] > deltas[3]


def test_wallet_seed_calibration_matrix_source_and_history_delta_bands(tmp_path):
    db_path = str(tmp_path / "wallet_seed_calibration_matrix.db")
    init_database(db_path)
    captured_calls: list[dict] = []

    def _seed_history(session_id: str, source_type: str, count: int) -> None:
        conn = get_connection(db_path)
        try:
            for idx in range(count):
                conn.execute(
                    """
                    INSERT INTO graph_event_log (
                        idempotency_key, event_type, session_id, offer_id, source
                    ) VALUES (?, ?, ?, NULL, ?)
                    """,
                    (
                        f"calibration-{session_id}-{idx}",
                        f"wallet_seed:{source_type}:historic",
                        session_id,
                        "wallet_seed",
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    class FakeRepo:
        async def ensure_session(self, session_id: str):  # noqa: ANN001
            return True

        @staticmethod
        def is_available() -> bool:
            return True

        async def reinforce_category(self, **kwargs):  # noqa: ANN003
            captured_calls.append(kwargs)
            return 0.3

        async def get_preference_scores(self, session_id: str, limit: int = 25):  # noqa: ANN001
            return []

    import spark.services.wallet_seed as wallet_seed_module

    original_get_repo = wallet_seed_module.get_repository
    wallet_seed_module.get_repository = lambda: FakeRepo()  # type: ignore[assignment]
    try:
        scenarios = [
            ("wallet_pass", 0),
            ("wallet_pass", 6),
            ("receipt_ocr", 0),
            ("receipt_ocr", 6),
            ("manual_import", 0),
            ("manual_import", 6),
        ]
        for source_type, history_count in scenarios:
            session_id = f"sess-calib-{source_type}-{history_count}"
            _seed_history(session_id, source_type, history_count)
            asyncio.run(
                apply_wallet_seed_preferences(
                    session_id=session_id,
                    seeds=[
                        WalletSeedItem(
                            category=f"calib_{source_type}_{history_count}",
                            weight=0.5,
                            source_type=source_type,
                            source_confidence=0.9,
                            artifact_count=3,
                        )
                    ],
                    db_path=db_path,
                )
            )
    finally:
        wallet_seed_module.get_repository = original_get_repo  # type: ignore[assignment]

    by_key = {
        (call["source_type"].replace("wallet_seed:", ""), call["category"].rsplit("_", 1)[-1]): float(
            call["delta"]
        )
        for call in captured_calls
    }
    wp0 = by_key[("wallet_pass", "0")]
    wp6 = by_key[("wallet_pass", "6")]
    ro0 = by_key[("receipt_ocr", "0")]
    ro6 = by_key[("receipt_ocr", "6")]
    mi0 = by_key[("manual_import", "0")]
    mi6 = by_key[("manual_import", "6")]

    # Source multiplier ordering at baseline history.
    assert wp0 > ro0 > mi0
    # Longitudinal damping should reduce each source with higher history.
    assert wp0 > wp6
    assert ro0 > ro6
    assert mi0 > mi6
    # Calibration bands guard against accidental large policy drift.
    assert 0.16 <= wp0 <= 0.17
    assert 0.07 <= wp6 <= 0.08
    assert 0.13 <= ro0 <= 0.14
    assert 0.06 <= ro6 <= 0.07
    assert 0.11 <= mi0 <= 0.12
    assert 0.05 <= mi6 <= 0.06
