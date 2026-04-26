from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from spark.models.common import WeatherNeed
from spark.models.context import IntentFieldProvenance, IntentVector
from spark.services.composite_helpers import classify_time_bucket

ACTIVITY_CONFIDENCE_CAP_BY_SOURCE = {
    "none": 0.0,
    "movement_inferred": 0.7,
    "native_health": 0.9,
    "strava": 0.95,
    "hybrid": 0.95,
}
ALLOWED_ACTIVITY_SIGNALS_BY_SOURCE = {
    "none": {"none"},
    "movement_inferred": {"none", "active_recently", "post_workout", "resting"},
    "native_health": {"none", "active_recently", "post_workout", "resting"},
    "strava": {"none", "active_recently", "post_workout", "resting"},
    "hybrid": {"none", "active_recently", "post_workout", "resting"},
}


@dataclass(frozen=True)
class IntentNormalizationResult:
    intent: IntentVector
    provenance: list[IntentFieldProvenance]


def normalize_intent_vector(
    intent: IntentVector,
    *,
    now: datetime,
    derived_weather_need: str | None,
) -> IntentNormalizationResult:
    """Apply server-side trust policy to client-provided intent fields."""
    canonical_time_bucket = classify_time_bucket(now)
    normalized = intent.model_copy(
        update={
            "time_bucket": canonical_time_bucket,
        }
    )

    provenance: list[IntentFieldProvenance] = [
        IntentFieldProvenance(
            field="time_bucket",
            policy="authoritative",
            client_value=intent.time_bucket,
            final_value=canonical_time_bucket,
            action="accepted"
            if intent.time_bucket == canonical_time_bucket
            else "overridden",
            reason="Canonical time bucket is derived server-side from request timestamp.",
            source="server_time",
        )
    ]

    if derived_weather_need:
        normalized = normalized.model_copy(
            update={
                "weather_need": WeatherNeed(derived_weather_need),
            }
        )
        provenance.append(
            IntentFieldProvenance(
                field="weather_need",
                policy="advisory",
                client_value=intent.weather_need.value,
                final_value=derived_weather_need,
                action="accepted"
                if intent.weather_need.value == derived_weather_need
                else "overridden",
                reason="Weather need is validated against server weather context before decisioning.",
                source="server_weather",
            )
        )
    else:
        provenance.append(
            IntentFieldProvenance(
                field="weather_need",
                policy="advisory",
                client_value=intent.weather_need.value,
                final_value=intent.weather_need.value,
                action="accepted",
                reason="Server weather context unavailable; client advisory value retained.",
                source="client_intent_fallback",
            )
        )

    normalized, activity_provenance = _normalize_activity_fields(normalized)
    provenance.extend(activity_provenance)

    return IntentNormalizationResult(intent=normalized, provenance=provenance)


def _normalize_activity_fields(
    intent: IntentVector,
) -> tuple[IntentVector, list[IntentFieldProvenance]]:
    activity_source = intent.activity_source
    activity_signal = intent.activity_signal
    activity_confidence = float(intent.activity_confidence)
    provenance: list[IntentFieldProvenance] = []

    if activity_source == "none":
        final_signal = "none"
        final_confidence = 0.0
    else:
        allowed_signals = ALLOWED_ACTIVITY_SIGNALS_BY_SOURCE.get(
            activity_source, {"none"}
        )
        final_signal = activity_signal if activity_signal in allowed_signals else "none"
        if activity_signal == "none":
            final_confidence = 0.0
        else:
            confidence_cap = ACTIVITY_CONFIDENCE_CAP_BY_SOURCE.get(activity_source, 0.7)
            final_confidence = max(0.0, min(activity_confidence, confidence_cap))
            if final_signal == "none":
                final_confidence = 0.0

    normalized = intent.model_copy(
        update={
            "activity_signal": final_signal,
            "activity_confidence": final_confidence,
        }
    )

    provenance.append(
        IntentFieldProvenance(
            field="activity_source",
            policy="advisory",
            client_value=activity_source,
            final_value=activity_source,
            action="accepted",
            reason="Activity source is accepted as advisory metadata for consistency and confidence trust checks.",
            source="client_intent",
        )
    )
    provenance.append(
        IntentFieldProvenance(
            field="activity_signal",
            policy="advisory",
            client_value=activity_signal,
            final_value=final_signal,
            action="accepted" if activity_signal == final_signal else "overridden",
            reason=(
                "Activity signal is reset to 'none' when source/signal consistency validation fails."
                if activity_signal != final_signal
                else "Activity signal accepted with advisory trust policy."
            ),
            source="activity_consistency_policy",
        )
    )
    provenance.append(
        IntentFieldProvenance(
            field="activity_confidence",
            policy="advisory",
            client_value=activity_confidence,
            final_value=final_confidence,
            action="accepted"
            if activity_confidence == final_confidence
            else "overridden",
            reason=(
                "Activity confidence is clamped by source-specific trust caps and signal/source consistency rules."
                if activity_confidence != final_confidence
                else "Activity confidence accepted with advisory trust policy."
            ),
            source="activity_consistency_policy",
        )
    )
    return normalized, provenance


def provenance_metadata(
    records: list[IntentFieldProvenance],
) -> dict[str, dict[str, Any]]:
    """Compact per-field provenance payload for decision/audit traces."""
    return {
        item.field: {
            "policy": item.policy,
            "client_value": item.client_value,
            "final_value": item.final_value,
            "action": item.action,
            "source": item.source,
            "reason": item.reason,
        }
        for item in records
    }
