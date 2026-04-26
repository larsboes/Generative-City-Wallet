from __future__ import annotations


from spark.db.connection import get_connection, init_database
from spark.services.location_cells import latlon_to_h3
from spark.services.offer_decision import decide_offer

# TEST_CELL is roughly at Marienplatz, Munich
TEST_LAT = 48.137154
TEST_LON = 11.576124
TEST_CELL = latlon_to_h3(TEST_LAT, TEST_LON)


def _seed_merchants_with_distances(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        # MERCHANT_NEAR: 100m away
        # MERCHANT_FAR: 800m away
        conn.execute(
            """
            INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell)
            VALUES
                ('MERCHANT_NEAR', 'Near Cafe', 'cafe', 48.138, 11.576, 'Near', ?),
                ('MERCHANT_FAR', 'Far Bakery', 'bakery', 48.145, 11.576, 'Far', ?)
            """,
            (TEST_CELL, TEST_CELL),
        )
        conn.commit()
    finally:
        conn.close()


def test_dynamic_transit_gating_blocks_far_merchant(tmp_path, monkeypatch):
    db_path = str(tmp_path / "dynamic_transit_block.db")
    init_database(db_path)
    _seed_merchants_with_distances(db_path)

    # Mock dependencies to focus on gating
    monkeypatch.setattr(
        "spark.services.offer_decision.compute_density_signal",
        lambda *args, **kwargs: {"density_score": 0.2, "current_rate": 2.0},
    )

    class FakeConflict:
        recommendation = "RECOMMEND"
        framing_band = "quiet_intentional"
        reason = "ok"

    monkeypatch.setattr(
        "spark.services.offer_decision.resolve_conflict",
        lambda **kwargs: FakeConflict(),
    )

    # Scenario: 10 minute delay.
    # Walking speed 80m/min.
    # MERCHANT_FAR is ~870m away (lat 48.137 -> 48.145).
    # (870 / 80) * 2 + 5 buffer = ~26 minutes required.
    # 26 > 10 -> Should be blocked.

    # MERCHANT_NEAR is ~100m away.
    # (100 / 80) * 2 + 5 buffer = 2.5 + 5 = 7.5 minutes required.
    # 7.5 < 10 -> Should be ALLOWED.

    result = decide_offer(
        session_id="sess-transit-dynamic",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="neutral",
        weather_need="neutral",
        preference_scores={"cafe": 0.9, "bakery": 0.9},
        transit_delay_minutes=10,
        db_path=db_path,
    )

    assert result.recommendation == "RECOMMEND"
    assert result.selected_merchant_id == "MERCHANT_NEAR"
    # Verify MERCHANT_FAR is not in candidate scores (it was filtered out by the return None)
    merchant_ids = [c["merchant_id"] for c in result.candidate_scores]
    assert "MERCHANT_NEAR" in merchant_ids
    assert "MERCHANT_FAR" not in merchant_ids


def test_dynamic_transit_gating_blocks_all_when_delay_too_short(tmp_path, monkeypatch):
    db_path = str(tmp_path / "dynamic_transit_block_all.db")
    init_database(db_path)
    _seed_merchants_with_distances(db_path)

    monkeypatch.setattr(
        "spark.services.offer_decision.compute_density_signal",
        lambda *args, **kwargs: {"density_score": 0.2, "current_rate": 2.0},
    )

    class FakeConflict:
        recommendation = "RECOMMEND"
        reason = "ok"
        framing_band = "none"

    monkeypatch.setattr(
        "spark.services.offer_decision.resolve_conflict",
        lambda **kwargs: FakeConflict(),
    )

    # Scenario: 4 minute delay.
    # Even MERCHANT_NEAR (7.5 mins required) shouldn't fit.
    result = decide_offer(
        session_id="sess-transit-too-short",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="neutral",
        weather_need="neutral",
        preference_scores={"cafe": 0.9},
        transit_delay_minutes=4,
        db_path=db_path,
    )

    assert result.recommendation == "DO_NOT_RECOMMEND"
    assert result.trace[0].code == "all_candidates_filtered"
