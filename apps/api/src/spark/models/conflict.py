from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from spark.models.common import ConflictRecommendation, SocialPreference


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
