from __future__ import annotations

from datetime import datetime

from spark.db.connection import get_connection, init_database
from spark.services.offer_decision import decide_offer


def _seed_minimal_merchants(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell)
            VALUES
                ('MERCHANT_001', 'Cafe One', 'cafe', 48.77, 9.18, 'A', 'STR-MITTE-047'),
                ('MERCHANT_002', 'Bar Two', 'bar', 48.77, 9.18, 'B', 'STR-MITTE-047')
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_decision_blocks_exercising(tmp_path):
    db_path = str(tmp_path / "decision_exercising.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)

    result = decide_offer(
        session_id="sess-1",
        grid_cell="STR-MITTE-047",
        movement_mode="exercising",
        social_preference="neutral",
        weather_need="neutral",
        preference_scores={"cafe": 0.8},
        db_path=db_path,
        now=datetime(2026, 4, 26, 10, 0, 0),
    )

    assert result.recommendation == "DO_NOT_RECOMMEND"
    assert result.selected_merchant_id is None
    assert result.trace[0].code == "movement_hard_block"


def test_decision_selects_highest_scoring_candidate(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_best.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)

    def fake_density(merchant_id: str, **kwargs):  # noqa: ANN003
        if merchant_id == "MERCHANT_001":
            return {"density_score": 0.2, "current_rate": 2.0}
        return {"density_score": 0.6, "current_rate": 8.0}

    class FakeConflict:
        recommendation = "RECOMMEND"
        framing_band = "quiet_intentional"
        reason = "ok"

    monkeypatch.setattr(
        "spark.services.offer_decision.compute_density_signal", fake_density
    )
    monkeypatch.setattr(
        "spark.services.offer_decision.resolve_conflict",
        lambda **kwargs: FakeConflict(),  # noqa: ARG005
    )

    result = decide_offer(
        session_id="sess-1",
        grid_cell="STR-MITTE-047",
        movement_mode="browsing",
        social_preference="neutral",
        weather_need="warmth_seeking",
        preference_scores={"cafe": 0.9, "bar": 0.2},
        db_path=db_path,
        now=datetime(2026, 4, 26, 10, 0, 0),
    )

    assert result.recommendation == "RECOMMEND"
    assert result.selected_merchant_id == "MERCHANT_001"
    assert result.selected_merchant_score >= 30
    assert result.candidate_scores[0]["merchant_id"] == "MERCHANT_001"


def test_decision_enforces_single_offer_guard(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_single_offer.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO offer_audit_log (
                offer_id, created_at, session_id, status
            ) VALUES (?, ?, ?, ?)
            """,
            ("off-1", datetime.now().isoformat(), "sess-blocked", "SENT"),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(
        "spark.services.offer_decision.compute_density_signal",
        lambda merchant_id, **kwargs: {"density_score": 0.2, "current_rate": 2.0},  # noqa: ARG005
    )

    class FakeConflict:
        recommendation = "RECOMMEND"
        framing_band = "quiet_intentional"
        reason = "ok"

    monkeypatch.setattr(
        "spark.services.offer_decision.resolve_conflict",
        lambda **kwargs: FakeConflict(),  # noqa: ARG005
    )

    result = decide_offer(
        session_id="sess-blocked",
        grid_cell="STR-MITTE-047",
        movement_mode="browsing",
        social_preference="quiet",
        weather_need="warmth_seeking",
        preference_scores={"cafe": 1.0},
        db_path=db_path,
    )

    assert result.recommendation == "DO_NOT_RECOMMEND"
    assert result.trace[0].code == "single_offer_guard"
