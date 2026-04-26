"""Spark OfferAgent — Strands-based intelligent offer orchestrator."""

from typing import Optional

from spark.utils.prompts import (
    OFFER_AGENT_SYSTEM_PROMPT,
    build_offer_agent_user_prompt,
)
from spark.agents.tools import OFFER_TOOLS
from spark.config import GEMINI_MODEL, GOOGLE_AI_API_KEY
from spark.models.agents import AgentDecision
from spark.utils.logger import get_logger

logger = get_logger("spark.agent")


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
        system_prompt=OFFER_AGENT_SYSTEM_PROMPT,
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
) -> AgentDecision | None:
    """
    Run the OfferAgent and return structured offer decision.

    Returns parsed dict with merchant_id, content, genui.
    Falls back to None on any failure (caller uses deterministic pipeline).
    """
    # Build the user context prompt for the agent
    user_prompt = build_offer_agent_user_prompt(
        session_id=session_id,
        grid_cell=grid_cell,
        movement_mode=movement_mode,
        social_preference=social_preference,
        price_tier=price_tier,
        weather_need=weather_need,
        time_bucket=time_bucket,
        recent_categories=recent_categories,
        merchant_id=merchant_id,
    )

    try:
        agent = create_offer_agent()
        logger.info("offer_agent_start", extra={"session_id": session_id})

        # Native Strands SDK async invocation with Pydantic structured output
        result = await agent.invoke_async(
            user_prompt, structured_output_model=AgentDecision
        )

        # Extracted validated Pydantic model
        decision: AgentDecision = result.structured_output  # type: ignore[reportArgumentType]

        logger.info(
            "offer_agent_done",
            extra={"session_id": session_id},
        )

        # Validate minimum required fields
        if decision.skip:
            logger.info(
                "offer_agent_skip",
                extra={"reason": decision.reason or "no suitable merchant"},
            )
            return decision

        if not decision.merchant_id or not decision.content:
            logger.warning("offer_agent_incomplete_response")
            return None

        return decision

    except Exception as e:
        logger.warning("offer_agent_failed: %s", e)
        return None
