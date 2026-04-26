from datetime import datetime, timezone

from spark.db.connection import get_connection
from spark.repositories.transactions import insert_venue_transactions
from spark.repositories.venues import upsert_venues
from spark.services.canonicalization import normalize_category
from spark.services.demand import (
    classify_density,
    compute_demand_context,
    infer_occupancy_pct,
)
from spark.services.venues import get_venue


def test_normalize_category_aliases() -> None:
    assert normalize_category("coffee-shop") == "cafe"
    assert normalize_category("club") == "nightclub"
    assert normalize_category("Fast Food") == "fast_food"


def test_classify_density_thresholds() -> None:
    assert classify_density(2.0, 10.0)[2:] == ("FLASH", True)
    assert classify_density(5.0, 10.0)[2:] == ("PRIORITY", True)
    assert classify_density(7.0, 10.0)[2:] == ("QUIET", True)
    assert classify_density(8.0, 10.0)[2:] == ("NORMAL", False)
    assert classify_density(0.0, 0.2)[2:] == ("NORMALLY_CLOSED", False)


def test_infer_occupancy_clamps_to_range() -> None:
    assert infer_occupancy_pct("bar", 0.5) == 0.0
    assert infer_occupancy_pct("bar", 22.0) == 1.0
    assert infer_occupancy_pct("bar", 99.0) == 1.0
    assert infer_occupancy_pct("restaurant", 10.0) is None


def test_compute_demand_context_uses_transaction_logs(tmp_path) -> None:
    db_path = str(tmp_path / "occupancy.db")
    upsert_venues(
        db_path,
        [
            {
                "merchant_id": "osm_node_1",
                "osm_type": "node",
                "osm_id": "1",
                "name": "Test Bar",
                "category": "bar",
                "lat": 48.137,
                "lon": 11.575,
                "city": "München",
            }
        ],
    )

    conn = get_connection(db_path)
    try:
        transactions = []
        for week, day in enumerate([10, 17]):
            for idx in range(20):
                transactions.append(
                    {
                        "transaction_id": f"hist-{week}-{idx}",
                        "merchant_id": "osm_node_1",
                        "category": "bar",
                        "timestamp": f"2026-04-{day}T20:{idx:02d}:00+00:00",
                        "hour_of_day": 20,
                        "day_of_week": 4,
                        "hour_of_week": 116,
                        "amount_eur": 10.0,
                        "source": "test_history",
                    }
                )
        for idx in range(6):
            transactions.append(
                {
                    "transaction_id": f"current-{idx}",
                    "merchant_id": "osm_node_1",
                    "category": "bar",
                    "timestamp": f"2026-04-24T20:{idx:02d}:00+00:00",
                    "hour_of_day": 20,
                    "day_of_week": 4,
                    "hour_of_week": 116,
                    "amount_eur": 10.0,
                    "source": "test_live",
                }
            )
        insert_venue_transactions(conn, transactions)
        conn.commit()
        venue = get_venue(conn, "osm_node_1")
        assert venue is not None

        demand = compute_demand_context(
            conn,
            venue,
            datetime(2026, 4, 24, 21, tzinfo=timezone.utc),
            arrival_offset_minutes=10,
        )
    finally:
        conn.close()

    assert demand.signal == "FLASH"
    assert demand.offer_eligible is True
    assert demand.current_txn_rate == 6
    assert demand.historical_avg == 20
    assert demand.current_occupancy_pct is not None
    assert demand.predicted_occupancy_pct is not None
