from __future__ import annotations

from enum import Enum


class MovementMode(str, Enum):
    BROWSING = "browsing"
    COMMUTING = "commuting"
    STATIONARY = "stationary"
    TRANSIT_WAITING = "transit_waiting"
    EXERCISING = "exercising"
    POST_WORKOUT = "post_workout"
    CYCLING = "cycling"


class WeatherNeed(str, Enum):
    WARMTH_SEEKING = "warmth_seeking"
    REFRESHMENT_SEEKING = "refreshment_seeking"
    SHELTER_SEEKING = "shelter_seeking"
    NEUTRAL = "neutral"


class SocialPreference(str, Enum):
    SOCIAL = "social"
    QUIET = "quiet"
    NEUTRAL = "neutral"


class PriceTier(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


class DensitySignalType(str, Enum):
    FLASH = "FLASH"
    PRIORITY = "PRIORITY"
    QUIET = "QUIET"
    NORMAL = "NORMAL"
    NORMALLY_CLOSED = "NORMALLY_CLOSED"


class CouponType(str, Enum):
    FLASH = "FLASH"
    MILESTONE = "MILESTONE"
    TIME_BOUND = "TIME_BOUND"
    DRINK = "DRINK"
    VISIBILITY_ONLY = "VISIBILITY_ONLY"


class ConflictRecommendation(str, Enum):
    RECOMMEND = "RECOMMEND"
    RECOMMEND_WITH_FRAMING = "RECOMMEND_WITH_FRAMING"
    DO_NOT_RECOMMEND = "DO_NOT_RECOMMEND"
