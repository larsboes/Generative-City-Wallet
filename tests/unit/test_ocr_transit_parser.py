from __future__ import annotations

import asyncio

from spark.models.ocr import OCRTransitParseRequest
from spark.services.ocr_transit import parse_ocr_transit_with_policy


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


def test_rule_based_parser_returns_reason_when_delay_missing():
    request = OCRTransitParseRequest(
        raw_text="Berlin transit board says delayed but no minutes shown",
    )
    result, attempts = asyncio.run(parse_ocr_transit_with_policy(request))
    assert attempts == 3
    assert result.parsed is False
    assert result.reason == "delay_not_found"
