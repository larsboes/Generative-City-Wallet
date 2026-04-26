import json

from spark.models.agents import AgentDecision
from spark.models.offers import LLMContent, LLMGenUI
from spark.agents.tools import _dump_tool_payload, _dump_tool_payload_list


def test_agent_decision_adapts_to_llm_offer_output() -> None:
    decision = AgentDecision(
        merchant_id="merchant-1",
        reasoning="Good fit",
        content=LLMContent(
            headline="Hi",
            subtext="There",
            cta_text="Now",
            emotional_hook="Later",
        ),
        genui=LLMGenUI(
            color_palette="warm_amber",
            typography_weight="medium",
            background_style="gradient",
            imagery_prompt="cozy cafe",
            urgency_style="gentle_pulse",
            card_mood="cozy",
        ),
    )

    llm_output = decision.to_llm_offer_output("quiet_intentional")

    assert llm_output is not None
    assert llm_output.content.headline == "Hi"
    assert llm_output.genui.color_palette == "warm_amber"
    assert llm_output.framing_band_used == "quiet_intentional"


def test_tool_dump_helpers_emit_json() -> None:
    payload = _dump_tool_payload_list(
        [
            LLMContent(headline="A", subtext="B", cta_text="C"),
            LLMContent(headline="D", subtext="E", cta_text="F"),
        ]
    )
    parsed = json.loads(payload)
    assert parsed[0]["headline"] == "A"

    single = _dump_tool_payload(
        LLMGenUI(
            color_palette="warm_amber",
            typography_weight="medium",
            background_style="gradient",
            imagery_prompt="x",
            urgency_style="gentle_pulse",
            card_mood="cozy",
        )
    )
    assert json.loads(single)["color_palette"] == "warm_amber"
