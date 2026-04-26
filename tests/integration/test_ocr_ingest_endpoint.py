from __future__ import annotations

from fastapi.testclient import TestClient

from spark.main import app


def test_ocr_ingest_low_confidence_is_not_accepted():
    with TestClient(app) as client:
        response = client.post(
            "/api/ocr/transit",
            json={
                "city": "Berlin",
                "district": "Kreuzberg",
                "line": "U1",
                "station": "Kottbusser Tor",
                "transit_delay_minutes": 15,
                "must_return_by": "2026-04-26T12:30:00Z",
                "confidence": 0.4,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["reason"] == "confidence_below_threshold"


def test_ocr_ingest_invalid_must_return_by_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/ocr/transit",
            json={
                "city": "Berlin",
                "district": "Kreuzberg",
                "line": "U8",
                "station": "Moritzplatz",
                "transit_delay_minutes": 20,
                "must_return_by": "not-a-timestamp",
                "confidence": 0.9,
            },
        )
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_must_return_by"


def test_ocr_parse_endpoint_returns_structured_payload():
    with TestClient(app) as client:
        response = client.post(
            "/api/ocr/transit/parse",
            json={
                "raw_text": "U1 Kreuzberg delay 18 minutes return 2026-04-26T18:45:00Z",
                "city_hint": "Berlin",
                "district_hint": "Kreuzberg",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["parsed"] is True
    assert body["payload"]["transit_delay_minutes"] == 18
    assert body["payload"]["must_return_by"] == "2026-04-26T18:45:00Z"
    assert body["attempts"] >= 1


def test_ocr_ingest_threshold_boundary_is_accepted():
    with TestClient(app) as client:
        response = client.post(
            "/api/ocr/transit",
            json={
                "city": "Berlin",
                "district": "Kreuzberg",
                "line": "U3",
                "station": "Gorlitzer Bahnhof",
                "transit_delay_minutes": 12,
                "must_return_by": "2026-04-26T12:30:00Z",
                "confidence": 0.6,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["reason"] is None
