from __future__ import annotations

import asyncio

from spark.models.ocr import OCRTransitParseRequest
from spark.services.ocr_transit import parse_ocr_transit_with_policy
import spark.services.ocr_transit as ocr_module


def test_rule_based_parser_extracts_delay_and_iso_return_by():
    request = OCRTransitParseRequest(
        raw_text="Berlin U1 Kreuzberg delay 14m return 2026-04-26T12:30:00Z",
        city_hint="Berlin",
        district_hint="Kreuzberg",
    )
    result, attempts = asyncio.run(parse_ocr_transit_with_policy(request))
    assert attempts >= 1
    assert result.parsed is True
    assert result.payload is not None
    assert result.payload.transit_delay_minutes == 14
    assert result.payload.must_return_by == "2026-04-26T12:30:00Z"
    assert result.payload.city == "Berlin"
    assert result.payload.district == "Kreuzberg"


def test_hybrid_parser_extracts_line_station_and_confidence():
    request = OCRTransitParseRequest(
        raw_text="U1 station Kottbusser Tor delay 18 minutes return by 21:40",
        city_hint="Berlin",
        district_hint="Kreuzberg",
        parser_provider="hybrid_rule_based",
    )
    result, attempts = asyncio.run(parse_ocr_transit_with_policy(request))
    assert attempts >= 1
    assert result.parsed is True
    assert result.payload is not None
    assert result.payload.transit_delay_minutes == 18
    assert result.payload.line == "U1"
    assert result.payload.station == "Kottbusser Tor"
    assert result.payload.must_return_by is not None
    assert result.payload.must_return_by.endswith("Z")
    assert result.payload.confidence >= 0.8


def test_model_assisted_parser_handles_approximate_delay_language():
    request = OCRTransitParseRequest(
        raw_text="S8 at Ostbahnhof approximately 22 minutes late return by 19:15",
        city_hint="Berlin",
        district_hint="Friedrichshain",
        parser_provider="model_assisted",
    )
    result, attempts = asyncio.run(parse_ocr_transit_with_policy(request))
    assert attempts >= 1
    assert result.parsed is True
    assert result.payload is not None
    assert result.payload.transit_delay_minutes == 22
    assert result.payload.line == "S8"
    assert result.payload.station == "Ostbahnhof"
    assert result.payload.must_return_by is not None
    assert result.payload.must_return_by.endswith("Z")
    assert result.payload.confidence >= 0.78


def test_rule_based_parser_returns_reason_when_delay_missing():
    request = OCRTransitParseRequest(
        raw_text="Berlin transit board says delayed but no minutes shown",
    )
    result, attempts = asyncio.run(parse_ocr_transit_with_policy(request))
    assert attempts == 3
    assert result.parsed is False
    assert result.reason == "delay_not_found"


def test_model_assisted_parser_out_of_range_delay_is_rejected():
    request = OCRTransitParseRequest(
        raw_text="delay is approximately 240 minutes",
        parser_provider="model_assisted",
    )
    result, attempts = asyncio.run(parse_ocr_transit_with_policy(request))
    assert attempts == 3
    assert result.parsed is False
    assert result.reason == "delay_out_of_range"


def test_parser_timeout_retries_and_returns_timeout_reason(monkeypatch):
    async def always_timeout(self, request):  # noqa: ANN001
        raise TimeoutError()

    monkeypatch.setattr(
        ocr_module.HybridRuleBasedOCRTransitProvider,
        "parse",
        always_timeout,
    )
    request = OCRTransitParseRequest(raw_text="delay 12m")
    result, attempts = asyncio.run(parse_ocr_transit_with_policy(request))
    assert attempts == 3
    assert result.parsed is False
    assert result.reason == "parse_timeout"
