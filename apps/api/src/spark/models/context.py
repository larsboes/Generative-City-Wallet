from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

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
    grid_cell: str = Field(
        description="Canonical H3 cell ID (for example, resolution 9)."
    )
    movement_mode: MovementMode
    time_bucket: str = Field(description="e.g. tuesday_lunch, friday_evening")
    weather_need: WeatherNeed
    social_preference: SocialPreference
    price_tier: PriceTier
    recent_categories: list[str] = Field(default_factory=list)
    dwell_signal: bool = False
    battery_low: bool = False
    session_id: str
    continuity_hint: str | None = None
    activity_signal: Literal["none", "active_recently", "post_workout", "resting"] = (
        "none"
    )
    activity_source: Literal[
        "none", "strava", "native_health", "hybrid", "movement_inferred"
    ] = "none"
    activity_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    location_grid_accuracy_m: Optional[int] = Field(default=None, ge=10, le=500)


class IntentFieldProvenance(BaseModel):
    field: str
    policy: Literal["authoritative", "advisory", "derived", "ignored"]
    client_value: Any = None
    final_value: Any = None
    action: Literal["accepted", "overridden", "derived", "ignored"]
    reason: str
    source: str


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
    intent_provenance: list[IntentFieldProvenance] = Field(default_factory=list)
    continuity_id: str | None = None
    continuity_source: str | None = None
    continuity_expires_at: str | None = None
    social_preference: SocialPreference
    price_tier: PriceTier


class EnvironmentContext(BaseModel):
    weather_condition: str
    temp_celsius: float
    feels_like_celsius: float
    weather_need: str
    vibe_signal: str
    source: Optional[str] = None
    provider_available: Optional[bool] = None
    cache_hit: Optional[bool] = None


class PlaceContext(BaseModel):
    source: str
    provider_available: bool = False
    nearby_place_count: int = 0
    avg_rating: Optional[float] = None
    avg_busyness: Optional[float] = None
    popular_place_name: Optional[str] = None


class EventContext(BaseModel):
    source: str
    provider_available: bool = False
    events_tonight_count: int = 0
    nearest_event_name: Optional[str] = None
    cache_hit: bool = False
    error_reason: Optional[str] = None
    http_status: Optional[int] = None


class ExternalContext(BaseModel):
    place: PlaceContext
    events: EventContext


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
    external: Optional[ExternalContext] = None
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
