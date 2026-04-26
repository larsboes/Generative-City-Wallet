from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OCRTransitPayload(BaseModel):
    city: str | None = None
    district: str | None = None
    line: str | None = None
    station: str | None = None
    transit_delay_minutes: int = Field(ge=1, le=180)
    must_return_by: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class OCRTransitIngestResponse(BaseModel):
    accepted: bool
    transit_delay_minutes: int
    must_return_by: str | None = None
    confidence: float
    reason: str | None = None


class OCRTransitParseRequest(BaseModel):
    raw_text: str = Field(min_length=5, max_length=10000)
    city_hint: str | None = None
    district_hint: str | None = None
    parser_provider: Literal["rule_based", "hybrid_rule_based", "model_assisted"] = (
        "hybrid_rule_based"
    )


class OCRTransitParseResponse(BaseModel):
    parsed: bool
    payload: OCRTransitPayload | None = None
    parser_provider: str
    attempts: int
    reason: str | None = None
