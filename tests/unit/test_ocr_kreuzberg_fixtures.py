from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from spark.db.connection import get_connection, init_database
from spark.services.location_cells import latlon_to_h3
from spark.services.offer_decision import decide_offer

TEST_CELL = latlon_to_h3(48.137154, 11.576124)


def _fixture(name: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    path = root / "tests" / "fixtures" / "ocr" / name
    return json.loads(path.read_text(encoding="utf-8"))


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


def test_kreuzberg_fixture_shape() -> None:
    short = _fixture("kreuzberg_delay_short.json")
    workable = _fixture("kreuzberg_delay_workable.json")

    assert short["district"] == "Kreuzberg"
    assert workable["district"] == "Kreuzberg"
    assert short["transit_delay_minutes"] < workable["transit_delay_minutes"]
    assert short["confidence"] >= 0.8


def test_kreuzberg_short_delay_blocks_offer(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "ocr_kreuzberg_short.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)
    payload = _fixture("kreuzberg_delay_short.json")

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
        session_id="sess-kreuzberg-short",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="quiet",
        weather_need="neutral",
        preference_scores={"cafe": 0.8},
        transit_delay_minutes=payload["transit_delay_minutes"],
        must_return_by=payload["must_return_by"],
        db_path=db_path,
        now=datetime(2026, 4, 26, 10, 0, 0),
    )

    assert result.recommendation == "DO_NOT_RECOMMEND"
    assert result.trace[0].code == "all_candidates_filtered"


def test_kreuzberg_workable_delay_allows_offer(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "ocr_kreuzberg_workable.db")
    init_database(db_path)
    _seed_minimal_merchants(db_path)
    payload = _fixture("kreuzberg_delay_workable.json")

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
        session_id="sess-kreuzberg-workable",
        grid_cell=TEST_CELL,
        movement_mode="browsing",
        social_preference="quiet",
        weather_need="neutral",
        preference_scores={"cafe": 0.8},
        transit_delay_minutes=payload["transit_delay_minutes"],
        must_return_by=payload["must_return_by"],
        db_path=db_path,
        now=datetime(2026, 4, 26, 10, 0, 0),
    )

    assert result.recommendation == "RECOMMEND"
