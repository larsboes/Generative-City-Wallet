"""
Spark shared contracts — Pydantic models.
TypeScript mirror: `packages/shared` (`@spark/shared`).
Frozen from day 1. If you change a field, tell everyone.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Mobile → Backend ──────────────────────────────────────────────────────────


class MovementMode(str, Enum):
    BROWSING = "browsing"
    COMMUTING = "commuting"
    STATIONARY = "stationary"
    TRANSIT_WAITING = "transit_waiting"
    EXERCISING = "exercising"
    POST_WORKOUT = "post_workout"
    CYCLING = "cycling"


class WeatherNeed(str, Enum):
    WARMTH_SEEKING = "warmth_seeking"
    REFRESHMENT_SEEKING = "refreshment_seeking"
    SHELTER_SEEKING = "shelter_seeking"
    NEUTRAL = "neutral"


class SocialPreference(str, Enum):
    SOCIAL = "social"
    QUIET = "quiet"
    NEUTRAL = "neutral"


class PriceTier(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


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


# ── Density Signal ────────────────────────────────────────────────────────────


class DensitySignalType(str, Enum):
    FLASH = "FLASH"
    PRIORITY = "PRIORITY"
    QUIET = "QUIET"
    NORMAL = "NORMAL"
    NORMALLY_CLOSED = "NORMALLY_CLOSED"


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


# ── Merchant Demand (subset inside CompositeContextState) ─────────────────────


class MerchantDemand(BaseModel):
    density_score: float
    drop_pct: float
    signal: DensitySignalType
    offer_eligible: bool
    current_occupancy_pct: Optional[float] = None
    predicted_occupancy_pct: Optional[float] = None


class CouponType(str, Enum):
    FLASH = "FLASH"
    MILESTONE = "MILESTONE"
    TIME_BOUND = "TIME_BOUND"
    DRINK = "DRINK"
    VISIBILITY_ONLY = "VISIBILITY_ONLY"


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


class ConflictRecommendation(str, Enum):
    RECOMMEND = "RECOMMEND"
    RECOMMEND_WITH_FRAMING = "RECOMMEND_WITH_FRAMING"
    DO_NOT_RECOMMEND = "DO_NOT_RECOMMEND"


class ConflictResolutionContext(BaseModel):
    recommendation: ConflictRecommendation
    framing_band: Optional[str] = None
    allowed_vocabulary: list[str] = Field(default_factory=list)
    banned_vocabulary: list[str] = Field(default_factory=list)


# ── Backend → Gemini Flash API ────────────────────────────────────────────────


class CompositeContextState(BaseModel):
    timestamp: str
    session_id: str
    user: UserContext
    merchant: MerchantContext
    environment: EnvironmentContext
    conflict_resolution: ConflictResolutionContext


# ── Gemini Flash → Backend (raw LLM output, before hard rails) ────────────────


class LLMContent(BaseModel):
    headline: str
    subtext: str
    cta_text: str
    emotional_hook: Optional[str] = None


class ColorPalette(str, Enum):
    WARM_AMBER = "warm_amber"
    COOL_BLUE = "cool_blue"
    DEEP_GREEN = "deep_green"
    ELECTRIC_PURPLE = "electric_purple"
    SOFT_CREAM = "soft_cream"
    DARK_CONTRAST = "dark_contrast"
    SUNSET_ORANGE = "sunset_orange"


class CardMood(str, Enum):
    COZY = "cozy"
    ENERGETIC = "energetic"
    REFRESHING = "refreshing"
    CELEBRATORY = "celebratory"
    CALM = "calm"


class LLMGenUI(BaseModel):
    color_palette: ColorPalette
    typography_weight: str
    background_style: str
    imagery_prompt: str
    urgency_style: str
    card_mood: CardMood


class LLMOfferOutput(BaseModel):
    content: LLMContent
    genui: LLMGenUI
    framing_band_used: str = ""


# ── Final Offer Object (post hard-rails, sent to mobile) ──────────────────────


class DiscountInfo(BaseModel):
    value: float
    type: str  # percentage | cover_refund | drink | none
    source: str = "merchant_rules_db"


class MerchantInfo(BaseModel):
    id: str
    name: str
    distance_m: float
    address: str
    category: str


class AuditInfo(BaseModel):
    rails_applied: bool = True
    discount_original_llm: float = 0
    discount_capped_to: float = 0
    composite_state_hash: str = ""


class ExplainabilityReason(BaseModel):
    code: str
    reason: str
    score: float = 0.0
    metadata: dict = Field(default_factory=dict)


class OfferObject(BaseModel):
    offer_id: str
    session_id: str
    merchant: MerchantInfo
    discount: DiscountInfo
    content: LLMContent
    genui: LLMGenUI
    expires_at: str
    qr_payload: Optional[str] = None
    explainability: list[ExplainabilityReason] = Field(default_factory=list)
    _audit: Optional[AuditInfo] = None


# ── QR Redemption ─────────────────────────────────────────────────────────────


class QRPayload(BaseModel):
    offer_id: str
    token_hash: str
    expiry_unix: int


class RedemptionValidationRequest(BaseModel):
    qr_payload: str
    merchant_id: str


class RedemptionValidationResponse(BaseModel):
    valid: bool
    offer_id: Optional[str] = None
    discount_value: Optional[float] = None
    discount_type: Optional[str] = None
    error: Optional[str] = (
        None  # EXPIRED | ALREADY_REDEEMED | INVALID_TOKEN | WRONG_MERCHANT
    )


# ── Cashback Credit ───────────────────────────────────────────────────────────


class CashbackCredit(BaseModel):
    session_id: str
    offer_id: str
    amount_eur: float
    merchant_name: str
    credited_at: str
    wallet_balance_eur: float


# ── Conflict Resolution (standalone endpoint) ─────────────────────────────────


class ConflictResolveRequest(BaseModel):
    merchant_id: str
    user_social_pref: SocialPreference
    current_txn_rate: float
    current_dt: str
    active_coupon: Optional[dict] = None


class ConflictResolveResponse(BaseModel):
    recommendation: ConflictRecommendation
    framing_band: Optional[str] = None
    coupon_mechanism: Optional[str] = None
    reason: str
    recheck_in_minutes: Optional[int] = None


# ── Demo Overrides (Context Slider) ───────────────────────────────────────────


class DemoOverrides(BaseModel):
    """Optional overrides from the Context Slider demo panel."""

    temp_celsius: Optional[float] = None
    weather_condition: Optional[str] = None
    merchant_occupancy_pct: Optional[float] = None
    social_preference: Optional[SocialPreference] = None
    time_bucket: Optional[str] = None


class GenerateOfferRequest(BaseModel):
    """Request accepted by the offer generation endpoint."""

    intent: IntentVector
    merchant_id: Optional[str] = None  # None = auto-select best merchant
    demo_overrides: Optional[DemoOverrides] = None


# ── Venue Occupancy (Finn's demand signal system) ────────────────────────────


class Venue(BaseModel):
    merchant_id: str
    osm_type: Optional[str] = None
    osm_id: Optional[str] = None
    name: str
    category: str
    lat: float
    lon: float
    city: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    opening_hours: Optional[str] = None
    source: str = "openstreetmap"


class VenueListResponse(BaseModel):
    venues: list[Venue]
    count: int


class DemandContext(BaseModel):
    density_score: float = Field(ge=0)
    drop_pct: float = Field(ge=0, le=1)
    signal: str  # FLASH | PRIORITY | QUIET | NORMAL | NORMALLY_CLOSED
    offer_eligible: bool
    current_txn_rate: float = Field(ge=0)
    historical_avg: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    current_occupancy_pct: Optional[float] = Field(default=None, ge=0, le=1)
    predicted_occupancy_pct: Optional[float] = Field(default=None, ge=0, le=1)


class OccupancyResponse(BaseModel):
    merchant_id: str
    name: str
    category: str
    city: Optional[str] = None
    timestamp: datetime
    demand: DemandContext


class OccupancyQueryRequest(BaseModel):
    merchant_ids: list[str] = Field(min_length=1, max_length=50)
    timestamp: Optional[datetime] = None
    arrival_offset_minutes: int = Field(default=10, ge=0, le=240)


class OccupancyQueryResponse(BaseModel):
    results: list[OccupancyResponse]
    count: int


class TransactionGenerationRequest(BaseModel):
    merchant_ids: Optional[list[str]] = Field(default=None, max_length=500)
    city: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=500)
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    days: int = Field(default=28, ge=1, le=365)
    seed: Optional[int] = None


class LiveUpdateRequest(BaseModel):
    merchant_ids: Optional[list[str]] = Field(default=None, max_length=500)
    city: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=500)
    timestamp: Optional[datetime] = None
    seed: Optional[int] = None


class TransactionGenerationResponse(BaseModel):
    inserted_count: int
    venue_count: int
    start: datetime
    end: datetime
    source: str


class HourlyTransactionBucket(BaseModel):
    hour: int = Field(ge=0, le=23)
    transaction_count: int = Field(ge=0)
    total_revenue_eur: float = Field(ge=0)
    avg_ticket_eur: float = Field(ge=0)


class DailyTransactionsResponse(BaseModel):
    merchant_id: str
    date: date
    transaction_count: int = Field(ge=0)
    total_revenue_eur: float = Field(ge=0)
    avg_ticket_eur: float = Field(ge=0)
    hourly: list[HourlyTransactionBucket]


class HourlyAverageBucket(BaseModel):
    hour: int = Field(ge=0, le=23)
    avg_transaction_count: float = Field(ge=0)
    avg_revenue_eur: float = Field(ge=0)


class TransactionAveragesResponse(BaseModel):
    merchant_id: str
    lookback_days: int
    avg_daily_transactions: float = Field(ge=0)
    avg_daily_revenue_eur: float = Field(ge=0)
    avg_ticket_eur: float = Field(ge=0)
    hourly: list[HourlyAverageBucket]


class RevenueDay(BaseModel):
    date: date
    transaction_count: int = Field(ge=0)
    total_revenue_eur: float = Field(ge=0)
    avg_ticket_eur: float = Field(ge=0)


class RevenueLast7DaysResponse(BaseModel):
    merchant_id: str
    days: list[RevenueDay]
    total_revenue_eur: float = Field(ge=0)


class HourRankingBucket(BaseModel):
    hour: int = Field(ge=0, le=23)
    avg_transaction_count: float = Field(ge=0)
    avg_revenue_eur: float = Field(ge=0)


class HourRankingsResponse(BaseModel):
    merchant_id: str
    lookback_days: int
    fastest_hours: list[HourRankingBucket]
    slowest_hours: list[HourRankingBucket]


class DashboardHourlyBucket(HourlyTransactionBucket):
    comparison_avg_transaction_count: float = Field(ge=0)
    comparison_avg_revenue_eur: float = Field(ge=0)


class VendorDashboardTodayResponse(BaseModel):
    merchant_id: str
    date: date
    current_hour: int = Field(ge=0, le=23)
    hourly: list[DashboardHourlyBucket]
    demand: DemandContext
    revenue_last_7_days: RevenueLast7DaysResponse
