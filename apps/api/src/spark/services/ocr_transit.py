from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

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
        delay_match = re.search(r"\b(\d{1,3})\s*(?:m|min|mins|minute|minutes)\b", text, re.I)
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
    provider = RuleBasedOCRTransitProvider()
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
