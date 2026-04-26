import asyncio

from spark.db.connection import get_connection, init_database
from spark.services.redemption import (
    _acquire_graph_event_idempotency_key,
    confirm_redemption,
    project_offer_outcome_to_graph,
)


def test_graph_projection_idempotency_key_insert_once(tmp_path):
    db_path = str(tmp_path / "idempotency.db")
    init_database(db_path)

    first = _acquire_graph_event_idempotency_key(
        event_type="offer_outcome_declined",
        session_id="sess-1",
        offer_id="offer-1",
        db_path=db_path,
    )
    second = _acquire_graph_event_idempotency_key(
        event_type="offer_outcome_declined",
        session_id="sess-1",
        offer_id="offer-1",
        db_path=db_path,
    )

    assert first is True
    assert second is False

    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM graph_event_log").fetchone()
        assert row is not None
        assert row["c"] == 1
    finally:
        conn.close()


def test_confirm_redemption_handles_malformed_stored_offer(tmp_path):
    db_path = str(tmp_path / "redemption.db")
    init_database(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO offer_audit_log (
                offer_id, created_at, session_id, merchant_id, llm_raw_output,
                final_offer, rails_audit, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "offer-1",
                "2026-04-26T10:00:00",
                "sess-1",
                "merchant-1",
                "{}",
                "{\"offer_id\":\"offer-1\",\"session_id\":\"sess-1\",\"merchant\":{\"name\":\"Cafe Broken\"},\"discount\":{\"value\":15},\"content\":{\"headline\":\"x\",\"subtext\":\"y\",\"cta_text\":\"z\"},\"genui\":{\"color_palette\":\"bad-value\"}}",
                "{}",
                "SENT",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    result = confirm_redemption("offer-1", db_path=db_path)

    assert result["success"] is True
    assert result["merchant_name"] == "Cafe Broken"
    assert result["amount_eur"] == 0.75


def test_offer_outcome_updates_sqlite_status(tmp_path):
    db_path = str(tmp_path / "offer_outcome.db")
    init_database(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO offer_audit_log (
                offer_id, created_at, session_id, merchant_id, llm_raw_output,
                final_offer, rails_audit, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "offer-decline-1",
                "2026-04-26T10:00:00",
                "sess-1",
                "merchant-1",
                "{}",
                "{}",
                "{}",
                "SENT",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    updated = asyncio.run(
        project_offer_outcome_to_graph(
            session_id="sess-1",
            offer_id="offer-decline-1",
            status="DECLINED",
            db_path=db_path,
        )
    )

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT status, declined_at FROM offer_audit_log WHERE offer_id = ?",
            ("offer-decline-1",),
        ).fetchone()
    finally:
        conn.close()

    assert updated is True
    assert row["status"] == "DECLINED"
    assert row["declined_at"] is not None
