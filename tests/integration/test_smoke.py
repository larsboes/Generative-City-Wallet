"""
Smoke tests — verify the backend starts and core endpoints return sane data.
"""

import pytest
from fastapi.testclient import TestClient

from spark.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_merchants_list(client):
    resp = client.get("/api/payone/merchants")
    assert resp.status_code == 200
    merchants = resp.json()
    assert len(merchants) >= 1
    assert all("merchant_id" in m and m["merchant_id"] for m in merchants)
    assert all("name" in m and m["name"] for m in merchants)


def test_density_endpoint(client):
    resp = client.get("/api/payone/density/MERCHANT_001")
    assert resp.status_code == 200
    data = resp.json()
    assert "density_score" in data
    assert "signal" in data
    assert data["merchant_id"] == "MERCHANT_001"


def test_offer_generation(client):
    payload = {
        "intent": {
            "grid_cell": "STR-MITTE-047",
            "movement_mode": "browsing",
            "time_bucket": "tuesday_lunch",
            "weather_need": "warmth_seeking",
            "social_preference": "quiet",
            "price_tier": "mid",
            "recent_categories": ["cafe"],
            "dwell_signal": False,
            "battery_low": False,
            "session_id": "test-smoke-001",
        },
        "merchant_id": "MERCHANT_001",
    }
    resp = client.post("/api/offers/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Could be an offer or a DO_NOT_RECOMMEND
    if data.get("offer_id"):
        assert data["merchant"]["name"] == "Café Römer"
        assert data["discount"]["source"] == "merchant_rules_db"
        assert "explainability" in data
        assert isinstance(data["explainability"], list)
        assert data["genui"]["color_palette"] in [
            "warm_amber",
            "cool_blue",
            "deep_green",
            "electric_purple",
            "soft_cream",
            "dark_contrast",
            "sunset_orange",
        ]
        assert data["qr_payload"].startswith("spark://redeem/")


def test_offer_genui_vibe_shift(client):
    """Verify different contexts produce different GenUI palettes."""
    cold_payload = {
        "intent": {
            "grid_cell": "STR-MITTE-047",
            "movement_mode": "browsing",
            "time_bucket": "tuesday_lunch",
            "weather_need": "warmth_seeking",
            "social_preference": "quiet",
            "price_tier": "mid",
            "recent_categories": [],
            "dwell_signal": False,
            "battery_low": False,
            "session_id": "test-vibe-cold",
        },
        "merchant_id": "MERCHANT_001",
        "demo_overrides": {"temp_celsius": 5, "weather_condition": "rain"},
    }
    hot_payload = {
        "intent": {
            "grid_cell": "STR-MITTE-047",
            "movement_mode": "browsing",
            "time_bucket": "tuesday_lunch",
            "weather_need": "refreshment_seeking",
            "social_preference": "neutral",
            "price_tier": "mid",
            "recent_categories": [],
            "dwell_signal": False,
            "battery_low": False,
            "session_id": "test-vibe-hot",
        },
        "merchant_id": "MERCHANT_001",
        "demo_overrides": {"temp_celsius": 32, "weather_condition": "sunny"},
    }

    cold_resp = client.post("/api/offers/generate", json=cold_payload).json()
    hot_resp = client.post("/api/offers/generate", json=hot_payload).json()

    # Both should return offers (not DO_NOT_RECOMMEND)
    if cold_resp.get("offer_id") and hot_resp.get("offer_id"):
        assert cold_resp["genui"]["color_palette"] != hot_resp["genui"]["color_palette"]


def test_conflict_resolution(client):
    payload = {
        "merchant_id": "MERCHANT_003",
        "user_social_pref": "social",
        "current_txn_rate": 2.8,
        "current_dt": "2025-06-14T21:14:00",
    }
    resp = client.post("/api/conflict/resolve", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendation"] in [
        "RECOMMEND",
        "RECOMMEND_WITH_FRAMING",
        "DO_NOT_RECOMMEND",
    ]
    assert "reason" in data


def test_context_provider_status(client):
    resp = client.get("/api/context/provider-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["grid_cell"] == "STR-MITTE-047"
    assert "weather" in data
    assert "external" in data
    assert "place" in data["external"]
    assert "events" in data["external"]
