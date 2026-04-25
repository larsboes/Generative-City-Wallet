"""
GraphValidationService — deterministic, graph-driven rule gate.

Runs BEFORE the LLM is invoked. Inspired by the ATC `ValidationService`
pattern: structured `accepted` / `rejected` decisions with machine-
readable reasons that can later be exposed for explainability.

All rule thresholds are sourced from `config.GRAPH_RULES` so they can be
tuned per environment without code changes.

Severity ladder:
- INFO  — observation only, attached to the audit trail
- SOFT  — non-blocking, may bias framing/metadata downstream
- HARD  — block the offer, surface a recheck-window to the caller
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.backend.config import GRAPH_RULES
from src.backend.graph.repository import GraphRepository, get_repository


class RuleSeverity(str, Enum):
    INFO = "info"
    SOFT = "soft"
    HARD = "hard"


@dataclass(frozen=True)
class RuleViolation:
    rule_id: str
    severity: RuleSeverity
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphValidationResult:
    accepted: bool
    violations: list[RuleViolation] = field(default_factory=list)
    soft_adjustments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    recheck_in_minutes: Optional[int] = None

    @property
    def hard_violations(self) -> list[RuleViolation]:
        return [v for v in self.violations if v.severity == RuleSeverity.HARD]

    @property
    def soft_violations(self) -> list[RuleViolation]:
        return [v for v in self.violations if v.severity == RuleSeverity.SOFT]

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "severity": v.severity.value,
                    "reason": v.reason,
                    "metadata": v.metadata,
                }
                for v in self.violations
            ],
            "soft_adjustments": self.soft_adjustments,
            "metadata": self.metadata,
            "recheck_in_minutes": self.recheck_in_minutes,
        }


class GraphValidationService:
    """
    Evaluate deterministic, graph-derived constraints on a candidate offer.

    Rule order is intentional: cheapest checks first, hard violations
    short-circuit further work. Soft violations are collected but never
    block.
    """

    def __init__(
        self,
        repo: Optional[GraphRepository] = None,
        rules_config: Optional[dict[str, Any]] = None,
    ):
        self.repo = repo or get_repository()
        self.config = {**GRAPH_RULES, **(rules_config or {})}

    async def validate(
        self,
        *,
        session_id: str,
        merchant_id: str,
        merchant_category: str,
        now_unix: Optional[float] = None,
    ) -> GraphValidationResult:
        now = now_unix if now_unix is not None else time.time()
        result = GraphValidationResult(accepted=True)

        # If the graph is unavailable we cannot enforce rules — degrade to
        # "accepted with note" so the offer pipeline keeps producing offers.
        if not self.repo.is_available():
            result.violations.append(
                RuleViolation(
                    rule_id="graph_unavailable",
                    severity=RuleSeverity.INFO,
                    reason="Knowledge graph unavailable — rules skipped, fallback path used.",
                )
            )
            result.metadata["graph_available"] = False
            return result

        result.metadata["graph_available"] = True

        # Rule 1 — session-wide daily offer budget (anti-spam).
        budget = int(self.config["session_offer_budget_per_day"])
        since_24h = now - 24 * 3600
        session_count = await self.repo.session_offer_count(
            session_id=session_id, since_unix=since_24h
        )
        result.metadata["session_offers_24h"] = session_count
        if session_count >= budget:
            result.accepted = False
            result.recheck_in_minutes = 60
            result.violations.append(
                RuleViolation(
                    rule_id="session_offer_budget",
                    severity=RuleSeverity.HARD,
                    reason=(
                        f"Session received {session_count} offers in the last 24h "
                        f"(budget={budget}). Holding back to avoid fatigue."
                    ),
                    metadata={"count": session_count, "budget": budget},
                )
            )
            return result  # short-circuit — no need to inspect more

        # Rule 2 — merchant fatigue cap.
        fatigue_max = int(self.config["merchant_fatigue_max_per_day"])
        merchant_stats = await self.repo.merchant_offer_stats(
            session_id=session_id, merchant_id=merchant_id, since_unix=since_24h
        )
        result.metadata["merchant_offers_24h"] = merchant_stats.count
        if merchant_stats.count >= fatigue_max:
            result.accepted = False
            result.recheck_in_minutes = 120
            result.violations.append(
                RuleViolation(
                    rule_id="merchant_fatigue_cap",
                    severity=RuleSeverity.HARD,
                    reason=(
                        f"Merchant {merchant_id} already offered "
                        f"{merchant_stats.count}× in last 24h (cap={fatigue_max})."
                    ),
                    metadata={
                        "merchant_id": merchant_id,
                        "count": merchant_stats.count,
                        "cap": fatigue_max,
                    },
                )
            )
            return result

        # Rule 3 — same-merchant cooldown (recent unredeemed offer).
        cooldown_min = int(self.config["same_merchant_cooldown_min"])
        if merchant_stats.last_unix:
            since_last_min = (now - float(merchant_stats.last_unix)) / 60.0
            if since_last_min < cooldown_min:
                result.accepted = False
                result.recheck_in_minutes = max(1, int(cooldown_min - since_last_min))
                result.violations.append(
                    RuleViolation(
                        rule_id="same_merchant_cooldown",
                        severity=RuleSeverity.HARD,
                        reason=(
                            f"Same merchant offered "
                            f"{since_last_min:.1f} min ago — cooldown {cooldown_min} min."
                        ),
                        metadata={
                            "since_last_min": round(since_last_min, 1),
                            "cooldown_min": cooldown_min,
                        },
                    )
                )
                return result

        # Rule 4 — category diversity (soft, non-blocking).
        diversity_window = int(self.config["category_diversity_window"])
        recent = await self.repo.recent_offers(
            session_id=session_id, limit=diversity_window
        )
        if recent:
            same_category = sum(
                1
                for o in recent
                if (o.category or "").lower() == merchant_category.lower()
            )
            result.metadata["recent_same_category"] = same_category
            if same_category >= diversity_window:
                result.violations.append(
                    RuleViolation(
                        rule_id="category_diversity",
                        severity=RuleSeverity.SOFT,
                        reason=(
                            f"Last {diversity_window} offers were all "
                            f"'{merchant_category}'. Consider diversifying framing."
                        ),
                        metadata={
                            "same_category": same_category,
                            "window": diversity_window,
                        },
                    )
                )
                result.soft_adjustments.append("diversify_framing")

        # Rule 5 — fairness budget by category share in recent window.
        fairness_window = int(self.config["fairness_window"])
        fairness_min_obs = int(self.config["fairness_min_observations"])
        fairness_max_share = float(self.config["fairness_max_category_share"])
        if fairness_max_share < 1.0:
            fairness_recent = await self.repo.recent_offers(
                session_id=session_id, limit=fairness_window
            )
            total = len(fairness_recent)
            if total >= fairness_min_obs:
                same_category = sum(
                    1
                    for o in fairness_recent
                    if (o.category or "").lower() == merchant_category.lower()
                )
                share = same_category / float(total)
                result.metadata["fairness_same_category"] = same_category
                result.metadata["fairness_total_observations"] = total
                result.metadata["fairness_share"] = round(share, 3)
                if share >= fairness_max_share:
                    result.accepted = False
                    result.recheck_in_minutes = 30
                    result.violations.append(
                        RuleViolation(
                            rule_id="fairness_budget",
                            severity=RuleSeverity.HARD,
                            reason=(
                                f"Category '{merchant_category}' already consumes "
                                f"{share:.0%} of last {total} offers "
                                f"(max={fairness_max_share:.0%})."
                            ),
                            metadata={
                                "category": merchant_category,
                                "share": round(share, 3),
                                "max_share": fairness_max_share,
                                "window": fairness_window,
                                "total": total,
                            },
                        )
                    )
                    return result

        return result
