from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from spark.models.demand import DemandContext


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
