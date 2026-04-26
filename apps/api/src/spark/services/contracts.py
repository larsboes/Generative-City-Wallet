from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from spark.models.demand import DemandContext, Venue


@dataclass(frozen=True)
class VendorDashboardData:
    target_day: date
    current_hour: int
    daily: dict[str, Any]
    comparison: list[dict[str, Any]]
    demand: DemandContext
    revenue: dict[str, Any]


@dataclass(frozen=True)
class OccupancyMerchantData:
    venue: Venue
    timestamp: datetime
    demand: DemandContext


@dataclass(frozen=True)
class OccupancyQueryData:
    timestamp: datetime
    items: list[tuple[Venue, DemandContext]]


@dataclass(frozen=True)
class HistoryGenerationData:
    inserted: int
    venue_count: int
    start: datetime
    end: datetime


@dataclass(frozen=True)
class LiveUpdateGenerationData:
    inserted: int
    venue_count: int
    window_start: datetime
    window_end: datetime
