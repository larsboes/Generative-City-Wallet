from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateWaveRequest(BaseModel):
    offer_id: str
    merchant_id: str
    created_by_session: str
    milestone_target: int = Field(default=3, ge=2, le=20)
    ttl_minutes: int = Field(default=90, ge=5, le=720)


class JoinWaveRequest(BaseModel):
    session_id: str


class WaveResponse(BaseModel):
    wave_id: str
    offer_id: str
    merchant_id: str
    participant_count: int
    milestone_target: int
    status: str
    expires_at: datetime
    catalyst_bonus_pct: float = Field(ge=0.0, le=1.0)


class JoinWaveResponse(WaveResponse):
    join_applied: bool
