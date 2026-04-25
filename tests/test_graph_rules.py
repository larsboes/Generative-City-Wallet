"""
Unit tests for GraphValidationService.

We use a hand-rolled FakeRepository so the tests are hermetic — no
Neo4j instance required. The fake mirrors the methods used by the
service and lets us drive every rule branch deterministically.
"""

from __future__ import annotations

import time

import pytest

from src.backend.graph.repository import MerchantOfferStats, RecentOffer
from src.backend.services.graph_rules import (
    GraphValidationService,
    RuleSeverity,
)


class FakeRepository:
    """Mimics GraphRepository for the rule engine tests."""

    def __init__(
        self,
        *,
        available: bool = True,
        session_offers_24h: int = 0,
        merchant_count_24h: int = 0,
        merchant_last_unix: float | None = None,
        recent: list[RecentOffer] | None = None,
    ):
        self._available = available
        self._session_offers_24h = session_offers_24h
        self._merchant_count_24h = merchant_count_24h
        self._merchant_last_unix = merchant_last_unix
        self._recent = recent or []

    def is_available(self) -> bool:
        return self._available

    async def session_offer_count(self, *, session_id: str, since_unix: float) -> int:
        return self._session_offers_24h

    async def merchant_offer_stats(
        self, *, session_id: str, merchant_id: str, since_unix: float
    ) -> MerchantOfferStats:
        return MerchantOfferStats(
            count=self._merchant_count_24h, last_unix=self._merchant_last_unix
        )

    async def recent_offers(self, *, session_id: str, limit: int) -> list[RecentOffer]:
        return self._recent[:limit]


@pytest.fixture
def base_args():
    return dict(
        session_id="sess-test",
        merchant_id="MERCHANT_001",
        merchant_category="cafe",
        now_unix=time.time(),
    )


async def test_graph_unavailable_passes_with_info_note(base_args):
    repo = FakeRepository(available=False)
    svc = GraphValidationService(repo=repo)

    result = await svc.validate(**base_args)

    assert result.accepted is True
    assert result.metadata["graph_available"] is False
    assert any(v.rule_id == "graph_unavailable" for v in result.violations)
    assert all(v.severity == RuleSeverity.INFO for v in result.violations)


async def test_clean_session_is_accepted(base_args):
    repo = FakeRepository(available=True)
    svc = GraphValidationService(repo=repo)

    result = await svc.validate(**base_args)

    assert result.accepted is True
    assert result.violations == []


async def test_session_offer_budget_blocks(base_args):
    repo = FakeRepository(available=True, session_offers_24h=10)
    svc = GraphValidationService(repo=repo, rules_config={"session_offer_budget_per_day": 8})

    result = await svc.validate(**base_args)

    assert result.accepted is False
    assert result.recheck_in_minutes == 60
    assert result.hard_violations[0].rule_id == "session_offer_budget"


async def test_merchant_fatigue_blocks(base_args):
    repo = FakeRepository(available=True, merchant_count_24h=5)
    svc = GraphValidationService(
        repo=repo, rules_config={"merchant_fatigue_max_per_day": 3}
    )

    result = await svc.validate(**base_args)

    assert result.accepted is False
    assert result.hard_violations[0].rule_id == "merchant_fatigue_cap"
    assert result.hard_violations[0].metadata["count"] == 5


async def test_same_merchant_cooldown_blocks(base_args):
    now = base_args["now_unix"]
    repo = FakeRepository(
        available=True,
        merchant_count_24h=1,
        merchant_last_unix=now - 5 * 60,  # 5 min ago
    )
    svc = GraphValidationService(
        repo=repo, rules_config={"same_merchant_cooldown_min": 30}
    )

    result = await svc.validate(**base_args)

    assert result.accepted is False
    assert result.hard_violations[0].rule_id == "same_merchant_cooldown"
    assert result.recheck_in_minutes is not None
    assert 1 <= result.recheck_in_minutes <= 30


async def test_category_diversity_is_soft(base_args):
    now = base_args["now_unix"]
    cafe_history = [
        RecentOffer(
            offer_id=f"off-{i}",
            merchant_id="MERCHANT_001",
            category="cafe",
            status="EXPIRED",
            created_at_unix=now - (i + 1) * 600,
        )
        for i in range(5)
    ]
    repo = FakeRepository(available=True, recent=cafe_history)
    svc = GraphValidationService(
        repo=repo,
        rules_config={
            "category_diversity_window": 5,
            "merchant_fatigue_max_per_day": 100,  # don't trip
            "same_merchant_cooldown_min": 0,
            "session_offer_budget_per_day": 100,
        },
    )

    result = await svc.validate(**base_args)

    assert result.accepted is True
    assert result.soft_adjustments == ["diversify_framing"]
    assert any(v.rule_id == "category_diversity" for v in result.soft_violations)


async def test_audit_dict_round_trip(base_args):
    repo = FakeRepository(available=True, session_offers_24h=99)
    svc = GraphValidationService(
        repo=repo, rules_config={"session_offer_budget_per_day": 8}
    )

    result = await svc.validate(**base_args)
    audit = result.to_audit_dict()

    assert audit["accepted"] is False
    assert isinstance(audit["violations"], list)
    assert audit["violations"][0]["rule_id"] == "session_offer_budget"
    assert audit["violations"][0]["severity"] == "hard"
