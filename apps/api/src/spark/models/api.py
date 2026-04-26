from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from spark.models.context import DemoOverrides, IntentVector
from spark.models.ocr import OCRTransitPayload


class GenerateOfferRequest(BaseModel):
    """Request accepted by the offer generation endpoint."""

    intent: IntentVector
    merchant_id: Optional[str] = None
    demo_overrides: Optional[DemoOverrides] = None
    transit_delay_minutes: Optional[int] = Field(default=None, ge=1, le=180)
    must_return_by: Optional[str] = None
    ocr_transit: Optional[OCRTransitPayload] = None


class WalletSeedItem(BaseModel):
    category: str = Field(min_length=1)
    weight: float = Field(default=0.25, ge=0.0, le=1.0)
    source_type: str = Field(default="wallet_pass", min_length=1, max_length=40)
    source_confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    artifact_count: int = Field(default=1, ge=1, le=20)


class WalletSeedRequest(BaseModel):
    seeds: list[WalletSeedItem] = Field(min_length=1, max_length=50)


class WalletSeedResponse(BaseModel):
    session_id: str
    applied: int = 0
    skipped: int = 0
    duplicates: int = 0
    suppressed_by_guardrail: int = 0
    avg_quality_multiplier: float = 0.0
    normalized_source_types: list[str] = Field(default_factory=list)
    governance_confidence_caps: dict[str, float] = Field(default_factory=dict)


class ContinuityResetRequest(BaseModel):
    session_id: str = Field(min_length=1)
    continuity_hint: str | None = None
    opt_out: bool = False


class ContinuityResetResponse(BaseModel):
    session_id: str
    continuity_id: str | None = None
    continuity_hint: str | None = None
    source: str
    expires_at: str
    reset_applied: bool
    opt_out: bool


class GenerateOfferBlockedResponse(BaseModel):
    offer: None = None
    reason: str
    rule_id: Optional[str] = None
    recheck_in_minutes: Optional[int] = None
    graph_decision: Optional[dict] = None
    pipeline: Optional[str] = None
    recommendation: Optional[str] = None
    decision_trace: Optional[dict] = None
