from __future__ import annotations

from spark.config import (
    GRAPH_PREF_DECAY_DEFAULT_RATE,
    GRAPH_PREF_MAX_UPDATES_PER_CATEGORY_WINDOW,
    GRAPH_PREF_UPDATE_WINDOW_SECONDS,
)
from spark.graph.repository import get_repository
from spark.models.api import WalletSeedItem, WalletSeedResponse
from spark.repositories.redemption import (
    acquire_graph_event_idempotency_key,
    count_graph_events_for_session,
    count_recent_graph_events_for_category,
    log_preference_update_event,
    record_learning_metric,
)

# Wallet seed signals should decay faster than interaction-driven preferences.
WALLET_SEED_DECAY_RATE = max(0.03, GRAPH_PREF_DECAY_DEFAULT_RATE)
WALLET_SEED_DECAY_BY_SOURCE = {
    "wallet_pass": max(WALLET_SEED_DECAY_RATE, 0.035),
    "receipt_ocr": max(WALLET_SEED_DECAY_RATE, 0.04),
    "manual_import": max(WALLET_SEED_DECAY_RATE, 0.03),
}
WALLET_SEED_SOURCE_GOVERNANCE = {
    "wallet_pass": {
        "default_confidence": 0.8,
        "max_confidence": 0.95,
        "max_artifacts": 10,
        "base_delta_multiplier": 1.0,
    },
    "receipt_ocr": {
        "default_confidence": 0.65,
        "max_confidence": 0.8,
        "max_artifacts": 8,
        "base_delta_multiplier": 0.85,
    },
    "manual_import": {
        "default_confidence": 0.7,
        "max_confidence": 0.75,
        "max_artifacts": 6,
        "base_delta_multiplier": 0.75,
    },
}
DEFAULT_SOURCE_TYPE = "manual_import"
MAX_PREF_UPDATES_PER_CATEGORY_WINDOW = GRAPH_PREF_MAX_UPDATES_PER_CATEGORY_WINDOW
PREF_UPDATE_RATE_LIMIT_WINDOW_SECONDS = GRAPH_PREF_UPDATE_WINDOW_SECONDS


def _normalize_seed(seed: WalletSeedItem) -> WalletSeedItem:
    source_type = seed.source_type.strip().lower()
    if source_type not in WALLET_SEED_SOURCE_GOVERNANCE:
        source_type = DEFAULT_SOURCE_TYPE
    governance = WALLET_SEED_SOURCE_GOVERNANCE[source_type]
    confidence = max(0.0, min(seed.source_confidence, 1.0))
    if confidence <= 0.0:
        confidence = float(governance["default_confidence"])
    confidence = min(confidence, float(governance["max_confidence"]))
    artifact_count = max(1, min(seed.artifact_count, int(governance["max_artifacts"])))
    return WalletSeedItem(
        category=seed.category,
        weight=seed.weight,
        source_type=source_type,
        source_confidence=confidence,
        artifact_count=artifact_count,
    )


def _quality_multiplier(seed: WalletSeedItem, *, history_count: int) -> float:
    confidence_component = 0.5 + (0.5 * max(0.0, min(seed.source_confidence, 1.0)))
    artifact_component = min(seed.artifact_count / 3.0, 1.0)
    # Longitudinal damping: repeated imports from same source/session should
    # still help, but with diminishing marginal impact.
    longitudinal_component = 1.0 / (1.0 + (0.2 * max(0, history_count)))
    return round(
        max(0.2, confidence_component * artifact_component * longitudinal_component), 3
    )


async def apply_wallet_seed_preferences(
    *, session_id: str, seeds: list[WalletSeedItem], db_path: str | None = None
) -> WalletSeedResponse:
    """
    Apply wallet-derived category priors to graph preferences.

    Idempotency is enforced in SQLite via graph_event_log so repeated imports
    do not duplicate reinforcement events.
    """
    repo = get_repository()
    if not repo.is_available():
        return WalletSeedResponse(session_id=session_id, applied=0, skipped=len(seeds))

    applied = 0
    skipped = 0
    duplicates = 0
    suppressed_by_guardrail = 0
    quality_total = 0.0
    normalized_sources_seen: set[str] = set()
    await repo.ensure_session(session_id)
    for seed in seeds:
        seed = _normalize_seed(seed)
        source_type = seed.source_type.strip().lower()
        normalized_sources_seen.add(source_type)
        governance = WALLET_SEED_SOURCE_GOVERNANCE.get(
            source_type,
            WALLET_SEED_SOURCE_GOVERNANCE[DEFAULT_SOURCE_TYPE],
        )
        decay_rate = WALLET_SEED_DECAY_BY_SOURCE.get(source_type, WALLET_SEED_DECAY_RATE)
        history_count = count_graph_events_for_session(
            session_id=session_id,
            event_type_prefix=f"wallet_seed:{source_type}:",
            db_path=db_path,
        )
        quality = _quality_multiplier(seed, history_count=history_count)
        source_event_id = (
            f"{session_id}:{source_type}:{seed.category}:{seed.weight:.4f}:"
            f"{seed.source_confidence:.4f}:{seed.artifact_count}"
        )
        event_applied = acquire_graph_event_idempotency_key(
            event_type=f"wallet_seed:{source_type}:{seed.category}",
            session_id=session_id,
            offer_id=None,
            source="wallet_seed",
            category=seed.category,
            source_event_id=source_event_id,
            payload={
                "weight": round(seed.weight, 4),
                "source_confidence": round(seed.source_confidence, 4),
                "artifact_count": seed.artifact_count,
            },
            db_path=db_path,
        )
        if not event_applied:
            duplicates += 1
            skipped += 1
            record_learning_metric(
                metric_name="learning_duplicate_suppression",
                metric_value=1.0,
                metric_group="idempotency",
                session_id=session_id,
                category=seed.category,
                source_type=f"wallet_seed:{source_type}",
                db_path=db_path,
            )
            log_preference_update_event(
                session_id=session_id,
                category=seed.category,
                source_type=f"wallet_seed:{source_type}",
                event_type=f"wallet_seed:{source_type}:{seed.category}",
                event_key=source_event_id,
                source_event_id=source_event_id,
                before_weight=None,
                delta=0.0,
                after_weight=None,
                outcome="duplicate",
                db_path=db_path,
            )
            continue

        recent_updates = count_recent_graph_events_for_category(
            session_id=session_id,
            category=seed.category,
            window_seconds=PREF_UPDATE_RATE_LIMIT_WINDOW_SECONDS,
            db_path=db_path,
        )
        if recent_updates >= MAX_PREF_UPDATES_PER_CATEGORY_WINDOW:
            suppressed_by_guardrail += 1
            skipped += 1
            record_learning_metric(
                metric_name="learning_guardrail_suppressed",
                metric_value=1.0,
                metric_group="rate_limit",
                session_id=session_id,
                category=seed.category,
                source_type=f"wallet_seed:{source_type}",
                db_path=db_path,
            )
            log_preference_update_event(
                session_id=session_id,
                category=seed.category,
                source_type=f"wallet_seed:{source_type}",
                event_type=f"wallet_seed:{source_type}:{seed.category}",
                event_key=source_event_id,
                source_event_id=source_event_id,
                before_weight=None,
                delta=0.0,
                after_weight=None,
                outcome="suppressed_by_guardrail",
                db_path=db_path,
            )
            continue

        # Base weight is intentionally conservative for cold-start priors.
        delta = (
            max(0.0, min(seed.weight, 1.0))
            * 0.35
            * quality
            * float(governance["base_delta_multiplier"])
        )
        before_weight = await _get_current_category_weight(
            repo=repo, session_id=session_id, category=seed.category
        )
        await repo.reinforce_category(
            session_id=session_id,
            category=seed.category,
            delta=delta,
            base_weight=0.25,
            source_type=f"wallet_seed:{source_type}",
            decay_rate=decay_rate,
            source_confidence=seed.source_confidence,
            artifact_count=seed.artifact_count,
        )
        after_weight = await _get_current_category_weight(
            repo=repo, session_id=session_id, category=seed.category
        )
        log_preference_update_event(
            session_id=session_id,
            category=seed.category,
            source_type=f"wallet_seed:{source_type}",
            event_type=f"wallet_seed:{source_type}:{seed.category}",
            event_key=source_event_id,
            source_event_id=source_event_id,
            before_weight=before_weight,
            delta=delta,
            after_weight=after_weight,
            outcome="applied",
            db_path=db_path,
        )
        record_learning_metric(
            metric_name="learning_update_applied",
            metric_value=1.0,
            metric_group="preference_update",
            session_id=session_id,
            category=seed.category,
            source_type=f"wallet_seed:{source_type}",
            db_path=db_path,
        )
        if before_weight is not None and after_weight is not None:
            record_learning_metric(
                metric_name="preference_weight_volatility",
                metric_value=abs(after_weight - before_weight),
                metric_group="drift",
                session_id=session_id,
                category=seed.category,
                source_type=f"wallet_seed:{source_type}",
                db_path=db_path,
            )
        applied += 1
        quality_total += quality

    avg_quality = round((quality_total / applied), 3) if applied > 0 else 0.0
    return WalletSeedResponse(
        session_id=session_id,
        applied=applied,
        skipped=skipped,
        duplicates=duplicates,
        suppressed_by_guardrail=suppressed_by_guardrail,
        avg_quality_multiplier=avg_quality,
        normalized_source_types=sorted(normalized_sources_seen),
        governance_confidence_caps={
            source: float(config["max_confidence"])
            for source, config in WALLET_SEED_SOURCE_GOVERNANCE.items()
        },
    )


async def _get_current_category_weight(repo, *, session_id: str, category: str) -> float | None:
    scores = await repo.get_preference_scores(session_id, limit=25)
    for score in scores:
        if score.category == category:
            return float(score.weight)
    return None
