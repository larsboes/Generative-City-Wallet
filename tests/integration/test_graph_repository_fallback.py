"""
Tests for GraphRepository fail-soft behavior.

When Neo4j is not initialized, every method must return a sensible
fallback value without raising. This guarantees the offer pipeline
keeps producing offers even if the graph is down.
"""

from __future__ import annotations

import pytest

from spark.graph import client as graph_client
from spark.graph.repository import (
    GraphRepository,
    MerchantOfferStats,
)


@pytest.fixture(autouse=True)
def _force_unavailable(monkeypatch):
    """Pretend Neo4j is unavailable for every test in this module."""
    monkeypatch.setattr(graph_client, "_driver", None)
    monkeypatch.setattr(graph_client, "_unavailable", True)
    yield


async def test_is_available_false():
    repo = GraphRepository()
    assert repo.is_available() is False


async def test_ensure_session_returns_false():
    repo = GraphRepository()
    assert await repo.ensure_session("sess-1") is False


async def test_get_preference_scores_returns_empty_list():
    repo = GraphRepository()
    assert await repo.get_preference_scores("sess-1") == []


async def test_recent_offers_returns_empty_list():
    repo = GraphRepository()
    assert await repo.recent_offers(session_id="sess-1") == []


async def test_session_offer_count_returns_zero():
    repo = GraphRepository()
    assert await repo.session_offer_count(session_id="sess-1", since_unix=0) == 0


async def test_merchant_offer_stats_returns_empty():
    repo = GraphRepository()
    stats = await repo.merchant_offer_stats(
        session_id="sess-1", merchant_id="m-1", since_unix=0
    )
    assert stats == MerchantOfferStats(count=0, last_unix=None)


async def test_write_methods_return_false():
    repo = GraphRepository()
    assert await repo.write_offer(
        offer_id="off-1",
        session_id="sess-1",
        merchant_id="m-1",
        merchant_name="Test",
        merchant_category="cafe",
        framing_band=None,
        density_signal="QUIET",
        drop_pct=0.5,
        distance_m=80,
        coupon_type=None,
        discount_pct=0,
        timestamp="2026-04-25T12:00:00",
        grid_cell="STR-MITTE-047",
        movement_mode="browsing",
        time_bucket="tuesday_lunch",
        weather_need="warmth_seeking",
        vibe_signal="cozy",
        temp_c=10.0,
        social_preference="quiet",
        occupancy_pct=None,
        predicted_occupancy_pct=None,
    ) is False
    assert await repo.write_redemption(
        session_id="sess-1",
        offer_id="off-1",
        discount_value=15.0,
        discount_type="percentage",
    ) is False
    assert await repo.write_wallet_event(offer_id="off-1", amount_eur=0.68) is False
    assert await repo.reinforce_category(
        session_id="sess-1", category="cafe", delta=0.1
    ) is None


async def test_init_graph_unreachable_does_not_raise(monkeypatch):
    """A bad URI should be swallowed and metrics should still report unavailable."""
    monkeypatch.setattr(graph_client, "_driver", None)
    monkeypatch.setattr(graph_client, "_unavailable", False)
    monkeypatch.setattr(
        "spark.graph.client.NEO4J_URI", "bolt://nonexistent.invalid:7687"
    )
    monkeypatch.setattr("spark.graph.client.NEO4J_STARTUP_TIMEOUT_S", 0.5)
    monkeypatch.setattr("spark.graph.client.NEO4J_ENABLED", True)

    connected = await graph_client.init_graph(run_schema=False)
    assert connected is False
    assert graph_client.is_available() is False
