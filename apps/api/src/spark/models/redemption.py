from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


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
    error: Optional[str] = None

