from __future__ import annotations

from pydantic import BaseModel, Field

from spark.models.offers import LLMContent, LLMGenUI, LLMOfferOutput


class AgentDecision(BaseModel):
    skip: bool = Field(default=False, description="True if no suitable merchant found")
    reason: str | None = Field(default=None, description="Reason if skip is true")
    merchant_id: str | None = Field(default=None, description="MERCHANT_XXX")
    reasoning: str | None = Field(
        default=None, description="Brief explanation of why this merchant was selected"
    )
    content: LLMContent | None = Field(default=None, description="Generated offer content")
    genui: LLMGenUI | None = Field(
        default=None, description="Visual design configuration"
    )

    def to_llm_offer_output(self, framing_band_used: str) -> LLMOfferOutput | None:
        if not self.content or not self.genui:
            return None
        return LLMOfferOutput(
            content=self.content,
            genui=self.genui,
            framing_band_used=framing_band_used,
        )


class DensitySignalToolResult(BaseModel):
    merchant_id: str
    density_score: float
    drop_pct: float
    signal: str
    offer_eligible: bool
    historical_avg: float
    current_rate: float
    current_occupancy_pct: float | None = None
    predicted_occupancy_pct: float | None = None
    confidence: float | None = None
    name: str | None = None
    type: str | None = None
    address: str | None = None


class UserPreferenceToolResult(BaseModel):
    category: str
    weight: float


class WeatherContextToolResult(BaseModel):
    temp_celsius: float
    feels_like_celsius: float
    weather_condition: str
    weather_need: str
    vibe_signal: str


class ConflictCheckToolResult(BaseModel):
    recommendation: str
    framing_band: str | None = None
    coupon_mechanism: str | None = None
    reason: str
    allowed_vocabulary: list[str] = Field(default_factory=list)
    banned_vocabulary: list[str] = Field(default_factory=list)
