"""
Strands-native tools for the Spark OfferAgent.

Each @tool function wraps an existing deterministic service, exposing it
to the agent's reasoning loop. The agent calls these tools to gather
real-time context before deciding which merchant to recommend and how
to frame the offer.

All tools return JSON strings — Strands convention for structured data.
"""

import json
from datetime import datetime

from strands import tool


@tool
def get_all_density_signals() -> str:
    """Get real-time density signals for ALL merchants in the system.

    Returns JSON array with each merchant's density_score, drop_pct, signal
    (FLASH/PRIORITY/QUIET/NORMAL), offer_eligible flag, current occupancy,
    name, type, and address. Use this to compare merchants and find the
    best candidate for an offer.
    """
    from src.backend.services.density import get_all_merchants_density

    results = get_all_merchants_density()
    return json.dumps(results, default=str, ensure_ascii=False)


@tool
def get_merchant_density(merchant_id: str) -> str:
    """Get detailed density signal for a specific merchant.

    Args:
        merchant_id: The merchant ID (e.g. MERCHANT_001).

    Returns density_score, drop_pct, signal, occupancy, and historical avg.
    """
    from src.backend.services.density import compute_density_signal

    result = compute_density_signal(merchant_id)
    return json.dumps(result, default=str, ensure_ascii=False)


@tool
async def get_user_preferences(session_id: str) -> str:
    """Get the user's category preference scores from the knowledge graph.

    Args:
        session_id: The anonymized user session ID.

    Returns JSON array of {category, weight} sorted by preference strength.
    Falls back to heuristic defaults when graph is unavailable.
    """
    from src.backend.graph.repository import get_repository

    repo = get_repository()
    scores = await repo.get_preference_scores(session_id, limit=10)

    if not scores:
        # Cold-start fallback
        return json.dumps(
            [
                {"category": "cafe", "weight": 0.82},
                {"category": "bakery", "weight": 0.60},
                {"category": "bar", "weight": 0.40},
            ]
        )

    return json.dumps(
        [{"category": s.category, "weight": round(s.weight, 3)} for s in scores]
    )


@tool
async def get_weather_context() -> str:
    """Get current Stuttgart weather conditions.

    Returns temperature, feels_like, weather_condition, weather_need
    (warmth_seeking/refreshment_seeking/shelter_seeking/neutral),
    and vibe_signal (cozy/energetic/refreshing/neutral).
    """
    from src.backend.services.weather import get_stuttgart_weather

    weather = await get_stuttgart_weather()
    return json.dumps(weather, default=str, ensure_ascii=False)


@tool
def check_conflict(
    merchant_id: str,
    user_social_pref: str,
    current_txn_rate: float,
) -> str:
    """Check if an offer for this merchant conflicts with the user's social preference.

    Args:
        merchant_id: The merchant ID.
        user_social_pref: One of 'social', 'quiet', 'neutral'.
        current_txn_rate: Current transaction rate at the merchant.

    Returns recommendation (RECOMMEND / RECOMMEND_WITH_FRAMING / DO_NOT_RECOMMEND),
    framing_band, allowed_vocabulary, and banned_vocabulary.
    """
    from src.backend.services.conflict import resolve_conflict

    result = resolve_conflict(
        merchant_id=merchant_id,
        user_social_pref=user_social_pref,
        current_txn_rate=current_txn_rate,
        current_dt=datetime.now(),
    )
    return json.dumps(
        {
            "recommendation": result.recommendation,
            "framing_band": result.framing_band,
            "coupon_mechanism": result.coupon_mechanism,
            "reason": result.reason,
            "allowed_vocabulary": result.allowed_vocabulary,
            "banned_vocabulary": result.banned_vocabulary,
        },
        ensure_ascii=False,
    )


# All tools as a list for easy import
OFFER_TOOLS = [
    get_all_density_signals,
    get_merchant_density,
    get_user_preferences,
    get_weather_context,
    check_conflict,
]
