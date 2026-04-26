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
    merchant_id: Optional[str] = None
    session_id: Optional[str] = None
    expires_at: Optional[str] = None
    discount_value: Optional[float] = None
    discount_type: Optional[str] = None
    error: Optional[str] = None


class RedemptionConfirmResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    session_id: Optional[str] = None
    offer_id: Optional[str] = None
    amount_eur: Optional[float] = None
    merchant_name: Optional[str] = None
    credited_at: Optional[str] = None
    wallet_balance_eur: Optional[float] = None


class OfferOutcomeResponse(BaseModel):
    success: bool
    offer_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


class WalletTransaction(BaseModel):
    offer_id: str
    amount_eur: float
    merchant_name: str
    credited_at: str


class WalletResponse(BaseModel):
    session_id: str
    balance_eur: float
    transactions: list[WalletTransaction]

