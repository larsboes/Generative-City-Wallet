from __future__ import annotations

from datetime import datetime, timezone

from spark.services.contracts import (
    HistoryGenerationData,
    LiveUpdateGenerationData,
    OccupancyMerchantData,
    OccupancyQueryData,
    VendorDashboardData,
)
from spark.services.occupancy_query import (
    get_occupancy_for_merchant,
    list_available_venues,
    query_occupancy,
)
from spark.services.transaction_generation import generate_history, generate_live_update
from spark.services.vendor_metrics import fetch_vendor_dashboard_today


def _first_merchant_id() -> str:
    venues = list_available_venues(None, None, None, None, None, 5)
    assert venues, "expected seeded venues for contract tests"
    return venues[0].merchant_id


def test_vendor_metrics_contract_shape():
    merchant_id = _first_merchant_id()
    result = fetch_vendor_dashboard_today(
        merchant_id=merchant_id,
        timestamp=datetime.now(timezone.utc),
        lookback_days=14,
    )
    assert isinstance(result, VendorDashboardData)
    assert isinstance(result.current_hour, int)
    assert isinstance(result.daily, dict)
    assert isinstance(result.comparison, list)


def test_occupancy_contract_shapes():
    merchant_id = _first_merchant_id()
    single = get_occupancy_for_merchant(
        merchant_id=merchant_id,
        timestamp=datetime.now(timezone.utc),
        arrival_offset_minutes=10,
    )
    assert isinstance(single, OccupancyMerchantData)
    assert single.venue.merchant_id == merchant_id

    multi = query_occupancy(
        merchant_ids=[merchant_id],
        timestamp=datetime.now(timezone.utc),
        arrival_offset_minutes=10,
    )
    assert isinstance(multi, OccupancyQueryData)
    assert len(multi.items) >= 1


def test_transaction_generation_contract_shapes():
    merchant_id = _first_merchant_id()

    history = generate_history(
        merchant_ids=[merchant_id],
        category=None,
        city=None,
        limit=1,
        days=1,
        start=None,
        end=None,
        seed=7,
    )
    assert isinstance(history, HistoryGenerationData)
    assert history.venue_count >= 1

    live = generate_live_update(
        merchant_ids=[merchant_id],
        category=None,
        city=None,
        limit=1,
        timestamp=datetime.now(timezone.utc),
        seed=7,
    )
    assert isinstance(live, LiveUpdateGenerationData)
    assert live.venue_count >= 1
