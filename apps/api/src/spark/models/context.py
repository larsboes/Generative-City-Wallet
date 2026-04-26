from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from spark.models.common import (
    ConflictRecommendation,
    CouponType,
    DensitySignalType,
    MovementMode,
    PriceTier,
    SocialPreference,
    WeatherNeed,
)


class IntentVector(BaseModel):
    grid_cell: str = Field(description="e.g. STR-MITTE-047 — 50m quantization")
    movement_mode: MovementMode
    time_bucket: str = Field(description="e.g. tuesday_lunch, friday_evening")
    weather_need: WeatherNeed
    social_preference: SocialPreference
    price_tier: PriceTier
    recent_categories: list[str] = Field(default_factory=list)
    dwell_signal: bool = False
    battery_low: bool = False
    session_id: str


class DensitySignal(BaseModel):
    merchant_id: str
    density_score: float
    drop_pct: float
    signal: DensitySignalType
    offer_eligible: bool
    historical_avg: float
    current_rate: float
    current_occupancy_pct: Optional[float] = None
    predicted_occupancy_pct: Optional[float] = None
    confidence: float = 1.0
    timestamp: str = ""


class MerchantDemand(BaseModel):
    density_score: float
    drop_pct: float
    signal: DensitySignalType
    offer_eligible: bool
    current_occupancy_pct: Optional[float] = None
    predicted_occupancy_pct: Optional[float] = None


class ActiveCoupon(BaseModel):
    type: Optional[CouponType] = None
    max_discount_pct: float = 0
    valid_window_min: int = 20
    config: Optional[dict] = None


class MerchantContext(BaseModel):
    id: str
    name: str
    category: str
    distance_m: float
    address: str
    demand: MerchantDemand
    active_coupon: ActiveCoupon
    inventory_signal: Optional[str] = None
    tone_preference: Optional[str] = None


class UserContext(BaseModel):
    intent: IntentVector
    preference_scores: dict[str, float] = Field(default_factory=dict)
    social_preference: SocialPreference
    price_tier: PriceTier


class EnvironmentContext(BaseModel):
    weather_condition: str
    temp_celsius: float
    feels_like_celsius: float
    weather_need: str
    vibe_signal: str


class ConflictResolutionContext(BaseModel):
    recommendation: ConflictRecommendation
    framing_band: Optional[str] = None
    allowed_vocabulary: list[str] = Field(default_factory=list)
    banned_vocabulary: list[str] = Field(default_factory=list)


class DecisionTraceItem(BaseModel):
    code: str
    reason: str
    score: float = 0.0
    metadata: dict[str, object] = Field(default_factory=dict)


class OfferDecisionTrace(BaseModel):
    recommendation: ConflictRecommendation
    selected_merchant_id: Optional[str] = None
    selected_merchant_score: float = 0.0
    recheck_in_minutes: Optional[int] = None
    candidate_scores: list[dict[str, object]] = Field(default_factory=list)
    trace: list[DecisionTraceItem] = Field(default_factory=list)


class CompositeContextState(BaseModel):
    timestamp: str
    session_id: str
    user: UserContext
    merchant: MerchantContext
    environment: EnvironmentContext
    conflict_resolution: ConflictResolutionContext
    decision_trace: Optional[OfferDecisionTrace] = None


class DemoOverrides(BaseModel):
    """Optional overrides from the Context Slider demo panel."""

    temp_celsius: Optional[float] = None
    weather_condition: Optional[str] = None
    merchant_occupancy_pct: Optional[float] = None
    social_preference: Optional[SocialPreference] = None
    time_bucket: Optional[str] = None
    current_dt: Optional[datetime] = None
    transit_delay_minutes: Optional[int] = Field(default=None, ge=1, le=180)
    must_return_by: Optional[str] = None

