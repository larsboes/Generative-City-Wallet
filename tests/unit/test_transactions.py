from datetime import date, datetime, timezone

from spark.db.connection import get_connection, upsert_venues
from spark.services.transaction_stats import (
    get_daily_transactions,
    get_fastest_slowest_hours,
    get_hourly_average_by_weekday,
    get_last_7_days_revenue,
)
from spark.services.transactions import (
    expected_txn_rate,
    generate_last_hour_update,
    generate_transactions_for_hour,
)
from spark.services.venues import get_venue


def seed_venue(db_path: str) -> None:
    upsert_venues(
        db_path,
        [
            {
                "merchant_id": "osm_node_1",
                "osm_type": "node",
                "osm_id": "1",
                "name": "Test Cafe",
                "category": "cafe",
                "lat": 48.137,
                "lon": 11.575,
                "city": "München",
            }
        ],
    )


def test_expected_rate_uses_base_rates_and_day_multipliers() -> None:
    dt = datetime(2026, 4, 20, 9, tzinfo=timezone.utc)
    assert expected_txn_rate("cafe", dt) == 45.24


def test_hour_generation_is_deterministic(tmp_path) -> None:
    db_path = str(tmp_path / "occupancy.db")
    seed_venue(db_path)
    conn = get_connection(db_path)
    try:
        venue = get_venue(conn, "osm_node_1")
        assert venue is not None
        hour = datetime(2026, 4, 20, 9, tzinfo=timezone.utc)
        first = generate_transactions_for_hour(venue, hour, "test", seed=42)
        second = generate_transactions_for_hour(venue, hour, "test", seed=42)
    finally:
        conn.close()

    assert first == second
    assert len(first) > 0
    assert all(txn["merchant_id"] == "osm_node_1" for txn in first)


def test_live_update_and_stats_are_log_backed(tmp_path) -> None:
    db_path = str(tmp_path / "occupancy.db")
    seed_venue(db_path)
    timestamp = datetime(2026, 4, 20, 10, tzinfo=timezone.utc)

    conn = get_connection(db_path)
    try:
        venue = get_venue(conn, "osm_node_1")
        assert venue is not None

        inserted, window_start, window_end = generate_last_hour_update(
            conn, [venue], timestamp, seed=7
        )
        daily = get_daily_transactions(conn, "osm_node_1", date(2026, 4, 20))
        hourly_avg = get_hourly_average_by_weekday(
            conn, "osm_node_1", 0, 7, date(2026, 4, 21)
        )
        revenue = get_last_7_days_revenue(conn, "osm_node_1", date(2026, 4, 20))
        rankings = get_fastest_slowest_hours(conn, "osm_node_1", 365)
    finally:
        conn.close()

    assert window_start == datetime(2026, 4, 20, 9, tzinfo=timezone.utc)
    assert window_end == timestamp
    assert inserted > 0
    assert daily["transaction_count"] == inserted
    assert daily["hourly"][9]["transaction_count"] == inserted
    assert len(hourly_avg) == 24
    assert revenue["total_revenue_eur"] > 0
    assert len(rankings["fastest_hours"]) == 5
    assert len(rankings["slowest_hours"]) == 5
