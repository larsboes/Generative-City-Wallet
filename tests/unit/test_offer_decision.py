from __future__ import annotations

from datetime import datetime

from spark.db.connection import get_connection, init_database
from spark.services.location_cells import latlon_to_h3
from spark.services.offer_decision import decide_offer

TEST_CELL = latlon_to_h3(48.137154, 11.576124)


def _seed_minimal_merchants(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell)
            VALUES
                ('MERCHANT_001', 'Cafe One', 'cafe', 48.1372, 11.5762, 'A', ?),
                ('MERCHANT_002', 'Bar Two', 'bar', 48.1372, 11.5762, 'B', ?)
            """,
            (TEST_CELL, TEST_CELL),
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
        grid_cell=TEST_CELL,
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
        grid_cell=TEST_CELL,
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
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="quiet",
        weather_need="warmth_seeking",
        preference_scores={"cafe": 1.0},
        db_path=db_path,
    )

    assert result.recommendation == "DO_NOT_RECOMMEND"
    assert result.trace[0].code == "single_offer_guard"


def test_post_workout_prefers_recovery_categories(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_post_workout_recovery.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)

    monkeypatch.setattr(
        "spark.services.offer_decision.compute_density_signal",
        lambda merchant_id, **kwargs: {"density_score": 0.4, "current_rate": 5.0},  # noqa: ARG005
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
        session_id="sess-post-workout",
        grid_cell=TEST_CELL,
        movement_mode="post_workout",
        social_preference="neutral",
        weather_need="neutral",
        preference_scores={"cafe": 0.5, "bar": 0.5},
        db_path=db_path,
        now=datetime(2026, 4, 26, 10, 0, 0),
    )

    assert result.recommendation == "RECOMMEND"
    assert result.selected_merchant_id == "MERCHANT_001"  # cafe beats bar
    assert any(
        step.code == "movement_category_adjustment"
        and step.metadata.get("movement_mode") == "post_workout"
        for step in result.trace
    )


def test_post_workout_shortens_single_offer_guard_recheck(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_post_workout_cooldown.db")
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
            ("off-post-1", datetime.now().isoformat(), "sess-post-guard", "SENT"),
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
        session_id="sess-post-guard",
        grid_cell=TEST_CELL,
        movement_mode="post_workout",
        social_preference="quiet",
        weather_need="warmth_seeking",
        preference_scores={"cafe": 1.0},
        db_path=db_path,
    )

    assert result.recommendation == "DO_NOT_RECOMMEND"
    assert result.trace[0].code == "single_offer_guard"
    assert result.recheck_in_minutes == 12


def test_transit_delay_short_window_blocks_offer(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_transit_block.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)

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
        session_id="sess-transit-block",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="quiet",
        weather_need="neutral",
        preference_scores={"cafe": 0.8},
        transit_delay_minutes=8,
        must_return_by="2026-04-26T10:15:00Z",
        db_path=db_path,
    )

    assert result.recommendation == "DO_NOT_RECOMMEND"
    assert result.trace[0].code == "all_candidates_filtered"
    assert result.recheck_in_minutes == 8


def test_transit_delay_large_window_allows_regular_decision(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_transit_allow.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)

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

    # Use a larger delay (30 mins) to ensure it fits the dynamic walk time
    result = decide_offer(
        session_id="sess-transit-allow",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="quiet",
        weather_need="neutral",
        preference_scores={"cafe": 0.8},
        transit_delay_minutes=30,
        must_return_by="2026-04-26T10:45:00Z",
        db_path=db_path,
    )

    assert result.recommendation == "RECOMMEND"
    assert all(step.code != "transit_window_block" for step in result.trace)


def test_social_mid_occupancy_uses_active_coupon(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_social_coupon.db")
    init_database(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell)
            VALUES ('MERCHANT_005', 'Club Five', 'club', 48.77, 9.18, 'C', ?)
            """,
            (TEST_CELL,),
        )
        conn.execute(
            """
            INSERT INTO merchant_coupons (merchant_id, coupon_type, config, active, created_at)
            VALUES ('MERCHANT_005', 'TIME_BOUND', '{"discount_pct": 20}', 1, '2026-04-26T10:00:00')
            """
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(
        "spark.services.offer_decision.compute_density_signal",
        lambda merchant_id, **kwargs: {"density_score": 0.4, "current_rate": 15.0},  # noqa: ARG005
    )

    result = decide_offer(
        session_id="sess-social-coupon",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="social",
        weather_need="neutral",
        preference_scores={"club": 0.7},
        db_path=db_path,
        now=datetime(2026, 4, 24, 20, 0, 0),
    )

    assert result.recommendation == "RECOMMEND_WITH_FRAMING"
    assert result.selected_merchant_id == "MERCHANT_005"
    assert result.trace[-1].metadata["coupon_type"] == "TIME_BOUND"


def test_strava_activity_signal_adds_alignment_trace(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_strava_trace.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)

    monkeypatch.setattr(
        "spark.services.offer_decision.compute_density_signal",
        lambda merchant_id, **kwargs: {"density_score": 0.35, "current_rate": 4.0},  # noqa: ARG005
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
        session_id="sess-strava",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="neutral",
        weather_need="neutral",
        preference_scores={"cafe": 0.6, "bar": 0.2},
        activity_signal="post_workout",
        activity_source="strava",
        activity_confidence=0.86,
        db_path=db_path,
        now=datetime(2026, 4, 26, 10, 0, 0),
    )

    activity_step = next(
        step for step in result.trace if step.code == "activity_alignment"
    )
    assert activity_step.metadata["activity_source"] == "strava"
    assert activity_step.metadata["source_present"] is True
    assert activity_step.metadata["confidence_band"] == "high"


def test_no_activity_signal_emits_no_activity_alignment_trace(tmp_path, monkeypatch):
    db_path = str(tmp_path / "decision_no_activity_trace.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)

    monkeypatch.setattr(
        "spark.services.offer_decision.compute_density_signal",
        lambda merchant_id, **kwargs: {"density_score": 0.35, "current_rate": 4.0},  # noqa: ARG005
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
        session_id="sess-no-activity",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="neutral",
        weather_need="neutral",
        preference_scores={"cafe": 0.6, "bar": 0.2},
        activity_signal="none",
        activity_source="none",
        activity_confidence=0.0,
        db_path=db_path,
        now=datetime(2026, 4, 26, 10, 0, 0),
    )

    assert all(step.code != "activity_alignment" for step in result.trace)
