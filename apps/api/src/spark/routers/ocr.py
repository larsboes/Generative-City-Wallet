from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from fastapi import HTTPException

from spark.models.ocr import (
    OCRTransitIngestResponse,
    OCRTransitParseRequest,
    OCRTransitParseResponse,
    OCRTransitPayload,
)
from spark.services.ocr_transit import parse_ocr_transit_with_policy

router = APIRouter(prefix="/api/ocr", tags=["ocr"])
OCR_CONFIDENCE_THRESHOLD = 0.6


@router.post("/transit", response_model=OCRTransitIngestResponse)
async def ingest_ocr_transit(payload: OCRTransitPayload):
    """
    Lightweight OCR transit ingestion endpoint.

    For MVP this endpoint validates and echoes a structured payload that can be
    forwarded into offer generation (`ocr_transit` field in GenerateOfferRequest).
    """
    if payload.must_return_by:
        try:
            datetime.fromisoformat(payload.must_return_by.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="invalid_must_return_by"
            ) from exc

    accepted = payload.confidence >= OCR_CONFIDENCE_THRESHOLD
    reason = None
    if not accepted:
        reason = "confidence_below_threshold"

    return OCRTransitIngestResponse(
        accepted=accepted,
        transit_delay_minutes=payload.transit_delay_minutes,
        must_return_by=payload.must_return_by,
        confidence=payload.confidence,
        reason=reason,
    )


@router.post("/transit/parse", response_model=OCRTransitParseResponse)
async def parse_ocr_transit(request: OCRTransitParseRequest):
    """
    Parse raw OCR text into structured transit delay payload.

    This endpoint applies adapter policy (timeout + retries) and returns a
    deterministic shape for downstream `/api/ocr/transit` and offer pipelines.
    """
    result, attempts = await parse_ocr_transit_with_policy(request)
    return OCRTransitParseResponse(
        parsed=result.parsed,
        payload=result.payload,
        parser_provider=request.parser_provider,
        attempts=attempts,
        reason=result.reason,
    )
