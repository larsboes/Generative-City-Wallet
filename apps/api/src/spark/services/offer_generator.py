"""
Offer copy + GenUI JSON: Gemini (default) or Ollama (dev).
Hard rails apply after this module in the router — never trust raw discounts here.
"""

import json
import re

import httpx
from google import genai
from google.genai import types

from spark.config import (
    GEMINI_MODEL,
    GOOGLE_AI_API_KEY,
    OFFER_LLM_PROVIDER,
    OLLAMA_API_KEY,
    OLLAMA_API_STYLE,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from spark.models.context import CompositeContextState
from spark.models.offers import LLMOfferOutput

# ── System Prompt (from doc 17 — complete) ─────────────────────────────────────

SYSTEM_PROMPT = """You are Spark's Offer Generation AI. You generate a single hyper-relevant commercial offer for a user who is in a specific real-world context, at a specific merchant that needs customers right now.

Your output is JSON. It will be used to render a mobile UI card AND drive the visual design. The merchant name, discount value, and expiry time are injected server-side — you will never generate these. Use [MERCHANT_NAME], [DISCOUNT]%, and [EXPIRY_MIN] as placeholders where needed.

## Content rules
- Headline: ≤6 words. Emotional, immediate, specific to the context.
- Subtext: ≤12 words. Honest. Ties the offer to the moment.
- CTA: ≤4 words. Active verb.
- Match emotional register to context: cold/rainy → warm/comforting; sunny/hot → cold/energetic; evening event → celebratory; post-workout → earned/recovery.

## Framing rules
You will receive an allowed_vocabulary list and a banned_vocabulary list in the user prompt. You MUST:
- Only use words from allowed_vocabulary to describe the venue's atmosphere or crowding state.
- NEVER use words from banned_vocabulary.
This constraint is not optional. It prevents misleading users about occupancy.

## GenUI rules
The card's visual identity must reflect the emotional state of the offer:
- warm_amber: cold weather, cozy, comfort, hot drinks
- cool_blue: hot weather, refreshment, iced drinks, energy
- deep_green: nature, health, post-workout, organic
- electric_purple: nightlife, events, celebratory
- soft_cream: quiet, calm, premium, morning
- dark_contrast: late night, exclusive, club
- sunset_orange: energetic, end-of-day, fun

## Hard constraints
- Do NOT generate specific discount numbers. Always write [DISCOUNT]%.
- Do NOT generate the merchant's name in content fields. Use [MERCHANT_NAME].
- Do NOT generate expiry time. Use [EXPIRY_MIN].
- Do NOT claim health benefits, allergen safety, or dietary suitability.
- Do NOT use present-tense atmosphere words (buzzing, packed, lively, electric, full house) unless venue occupancy is confirmed above 60%. Use future-tense framing ("filling up") instead.

## Language
- Generate all content in German unless explicitly told otherwise.
- Use informal "du" form.
- Keep it warm and direct.

Output: valid JSON only. No markdown, no explanation. Match this schema exactly:
{
  "content": {
    "headline": "...",
    "subtext": "...",
    "cta_text": "...",
    "emotional_hook": "..."
  },
  "genui": {
    "color_palette": "...",
    "typography_weight": "...",
    "background_style": "...",
    "imagery_prompt": "...",
    "urgency_style": "...",
    "card_mood": "..."
  },
  "framing_band_used": "..."
}"""


def build_user_prompt(state: CompositeContextState) -> str:
    """Build the dynamic user prompt from composite context state."""
    cr = state.conflict_resolution
    demand = state.merchant.demand

    occ_line = ""
    if demand.current_occupancy_pct is not None:
        occ_line = f"- Current occupancy: ~{int(demand.current_occupancy_pct * 100)}%"

    pred_line = ""
    if demand.predicted_occupancy_pct is not None:
        pred_line = f"- Predicted occupancy at arrival: ~{int(demand.predicted_occupancy_pct * 100)}%"

    inv_line = ""
    if state.merchant.inventory_signal:
        inv_line = f"- Inventory: {state.merchant.inventory_signal}"

    tone_line = ""
    if state.merchant.tone_preference:
        tone_line = f"- Merchant tone: {state.merchant.tone_preference}"

    return f"""CONTEXT STATE — {state.timestamp}

ENVIRONMENT:
- Weather: {state.environment.temp_celsius}°C ({state.environment.weather_condition}), feels like {state.environment.feels_like_celsius}°C
- User need: {state.environment.weather_need}
- Vibe signal: {state.environment.vibe_signal}

USER:
- Movement: {state.user.intent.movement_mode.value}
- Social preference: {state.user.social_preference.value}
- Price tier: {state.user.price_tier.value}
- Top category preferences: {state.user.preference_scores}
- Recent accepts: {state.user.intent.recent_categories}

MERCHANT: [MERCHANT_NAME]
- Category: {state.merchant.category}
- Distance: {state.merchant.distance_m}m (~{int(state.merchant.distance_m) // 80} min walk)
- Demand signal: {demand.signal} ({int(demand.drop_pct * 100)}% below typical volume)
{occ_line}
{pred_line}
- Offer type: {state.merchant.active_coupon.type}
- Discount cap: [DISCOUNT]% (do not exceed, do not guess)
- Offer window: [EXPIRY_MIN] minutes
{inv_line}
{tone_line}

FRAMING INSTRUCTION: {cr.recommendation} ({cr.framing_band})
ALLOWED vocabulary for atmosphere: {", ".join(cr.allowed_vocabulary) if cr.allowed_vocabulary else "any"}
BANNED vocabulary (occupancy too low): {", ".join(cr.banned_vocabulary) if cr.banned_vocabulary else "none"}

Generate the offer JSON now. German language. Informal Du-form."""


# ── Fallback offer (when no API key or API fails) ─────────────────────────────

FALLBACK_OFFER = LLMOfferOutput(
    content={  # type: ignore[reportArgumentType]
        "headline": "Wärm dich kurz auf",
        "subtext": "Flat White + Croissant — nur [DISCOUNT]% bei [MERCHANT_NAME]",
        "cta_text": "Jetzt sichern",
        "emotional_hook": "Draußen ist es kalt. Hier wartet dein Moment.",
    },
    genui={  # type: ignore[reportArgumentType]
        "color_palette": "warm_amber",
        "typography_weight": "medium",
        "background_style": "gradient",
        "imagery_prompt": "warm ceramic coffee mug with steam, cozy amber lighting, shallow depth of field",
        "urgency_style": "gentle_pulse",
        "card_mood": "cozy",
    },
    framing_band_used="quiet_intentional",
)


def _parse_llm_json_blob(text: str) -> dict:
    """Best-effort JSON object from model output (handles stray whitespace / fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


async def _generate_ollama(state: CompositeContextState) -> LLMOfferOutput:
    """Ollama /api/chat with JSON format hint — same schema target as Gemini."""
    user_prompt = build_user_prompt(state)
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "options": {"temperature": 0.75},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
    content = (data.get("message") or {}).get("content") or ""
    raw = _parse_llm_json_blob(content)
    return LLMOfferOutput(**raw)


async def _generate_ollama_openai_compat(
    state: CompositeContextState,
) -> LLMOfferOutput:
    """OpenAI-compatible chat/completions JSON path for local dev providers."""
    user_prompt = build_user_prompt(state)
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.75,
    }
    headers: dict[str, str] = {}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f"{OLLAMA_BASE_URL}/v1/chat/completions", json=payload, headers=headers
        )
        r.raise_for_status()
        data = r.json()
    choices = data.get("choices") or []
    content = ""
    if choices:
        content = ((choices[0] or {}).get("message") or {}).get("content") or ""
    raw = _parse_llm_json_blob(content)
    return LLMOfferOutput(**raw)


async def generate_offer_llm(state: CompositeContextState) -> LLMOfferOutput:
    """
    Raw LLM offer JSON before hard-rails enforcement.
    OFFER_LLM_PROVIDER: gemini (default) | ollama (local dev).
    """
    if OFFER_LLM_PROVIDER == "ollama":
        try:
            if OLLAMA_API_STYLE == "openai":
                return await _generate_ollama_openai_compat(state)
            return await _generate_ollama(state)
        except Exception as e:
            print(f"⚠️  Ollama error, using fallback: {e}")
            return _generate_smart_fallback(state)

    if not GOOGLE_AI_API_KEY:
        return _generate_smart_fallback(state)

    try:
        client = genai.Client(api_key=GOOGLE_AI_API_KEY)

        prompt = build_user_prompt(state)
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.75,
                max_output_tokens=512,
            ),
        )
        raw = json.loads(response.text)  # type: ignore[reportArgumentType]
        return LLMOfferOutput(**raw)

    except Exception as e:
        print(f"⚠️  Gemini API error, using fallback: {e}")
        return _generate_smart_fallback(state)


def _generate_smart_fallback(state: CompositeContextState) -> LLMOfferOutput:
    """Context-aware fallback when Gemini API is unavailable."""
    weather_need = state.environment.weather_need
    category = state.merchant.category
    social = state.user.social_preference.value

    # Pick palette + mood based on context
    if weather_need == "warmth_seeking":
        palette, mood = "warm_amber", "cozy"
        headline = "Wärm dich kurz auf"
        subtext = "Dein warmer Moment wartet — nur [DISCOUNT]% bei [MERCHANT_NAME]"
        imagery = "warm ceramic coffee mug with steam, cozy amber lighting, shallow depth of field"
    elif weather_need == "refreshment_seeking":
        palette, mood = "cool_blue", "refreshing"
        headline = "Eiskalt. Ganz nah."
        subtext = "Erfrischung wartet — [DISCOUNT]% bei [MERCHANT_NAME]"
        imagery = "iced drink from above, condensation drops, bright natural light, clean white surface"
    elif social == "social":
        palette, mood = "electric_purple", "celebratory"
        headline = "Der Abend startet hier"
        subtext = "Komm vorbei — [DISCOUNT]% bei [MERCHANT_NAME]"
        imagery = (
            "warm bar interior, ambient lighting, people chatting, cocktail glasses"
        )
    else:
        palette, mood = "soft_cream", "calm"
        headline = "Dein ruhiger Moment"
        subtext = "Entspann dich — [DISCOUNT]% bei [MERCHANT_NAME]"
        imagery = "quiet cafe corner, natural light, open book, warm drink"

    if category == "bakery":
        headline = "Frisch aus dem Ofen"
        subtext = "Noch warm — [DISCOUNT]% bei [MERCHANT_NAME]"
        imagery = "fresh croissants on a wooden board, golden crust, bakery warmth, morning light"

    return LLMOfferOutput(
        content={  # type: ignore[reportArgumentType]
            "headline": headline,
            "subtext": subtext,
            "cta_text": "Jetzt sichern",
            "emotional_hook": "Genau der richtige Moment.",
        },
        genui={  # type: ignore[reportArgumentType]
            "color_palette": palette,
            "typography_weight": "medium",
            "background_style": "gradient",
            "imagery_prompt": imagery,
            "urgency_style": "gentle_pulse",
            "card_mood": mood,
        },
        framing_band_used=state.conflict_resolution.framing_band or "quiet_intentional",
    )
