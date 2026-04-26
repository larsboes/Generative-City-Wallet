from __future__ import annotations

from datetime import datetime, timezone

from spark.db.connection import get_connection, init_database
from spark.repositories.payone import insert_payone_transaction
from spark.services.density import compute_density_signal


def test_payone_ingest_event_impacts_density_read_path(tmp_path) -> None:
    db_path = str(tmp_path / "payone_ingest.db")
    init_database(db_path)

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "MERCHANT_INGEST_001",
                "Ingest Test Cafe",
                "cafe",
                48.1,
                9.1,
                "Teststrasse 1",
                "STR-MITTE-047",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    ts = datetime(2026, 4, 26, 10, 0, tzinfo=timezone.utc)
    hour_of_week = ts.weekday() * 24 + ts.hour

    # Baseline historical rows (avg=10).
    for i in range(4):
        insert_payone_transaction(
            merchant_id="MERCHANT_INGEST_001",
            merchant_type="cafe",
            timestamp=ts.isoformat(),
            hour_of_day=ts.hour,
            day_of_week=ts.weekday(),
            hour_of_week=hour_of_week,
            txn_count=10,
            total_volume_eur=100.0 + i,
            db_path=db_path,
        )

    # Simulate a new low-traffic ingested event from fluentbit path.
    insert_payone_transaction(
        merchant_id="MERCHANT_INGEST_001",
        merchant_type="cafe",
        timestamp=ts.isoformat(),
        hour_of_day=ts.hour,
        day_of_week=ts.weekday(),
        hour_of_week=hour_of_week,
        txn_count=2,
        total_volume_eur=8.0,
        db_path=db_path,
    )

    density = compute_density_signal(
        "MERCHANT_INGEST_001",
        current_dt=ts,
        db_path=db_path,
    )

    assert density["current_rate"] == 2.0
    assert density["offer_eligible"] is True
    assert density["signal"] in {"PRIORITY", "FLASH"}
