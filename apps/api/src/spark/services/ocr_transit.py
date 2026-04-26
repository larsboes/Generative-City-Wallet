from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from spark.models.ocr import OCRTransitParseRequest, OCRTransitPayload

OCR_PARSE_TIMEOUT_SECONDS = 1.5
OCR_PARSE_RETRY_ATTEMPTS = 3
OCR_PARSE_RETRY_BASE_DELAY_SECONDS = 0.15


@dataclass(frozen=True)
class OCRParseResult:
    parsed: bool
    payload: OCRTransitPayload | None = None
    reason: str | None = None


class RuleBasedOCRTransitProvider:
    """
    Deterministic parser for OCR transit snippets.

    Expected text patterns include:
    - delay: "delay 14m", "14 min", "14 minutes"
    - return deadline: ISO timestamp or "return by HH:MM"
    """

    async def parse(self, request: OCRTransitParseRequest) -> OCRParseResult:
        text = request.raw_text.strip()
        delay_match = re.search(
            r"\b(\d{1,3})\s*(?:m|min|mins|minute|minutes)\b", text, re.I
        )
        if not delay_match:
            return OCRParseResult(parsed=False, reason="delay_not_found")

        delay_minutes = int(delay_match.group(1))
        if delay_minutes < 1 or delay_minutes > 180:
            return OCRParseResult(parsed=False, reason="delay_out_of_range")

        must_return_by = _extract_return_by(text)
        payload = OCRTransitPayload(
            city=request.city_hint,
            district=request.district_hint,
            transit_delay_minutes=delay_minutes,
            must_return_by=must_return_by,
            confidence=0.7,
        )
        return OCRParseResult(parsed=True, payload=payload)


class HybridRuleBasedOCRTransitProvider:
    """
    Stronger deterministic parser with broader extraction + confidence scoring.

    Captures line/station metadata when present and normalizes `return by HH:MM`
    into an ISO UTC timestamp for ingest compatibility.
    """

    async def parse(self, request: OCRTransitParseRequest) -> OCRParseResult:
        text = request.raw_text.strip()
        delay_minutes = _extract_delay_minutes(text)
        if delay_minutes is None:
            return OCRParseResult(parsed=False, reason="delay_not_found")
        if delay_minutes < 1 or delay_minutes > 180:
            return OCRParseResult(parsed=False, reason="delay_out_of_range")

        line = _extract_line(text)
        station = _extract_station(text)
        must_return_by = _extract_return_by_iso(text)

        confidence = _compute_confidence(
            delay_minutes=delay_minutes,
            has_line=bool(line),
            has_station=bool(station),
            has_must_return_by=bool(must_return_by),
            has_city_hint=bool(request.city_hint),
            has_district_hint=bool(request.district_hint),
        )

        payload = OCRTransitPayload(
            city=request.city_hint,
            district=request.district_hint,
            line=line,
            station=station,
            transit_delay_minutes=delay_minutes,
            must_return_by=must_return_by,
            confidence=confidence,
        )
        return OCRParseResult(parsed=True, payload=payload)


class ModelAssistedOCRTransitProvider:
    """
    Model-assisted extraction path with deterministic safety guards.

    This simulates a model-oriented adapter by accepting broader natural language
    patterns, then normalizing output through the same typed payload contract.
    """

    async def parse(self, request: OCRTransitParseRequest) -> OCRParseResult:
        text = request.raw_text.strip()
        delay_minutes = _extract_delay_minutes_model_assisted(text)
        if delay_minutes is None:
            return OCRParseResult(parsed=False, reason="delay_not_found")
        if delay_minutes < 1 or delay_minutes > 180:
            return OCRParseResult(parsed=False, reason="delay_out_of_range")

        line = _extract_line(text)
        station = _extract_station(text)
        must_return_by = _extract_return_by_iso(text)
        confidence = _compute_model_assisted_confidence(
            delay_minutes=delay_minutes,
            has_line=bool(line),
            has_station=bool(station),
            has_must_return_by=bool(must_return_by),
            has_city_hint=bool(request.city_hint),
            has_district_hint=bool(request.district_hint),
        )

        payload = OCRTransitPayload(
            city=request.city_hint,
            district=request.district_hint,
            line=line,
            station=station,
            transit_delay_minutes=delay_minutes,
            must_return_by=must_return_by,
            confidence=confidence,
        )
        return OCRParseResult(parsed=True, payload=payload)


def _extract_delay_minutes(text: str) -> int | None:
    patterns = [
        r"\b(?:delay(?:ed)?|versp[aä]tung|late)\s*(?:of|is|:)?\s*(\d{1,3})\s*(?:m|min|mins|minute|minutes)\b",
        r"\b(\d{1,3})\s*(?:m|min|mins|minute|minutes)\s*(?:delay|late|versp[aä]tung)?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1))
    return None


def _extract_delay_minutes_model_assisted(text: str) -> int | None:
    patterns = [
        r"\b(?:delay(?:ed)?|versp[aä]tung|late)\s*(?:of|is|:|about|approx(?:imately)?)?\s*(\d{1,3})\s*(?:m|min|mins|minute|minutes)\b",
        r"\b(?:about|approx(?:imately)?)\s*(\d{1,3})\s*(?:m|min|mins|minute|minutes)\s*(?:late|delay|versp[aä]tung)?\b",
        r"\b(\d{1,3})\s*(?:m|min|mins|minute|minutes)\s*(?:late|delay|versp[aä]tung)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1))
    return _extract_delay_minutes(text)


def _extract_line(text: str) -> str | None:
    line_match = re.search(
        r"\b((?:S|U|RB|RE|ICE|IC|M)\s?-?\s?\d{1,3}[A-Z]?)\b",
        text,
        re.I,
    )
    if not line_match:
        return None
    return re.sub(r"\s+", "", line_match.group(1).upper())


def _extract_station(text: str) -> str | None:
    # Common forms: "station Kottbusser Tor", "at Hauptbahnhof", "-> Alexanderplatz"
    patterns = [
        r"\bstation\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-\s]{1,40}?)(?=\s+(?:delay|return|versp[aä]tung|late)\b|$)",
        r"\bat\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9\-\s]{1,60}?)(?=\s+(?:delay|return|versp[aä]tung|late)\b|$)",
        r"->\s*([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-\s]{1,40})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        value = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;")
        value = re.sub(
            r"\s+(?:about|approx(?:imately)?)\s+\d{1,3}\s*(?:m|min|mins|minute|minutes)\s*$",
            "",
            value,
            flags=re.I,
        ).strip(" .,:;")
        if value:
            return value
    return None


def _extract_return_by_iso(text: str) -> str | None:
    # ISO-like capture (e.g., 2026-04-26T12:30:00Z)
    iso_match = re.search(
        r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\b",
        text,
    )
    if iso_match:
        return iso_match.group(0)

    hhmm_match = re.search(r"return\s+by\s+(\d{1,2}):(\d{2})", text, re.I)
    if not hhmm_match:
        return None

    hour = int(hhmm_match.group(1))
    minute = int(hhmm_match.group(2))
    if hour > 23 or minute > 59:
        return None

    now = datetime.now(timezone.utc)
    normalized = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if normalized < now:
        # If time already passed today, roll forward one day.
        normalized = normalized + timedelta(days=1)
    return normalized.strftime("%Y-%m-%dT%H:%M:%SZ")


def _compute_confidence(
    *,
    delay_minutes: int,
    has_line: bool,
    has_station: bool,
    has_must_return_by: bool,
    has_city_hint: bool,
    has_district_hint: bool,
) -> float:
    score = 0.55
    if 1 <= delay_minutes <= 90:
        score += 0.1
    if has_line:
        score += 0.1
    if has_station:
        score += 0.1
    if has_must_return_by:
        score += 0.1
    if has_city_hint:
        score += 0.025
    if has_district_hint:
        score += 0.025
    return round(min(score, 0.98), 3)


def _compute_model_assisted_confidence(
    *,
    delay_minutes: int,
    has_line: bool,
    has_station: bool,
    has_must_return_by: bool,
    has_city_hint: bool,
    has_district_hint: bool,
) -> float:
    score = 0.62
    if 1 <= delay_minutes <= 90:
        score += 0.08
    if has_line:
        score += 0.08
    if has_station:
        score += 0.08
    if has_must_return_by:
        score += 0.08
    if has_city_hint:
        score += 0.02
    if has_district_hint:
        score += 0.02
    return round(min(score, 0.97), 3)


def _extract_return_by(text: str) -> str | None:
    # ISO-like capture (e.g., 2026-04-26T12:30:00Z)
    iso_match = re.search(
        r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\b",
        text,
    )
    if iso_match:
        return iso_match.group(0)

    hhmm_match = re.search(r"return\s+by\s+(\d{1,2}):(\d{2})", text, re.I)
    if not hhmm_match:
        return None

    hour = int(hhmm_match.group(1))
    minute = int(hhmm_match.group(2))
    if hour > 23 or minute > 59:
        return None
    # Keep date-free HH:MM for now; ingress validator can reject/transform if required.
    return f"{hour:02d}:{minute:02d}"


async def parse_ocr_transit_with_policy(
    request: OCRTransitParseRequest,
) -> tuple[OCRParseResult, int]:
    provider = _provider_for(request.parser_provider)
    attempts = 0
    last_reason = "parse_failed"

    for attempt in range(1, OCR_PARSE_RETRY_ATTEMPTS + 1):
        attempts = attempt
        try:
            result = await asyncio.wait_for(
                provider.parse(request),
                timeout=OCR_PARSE_TIMEOUT_SECONDS,
            )
            if result.parsed:
                return result, attempts
            last_reason = result.reason or "parse_failed"
        except TimeoutError:
            last_reason = "parse_timeout"

        if attempt < OCR_PARSE_RETRY_ATTEMPTS:
            delay = OCR_PARSE_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            await asyncio.sleep(delay)

    return OCRParseResult(parsed=False, reason=last_reason), attempts


def _provider_for(parser_provider: str):
    if parser_provider == "rule_based":
        return RuleBasedOCRTransitProvider()
    if parser_provider == "model_assisted":
        return ModelAssistedOCRTransitProvider()
    return HybridRuleBasedOCRTransitProvider()
