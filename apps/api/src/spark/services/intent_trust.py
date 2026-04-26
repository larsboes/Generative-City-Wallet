from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from spark.models.common import WeatherNeed
from spark.models.context import IntentFieldProvenance, IntentVector
from spark.services.composite_helpers import classify_time_bucket


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

    return IntentNormalizationResult(intent=normalized, provenance=provenance)


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
