from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


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
    signal: str
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

