from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
