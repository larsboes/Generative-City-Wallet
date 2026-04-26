"""
Manual intent sweep for inspecting the current offer API behavior.

Run with:
  uv run pytest -s tests/integration/test_intent_api_sweep.py
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from spark.config import DB_PATH
from spark.db.connection import get_connection
from spark.main import app
from spark.models.common import MovementMode, PriceTier, SocialPreference, WeatherNeed
from spark.services.location_cells import is_valid_h3, latlon_to_h3


SWEEP_HOUR_OF_WEEK = 117  # Friday 21:00, present in the synthetic 28-day seed.


def _ensure_seeded_database() -> None:
    """Ensure we are using OSM-derived demo data, not legacy MERCHANT_* seed data."""
    if DB_PATH != ":memory:" and not Path(DB_PATH).exists():
        raise AssertionError(
            f"Database file missing at {DB_PATH}. Run scripts/ops/load_munich_demo.py first."
        )

    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
              COUNT(*) AS merchant_count,
              SUM(CASE WHEN id LIKE 'MERCHANT_%' THEN 1 ELSE 0 END) AS legacy_count,
              SUM(CASE WHEN substr(grid_cell, 1, 3) IN ('STR', 'MUC') THEN 1 ELSE 0 END) AS legacy_cells
            FROM merchants
            """
        ).fetchone()
        merchant_count = int(row["merchant_count"]) if row else 0
        legacy_count = int(row["legacy_count"]) if row and row["legacy_count"] else 0
        legacy_cells = int(row["legacy_cells"]) if row and row["legacy_cells"] else 0
        bad_cells = conn.execute(
            "SELECT id, grid_cell FROM merchants ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    if merchant_count == 0:
        raise AssertionError(
            "No merchants found. Load OSM demo data first via scripts/ops/load_munich_demo.py."
        )
    if legacy_count > 0:
        raise AssertionError(
            "Legacy MERCHANT_* rows detected. Reset with scripts/ops/load_munich_demo.py."
        )
    if legacy_cells > 0:
        raise AssertionError("Legacy non-H3 grid_cell prefixes detected in merchants.")
    invalid_h3_merchants = [row["id"] for row in bad_cells if not is_valid_h3(row["grid_cell"])]
    if invalid_h3_merchants:
        raise AssertionError(
            f"Non-H3 merchant grid_cell values found: {invalid_h3_merchants[:5]}"
        )


def _osm_merchants_for_sweep(limit: int = 7) -> list[dict[str, str]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, grid_cell
            FROM merchants
            WHERE id NOT LIKE 'MERCHANT_%'
            ORDER BY id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    merchants = [{"id": row["id"], "grid_cell": row["grid_cell"]} for row in rows]
    if not merchants:
        raise AssertionError("Expected OSM merchant IDs in merchants table, found none.")
    return merchants


@pytest.fixture(scope="module")
def client():
    patch = pytest.MonkeyPatch()
    patch.setattr("spark.services.offer_pipeline.AGENT_ENABLED", False)
    patch.setattr("spark.services.offer_generator.GOOGLE_AI_API_KEY", "")
    _ensure_seeded_database()
    try:
        with TestClient(app) as c:
            merchants_resp = c.get("/api/payone/merchants")
            assert merchants_resp.status_code == 200
            assert len(merchants_resp.json()) >= 5
            yield c
    finally:
        patch.undo()


def _seeded_sweep_current_dt() -> str:
    """Return a real timestamp from the seeded synthetic Payone history."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT MAX(timestamp) AS ts
            FROM payone_transactions
            WHERE hour_of_week = ?
            """,
            (SWEEP_HOUR_OF_WEEK,),
        ).fetchone()
    finally:
        conn.close()

    if not row or not row["ts"]:
        raise AssertionError(
            f"No seeded payone_transactions found for hour_of_week={SWEEP_HOUR_OF_WEEK}"
        )
    return datetime.fromisoformat(row["ts"]).isoformat()


def _intent(
    *,
    name: str,
    grid_cell: str = latlon_to_h3(48.137154, 11.576124),
    movement_mode: str = MovementMode.BROWSING.value,
    time_bucket: str = "tuesday_lunch",
    weather_need: str = WeatherNeed.NEUTRAL.value,
    social_preference: str = SocialPreference.NEUTRAL.value,
    price_tier: str = PriceTier.MID.value,
    recent_categories: list[str] | None = None,
    dwell_signal: bool = False,
    battery_low: bool = False,
) -> dict[str, Any]:
    return {
        "grid_cell": grid_cell,
        "movement_mode": movement_mode,
        "time_bucket": time_bucket,
        "weather_need": weather_need,
        "social_preference": social_preference,
        "price_tier": price_tier,
        "recent_categories": recent_categories or [],
        "dwell_signal": dwell_signal,
        "battery_low": battery_low,
        "session_id": f"intent-sweep-{name}",
    }


FOCUSED_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "cold_quiet_cafe",
        "merchant_id": None,
        "intent": _intent(
            name="cold-quiet-cafe",
            weather_need=WeatherNeed.WARMTH_SEEKING.value,
            social_preference=SocialPreference.QUIET.value,
            recent_categories=["cafe"],
        ),
        "demo_overrides": {"temp_celsius": 5, "weather_condition": "rain"},
    },
    {
        "name": "morning_bakery_commute",
        "merchant_id": None,
        "intent": _intent(
            name="morning-bakery-commute",
            movement_mode=MovementMode.COMMUTING.value,
            time_bucket="weekday_morning",
            price_tier=PriceTier.LOW.value,
            recent_categories=["bakery", "coffee"],
            battery_low=True,
        ),
    },
    {
        "name": "social_bar_evening",
        "merchant_id": None,
        "intent": _intent(
            name="social-bar-evening",
            movement_mode=MovementMode.STATIONARY.value,
            time_bucket="friday_evening",
            social_preference=SocialPreference.SOCIAL.value,
            price_tier=PriceTier.HIGH.value,
            recent_categories=["bar", "restaurant"],
            dwell_signal=True,
        ),
    },
    {
        "name": "restaurant_shelter_lunch",
        "merchant_id": None,
        "intent": _intent(
            name="restaurant-shelter-lunch",
            time_bucket="tuesday_lunch",
            weather_need=WeatherNeed.SHELTER_SEEKING.value,
            recent_categories=["restaurant"],
        ),
        "demo_overrides": {"temp_celsius": 9, "weather_condition": "storm"},
    },
    {
        "name": "late_club_high_energy",
        "merchant_id": None,
        "intent": _intent(
            name="late-club-high-energy",
            movement_mode=MovementMode.TRANSIT_WAITING.value,
            time_bucket="saturday_late",
            social_preference=SocialPreference.SOCIAL.value,
            price_tier=PriceTier.HIGH.value,
            recent_categories=["club", "bar"],
        ),
    },
    {
        "name": "post_workout_refreshment",
        "merchant_id": None,
        "intent": _intent(
            name="post-workout-refreshment",
            movement_mode=MovementMode.POST_WORKOUT.value,
            time_bucket="saturday_afternoon",
            weather_need=WeatherNeed.REFRESHMENT_SEEKING.value,
            price_tier=PriceTier.LOW.value,
            recent_categories=["bakery", "cafe"],
            dwell_signal=True,
        ),
        "demo_overrides": {"temp_celsius": 31, "weather_condition": "sunny"},
    },
    {
        "name": "cycling_low_battery",
        "merchant_id": None,
        "intent": _intent(
            name="cycling-low-battery",
            movement_mode=MovementMode.CYCLING.value,
            time_bucket="weekday_evening",
            weather_need=WeatherNeed.REFRESHMENT_SEEKING.value,
            social_preference=SocialPreference.QUIET.value,
            battery_low=True,
        ),
    },
    {
        "name": "poor_fit_quiet_club",
        "merchant_id": None,
        "intent": _intent(
            name="poor-fit-quiet-club",
            movement_mode=MovementMode.BROWSING.value,
            time_bucket="tuesday_lunch",
            weather_need=WeatherNeed.WARMTH_SEEKING.value,
            social_preference=SocialPreference.QUIET.value,
            price_tier=PriceTier.LOW.value,
            recent_categories=["cafe", "bakery"],
        ),
    },
]


def _enum_matrix_scenarios(merchant_ids: list[str]) -> list[dict[str, Any]]:
    weather = list(WeatherNeed)
    social = list(SocialPreference)
    price = list(PriceTier)
    scenarios: list[dict[str, Any]] = []

    for index, mode in enumerate(MovementMode):
        name = f"matrix_{mode.value}"
        scenarios.append(
            {
                "name": name,
                "merchant_id": merchant_ids[index % len(merchant_ids)],
                "intent": _intent(
                    name=name.replace("_", "-"),
                    movement_mode=mode.value,
                    time_bucket=[
                        "weekday_morning",
                        "tuesday_lunch",
                        "weekday_evening",
                        "friday_evening",
                        "saturday_afternoon",
                        "saturday_late",
                        "sunday_midday",
                    ][index],
                    weather_need=weather[index % len(weather)].value,
                    social_preference=social[index % len(social)].value,
                    price_tier=price[index % len(price)].value,
                    recent_categories=[
                        ["cafe"],
                        ["bakery"],
                        ["restaurant"],
                        ["bar"],
                        ["club"],
                        ["retail"],
                        [],
                    ][index],
                    dwell_signal=index % 2 == 0,
                    battery_low=index % 3 == 0,
                ),
            }
        )

    return scenarios


def _summarize_result(name: str, status_code: int, data: dict[str, Any]) -> str:
    if data.get("offer_id"):
        merchant = data.get("merchant") or {}
        discount = data.get("discount") or {}
        genui = data.get("genui") or {}
        explainability = data.get("explainability") or []
        top_reason = explainability[0]["code"] if explainability else "-"
        return (
            f"{name:28} status={status_code} "
            f"offer={data.get('offer_id')} "
            f"merchant={merchant.get('id')}:{merchant.get('name')} "
            f"discount={discount.get('value')}{discount.get('type')} "
            f"source={discount.get('source')} "
            f"palette={genui.get('color_palette')} "
            f"reason={top_reason}"
        )

    reason = data.get("reason") or data.get("detail") or "-"
    recommendation = data.get("recommendation") or data.get("rule_id") or "-"
    decision_trace = data.get("decision_trace") or {}
    trace = decision_trace.get("trace") or []
    first_trace = trace[0] if trace else {}
    trace_code = first_trace.get("code", "-")
    trace_reason = first_trace.get("reason", reason)
    return (
        f"{name:28} status={status_code} "
        f"offer=None recommendation={recommendation} "
        f"trace={trace_code} reason={trace_reason}"
    )


def _debug_candidate_summary(data: dict[str, Any]) -> str:
    """
    Build a compact candidate diagnostics string from decision_trace.
    """
    decision_trace = data.get("decision_trace") or {}
    candidate_scores = decision_trace.get("candidate_scores") or []
    trace_items = decision_trace.get("trace") or []
    first_trace = trace_items[0] if trace_items else {}
    first_trace_code = first_trace.get("code", "-")

    if not candidate_scores:
        return f"candidate_debug trace={first_trace_code} candidates=none"

    top = sorted(
        candidate_scores,
        key=lambda item: float(item.get("score", 0.0)),
        reverse=True,
    )[:3]
    compact = ", ".join(
        f"{item.get('merchant_id')}:{float(item.get('score', 0.0)):.1f}:{item.get('recommendation')}"
        for item in top
    )
    return f"candidate_debug trace={first_trace_code} top3=[{compact}]"


def test_intent_api_sweep(client, capsys):
    osm_merchants = _osm_merchants_for_sweep()
    merchant_cells = sorted({m["grid_cell"] for m in osm_merchants if m["grid_cell"]})
    if len(merchant_cells) < 2:
        raise AssertionError("Expected seeded OSM merchants to span multiple H3 cells.")
    scenarios = FOCUSED_SCENARIOS + _enum_matrix_scenarios(
        [m["id"] for m in osm_merchants]
    )
    run_id = uuid.uuid4().hex[:8]
    current_dt = _seeded_sweep_current_dt()

    print(f"\nIntent API sweep: {len(scenarios)} scenarios")
    print(f"run_id={run_id} current_dt={current_dt} hour_of_week={SWEEP_HOUR_OF_WEEK}")
    print("agent_enabled=False for deterministic manual diagnostics")
    print("gemini_disabled=True; using smart fallback copy/genui")
    print("-" * 120)

    failures: list[str] = []
    for idx, scenario in enumerate(scenarios):
        intent = scenario["intent"].copy()
        intent["grid_cell"] = merchant_cells[idx % len(merchant_cells)]
        intent["session_id"] = f"{intent['session_id']}-{run_id}"
        demo_overrides = {
            **(scenario.get("demo_overrides") or {}),
            "current_dt": current_dt,
        }
        payload = {
            "intent": intent,
            "merchant_id": scenario.get("merchant_id"),
            "demo_overrides": demo_overrides,
        }

        response = client.post("/api/offers/generate", json=payload)
        try:
            data = response.json()
        except ValueError:
            failures.append(
                f"{scenario['name']} returned non-JSON response: {response.text[:300]}"
            )
            continue

        print(_summarize_result(scenario["name"], response.status_code, data))
        if response.status_code == 200 and not data.get("offer_id"):
            print(_debug_candidate_summary(data))
        print("")

        if response.status_code != 200:
            failures.append(
                f"{scenario['name']} returned HTTP {response.status_code}: {data}"
            )
        elif not (data.get("offer_id") or "reason" in data):
            failures.append(f"{scenario['name']} returned unexpected payload: {data}")

    captured = capsys.readouterr()
    print(captured.out)

    assert not failures, "\n".join(failures)
