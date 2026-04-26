from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DecisionTraceStep:
    code: str
    reason: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MerchantDecision:
    merchant_id: str
    score: float
    conflict_recommendation: str
    conflict_framing_band: str | None
    trace: list[DecisionTraceStep]


@dataclass(frozen=True)
class OfferDecisionResult:
    recommendation: str
    selected_merchant_id: str | None
    selected_merchant_score: float
    recheck_in_minutes: int | None
    trace: list[DecisionTraceStep]
    candidate_scores: list[dict[str, Any]]
    conflict_framing_band: str | None

