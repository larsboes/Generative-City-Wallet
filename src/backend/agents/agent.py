"""
Spark OfferAgent — Strands-based intelligent offer orchestrator.

The agent reasons about:
  • Which merchant to recommend (density × preferences × conflict)
  • How to frame the offer (context-aware GenUI + copy)
  • When NOT to offer (if no merchant fits)

What the agent CANNOT do:
  • Set discounts, prices, or expiry — DB rails enforce those
  • Override graph validation (fatigue, cooldown, budget)
  • Bypass hard rails (merchant name, banned copy patterns)
"""

import json
import logging
from typing import Optional

from src.backend.agents.tools import OFFER_TOOLS
from src.backend.config import GEMINI_MODEL, GOOGLE_AI_API_KEY

logger = logging.getLogger("spark.agent")

SYSTEM_PROMPT = """\
You are Spark's OfferAgent — an intelligent local commerce recommender for Stuttgart.

## Your role
You have tools to inspect real-time merchant density, user preferences, weather, \
and conflict resolution. Use them to:
1. Survey all merchants' density signals
2. Check the user's category preferences
3. Get the current weather context
4. Select the best merchant for this user at this moment
5. Verify the selection with conflict resolution
6. Generate the offer content and visual design

## Decision rules
- Prefer merchants with high drop_pct (FLASH > PRIORITY > QUIET)
- Align with user category preferences from the knowledge graph
- Match weather context to offer framing (cold → warm/cozy, hot → refresh)
- Respect conflict resolution — if DO_NOT_RECOMMEND, try another merchant
- If no merchant is suitable, return {"skip": true, "reason": "..."}

## Output format
Return ONLY valid JSON. No markdown, no explanation. Schema:
{
  "merchant_id": "MERCHANT_XXX",
  "reasoning": "Brief explanation of why this merchant was selected",
  "content": {
    "headline": "≤6 words, emotional, German, Du-form",
    "subtext": "≤12 words, ties offer to moment",
    "cta_text": "≤4 words, active verb",
    "emotional_hook": "Optional emotional closer"
  },
  "genui": {
    "color_palette": "warm_amber|cool_blue|deep_green|electric_purple|soft_cream|dark_contrast|sunset_orange",
    "typography_weight": "light|medium|bold",
    "background_style": "gradient|solid|blur|texture",
    "imagery_prompt": "Descriptive image prompt for card background",
    "urgency_style": "gentle_pulse|countdown|static|glow",
    "card_mood": "cozy|energetic|refreshing|celebratory|calm"
  }
}

## Hard constraints
- Use [MERCHANT_NAME] as placeholder — the real name is injected server-side
- Use [DISCOUNT]% as discount placeholder — the real value comes from the DB
- Use [EXPIRY_MIN] for expiry — computed server-side
- Generate all content in German, informal Du-form
- Do NOT claim health benefits
- Do NOT use "packed"/"buzzing"/"voll" if occupancy is below 60%
"""


def _build_model():
    """Build GeminiModel for Strands."""
    from strands.models.gemini import GeminiModel

    return GeminiModel(
        model_id=GEMINI_MODEL,
        client_args={"api_key": GOOGLE_AI_API_KEY},
        params={"temperature": 0.7},
    )


def create_offer_agent():
    """Create a Strands OfferAgent with Gemini model and service tools."""
    from strands import Agent

    model = _build_model()
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=OFFER_TOOLS,
    )


async def run_offer_agent(
    *,
    session_id: str,
    grid_cell: str,
    movement_mode: str,
    social_preference: str,
    price_tier: str,
    weather_need: str,
    time_bucket: str,
    recent_categories: list[str],
    merchant_id: Optional[str] = None,
) -> dict:
    """
    Run the OfferAgent and return structured offer decision.

    Returns parsed JSON dict with merchant_id, content, genui.
    Falls back to None on any failure (caller uses deterministic pipeline).
    """
    # Build the user context prompt for the agent
    merchant_hint = (
        f"\nThe user has specifically requested merchant {merchant_id}. "
        f"Check its density and conflict status, but still verify it's suitable."
        if merchant_id
        else "\nNo specific merchant requested — survey all options and pick the best fit."
    )

    user_prompt = f"""Generate an offer for this user context:

SESSION: {session_id}
GRID CELL: {grid_cell}
MOVEMENT: {movement_mode}
SOCIAL PREFERENCE: {social_preference}
PRICE TIER: {price_tier}
WEATHER NEED: {weather_need}
TIME BUCKET: {time_bucket}
RECENT CATEGORIES: {", ".join(recent_categories) if recent_categories else "none"}
{merchant_hint}

Use your tools to gather real-time data, then select a merchant and generate the offer."""

    try:
        agent = create_offer_agent()
        logger.info("offer_agent_start", extra={"session_id": session_id})

        # Strands Agent.__call__ is synchronous — run in thread to not block
        import asyncio
        import concurrent.futures

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, agent, user_prompt)

        response_text = str(result)
        logger.info(
            "offer_agent_done",
            extra={"session_id": session_id, "response_length": len(response_text)},
        )

        # Parse the JSON from agent response
        # Agent may wrap JSON in markdown code blocks — strip those
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[: cleaned.rfind("```")]
            cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        # Validate minimum required fields
        if parsed.get("skip"):
            logger.info(
                "offer_agent_skip",
                extra={"reason": parsed.get("reason", "no suitable merchant")},
            )
            return parsed

        if not parsed.get("merchant_id") or not parsed.get("content"):
            logger.warning("offer_agent_incomplete_response")
            return None

        return parsed

    except json.JSONDecodeError as e:
        logger.warning("offer_agent_json_error: %s", e)
        return None
    except Exception as e:
        logger.warning("offer_agent_failed: %s", e)
        return None
