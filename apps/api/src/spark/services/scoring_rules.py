"""
Pure domain scoring rules for offer decisions.

Every function in this module is a pure function with zero I/O.
They take domain primitives in and return scores or classifications out.
"""

from __future__ import annotations

POST_WORKOUT_RECOVERY_CATEGORIES = {
    "healthy_cafe",
    "juice_bar",
    "smoothie_bar",
    "cafe",
    "bakery",
}
POST_WORKOUT_SUPPRESSED_CATEGORIES = {"bar", "club", "nightclub"}
CYCLING_RECOVERY_CATEGORIES = {"juice_bar", "smoothie_bar", "healthy_cafe", "cafe"}
CYCLING_SUPPRESSED_CATEGORIES = {"club", "nightclub"}
TRANSIT_WAITING_FAST_CATEGORIES = {"cafe", "bakery", "juice_bar"}
TRANSIT_WAITING_SUPPRESSED_CATEGORIES = {"club", "nightclub", "restaurant"}
COMMUTING_FAST_CATEGORIES = {"cafe", "bakery", "juice_bar", "healthy_cafe"}
COMMUTING_SUPPRESSED_CATEGORIES = {"restaurant", "bar", "club", "nightclub"}


def weather_alignment(*, weather_need: str, merchant_category: str) -> float:
    warm_categories = {"cafe", "bakery"}
    cool_categories = {"smoothie_bar", "juice_bar", "healthy_cafe"}
    nightlife_categories = {"bar", "club", "nightclub"}
    if weather_need == "warmth_seeking":
        return 1.0 if merchant_category in warm_categories else 0.4
    if weather_need == "refreshment_seeking":
        return 1.0 if merchant_category in cool_categories else 0.4
    if weather_need == "shelter_seeking":
        return (
            0.9 if merchant_category in warm_categories | nightlife_categories else 0.5
        )
    return 0.5


def movement_category_adjustment(
    *, movement_mode: str, merchant_category: str
) -> tuple[float, str]:
    """
    Deterministic movement-aware weighting.

    Post-workout users should see recovery-oriented options and avoid nightlife.
    """
    if movement_mode == "post_workout":
        if merchant_category in POST_WORKOUT_RECOVERY_CATEGORIES:
            return 18.0, "Post-workout recovery category boost applied."
        if merchant_category in POST_WORKOUT_SUPPRESSED_CATEGORIES:
            return -14.0, "Post-workout nightlife suppression applied."
        return 0.0, "Post-workout neutral category."

    if movement_mode == "cycling":
        if merchant_category in CYCLING_RECOVERY_CATEGORIES:
            return 10.0, "Cycling recovery category boost applied."
        if merchant_category in CYCLING_SUPPRESSED_CATEGORIES:
            return -8.0, "Cycling nightlife suppression applied."
        return 0.0, "Cycling neutral category."

    if movement_mode == "transit_waiting":
        if merchant_category in TRANSIT_WAITING_FAST_CATEGORIES:
            return 8.0, "Transit-waiting quick-stop category boost applied."
        if merchant_category in TRANSIT_WAITING_SUPPRESSED_CATEGORIES:
            return -10.0, "Transit-waiting long-visit category suppression applied."
        return 0.0, "Transit-waiting neutral category."

    if movement_mode == "commuting":
        if merchant_category in COMMUTING_FAST_CATEGORIES:
            return 6.0, "Commuting quick-stop category boost applied."
        if merchant_category in COMMUTING_SUPPRESSED_CATEGORIES:
            return -12.0, "Commuting long-visit category suppression applied."
        return 0.0, "Commuting neutral category."

    return 0.0, "No movement-specific category adjustment."


def movement_recheck_minutes(*, movement_mode: str, default_minutes: int) -> int:
    """
    Adapt retry cadence to movement transitions.

    Post-workout windows are short-lived, so recheck sooner than default.
    """
    if movement_mode == "post_workout":
        return max(5, min(default_minutes, 12))
    if movement_mode == "cycling":
        return max(7, min(default_minutes, 15))
    if movement_mode == "transit_waiting":
        return max(3, min(default_minutes, 8))
    if movement_mode == "commuting":
        return max(4, min(default_minutes, 9))
    return default_minutes


def activity_alignment_points(
    *,
    activity_signal: str,
    activity_source: str,
    activity_confidence: float,
    merchant_category: str,
) -> float:
    confidence = max(0.0, min(1.0, activity_confidence))
    recovery_categories = {"healthy_cafe", "juice_bar", "smoothie_bar", "cafe", "bakery"}
    if activity_signal in {"active_recently", "post_workout"}:
        if merchant_category in recovery_categories:
            return round(6.0 * confidence, 3)
        if merchant_category in {"bar", "club", "nightclub"}:
            return round(-4.0 * confidence, 3)
    if activity_signal == "resting" and activity_source in {"strava", "native_health", "hybrid"}:
        if merchant_category in {"cafe", "bakery"}:
            return round(2.0 * confidence, 3)
    return 0.0


def confidence_band(confidence: float) -> str:
    bounded = max(0.0, min(1.0, confidence))
    if bounded >= 0.8:
        return "high"
    if bounded >= 0.5:
        return "medium"
    if bounded > 0.0:
        return "low"
    return "none"
