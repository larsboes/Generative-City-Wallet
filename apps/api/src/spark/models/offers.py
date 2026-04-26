from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


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


class DiscountInfo(BaseModel):
    value: float
    type: str
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
    mapping_actions: list[dict[str, Any]] = Field(default_factory=list)


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
    audit_info: Optional[AuditInfo] = Field(default=None, exclude=True)


class CashbackCredit(BaseModel):
    session_id: str
    offer_id: str
    amount_eur: float
    merchant_name: str
    credited_at: str
    wallet_balance_eur: float

