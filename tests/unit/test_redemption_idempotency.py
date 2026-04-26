from spark.db.connection import get_connection, init_database
from spark.services.redemption import _acquire_graph_event_idempotency_key


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
