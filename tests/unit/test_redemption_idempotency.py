from spark.db.connection import get_connection, init_database
from spark.services.redemption import (
    _acquire_graph_event_idempotency_key,
    confirm_redemption,
)
from spark.repositories.redemption import count_recent_graph_events_for_category


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
    assert result["base_amount_eur"] == 0.75
    assert result["catalyst_bonus_pct"] == 0.0


def test_confirm_redemption_applies_completed_wave_catalyst_bonus(tmp_path):
    db_path = str(tmp_path / "redemption-wave-bonus.db")
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
                "offer-wave-1",
                "2026-04-26T10:00:00",
                "sess-wave-bonus-1",
                "merchant-1",
                "{}",
                "{\"offer_id\":\"offer-wave-1\",\"session_id\":\"sess-wave-bonus-1\",\"merchant\":{\"name\":\"Cafe Wave\"},\"discount\":{\"value\":20},\"content\":{\"headline\":\"x\",\"subtext\":\"y\",\"cta_text\":\"z\"},\"genui\":{\"color_palette\":\"soft_cream\",\"typography_weight\":\"semibold\",\"background_style\":\"clean\",\"imagery_prompt\":\"cafe\",\"urgency_style\":\"low\",\"card_mood\":\"cozy\"},\"expires_at\":\"2026-04-26T12:00:00\"}",
                "{}",
                "SENT",
            ),
        )
        conn.execute(
            """
            INSERT INTO spark_waves (
                wave_id, offer_id, merchant_id, created_by_session,
                participant_count, milestone_target, expires_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wave-1",
                "offer-wave-1",
                "merchant-1",
                "sess-wave-bonus-1",
                3,
                3,
                "2099-01-01T00:00:00+00:00",
                "COMPLETED",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    result = confirm_redemption("offer-wave-1", db_path=db_path)
    assert result["success"] is True
    assert result["base_amount_eur"] == 1.0
    assert result["catalyst_bonus_pct"] == 0.2
    assert result["amount_eur"] == 1.2


def test_graph_projection_idempotency_allows_distinct_source_events(tmp_path):
    db_path = str(tmp_path / "idempotency-distinct.db")
    init_database(db_path)

    first = _acquire_graph_event_idempotency_key(
        event_type="wallet_seed:wallet_pass:cafe",
        session_id="sess-1",
        offer_id=None,
        category="cafe",
        source_event_id="evt-1",
        event_payload={"weight": 0.3},
        db_path=db_path,
    )
    second_same = _acquire_graph_event_idempotency_key(
        event_type="wallet_seed:wallet_pass:cafe",
        session_id="sess-1",
        offer_id=None,
        category="cafe",
        source_event_id="evt-1",
        event_payload={"weight": 0.3},
        db_path=db_path,
    )
    third_distinct = _acquire_graph_event_idempotency_key(
        event_type="wallet_seed:wallet_pass:cafe",
        session_id="sess-1",
        offer_id=None,
        category="cafe",
        source_event_id="evt-2",
        event_payload={"weight": 0.31},
        db_path=db_path,
    )

    assert first is True
    assert second_same is False
    assert third_distinct is True


def test_recent_category_event_counter_uses_window(tmp_path):
    db_path = str(tmp_path / "idempotency-window.db")
    init_database(db_path)
    for idx in range(3):
        _acquire_graph_event_idempotency_key(
            event_type=f"pref_update:wallet_seed:{idx}",
            session_id="sess-window",
            offer_id=None,
            category="cafe",
            source_event_id=f"evt-{idx}",
            db_path=db_path,
        )

    count = count_recent_graph_events_for_category(
        session_id="sess-window",
        category="cafe",
        window_seconds=300,
        db_path=db_path,
    )
    assert count >= 3
