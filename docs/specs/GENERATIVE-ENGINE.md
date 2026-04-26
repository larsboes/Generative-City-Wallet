# Generative Offer Engine

## Overview: GenUI & Dynamic Content

Unlike template-based systems, Spark's Generative Engine designs the entire offer interface at runtime. The visual DNA of the offer card—including color palette, typography, imagery, and emotional tone—is dynamically generated to match the user's specific context.

---

## The Offer Object

Each offer is a structured JSON object containing content, financial terms, and visual GenUI parameters.

```json
{
  "offer_id": "uuid",
  "content": {
    "headline": "Warm up on us",
    "subtext": "Flat white + croissant, just 80m away",
    "emotional_hook": "It's cold out there. Café Römer is quiet and warm right now."
  },
  "discount": {
    "type": "percentage",
    "value": 15
  },
  "genui": {
    "theme": "cozy",
    "color_palette": { "primary": "#8B4513", "secondary": "#F5E6D3" },
    "typography": "serif_warm",
    "imagery_prompt": "A ceramic mug of coffee with steam rising, warm amber light",
    "animation": "gentle_fade_warm"
  }
}
```

---

## AI Architecture (Gemini Flash)

Spark utilizes **Gemini Flash** for high-speed, low-latency generation. The model is constrained by a system prompt that enforces brand voice, visual principles, and GDPR safety.

### System Prompt Constraints
- **Comprehension:** Offers must be understood in < 3 seconds.
- **Tone Matching:** Align visual theme with context (e.g., cold/rainy → warm/cozy).
- **Safety:** Use placeholders for business-critical values (e.g., `[DISCOUNT]%`) to be filled by hard rails.
- **Format:** Strict JSON output using native schema enforcement.

---

## Vibe-Shifting GenUI Scenarios

| Scenario | Visual Theme | Emotional Register |
|---|---|---|
| **Rainy + Cold** | Warm ambers, serif fonts, soft glows. | Cozy, inviting, shelter-seeking. |
| **Sunny + Quick** | Electric blues, sharp sans-serif, high contrast. | Fresh, functional, fast. |
| **Evening + Social** | Deep purples, gold accents, dramatic reveals. | Playful, celebratory, atmospheric. |

---

## Offer Lifecycle

1. **Trigger:** Composite context state identifies a relevant moment.
2. **Generation:** Gemini Flash creates content + GenUI spec.
3. **Hard Rails:** Server-side overrides enforce discount caps and merchant truth.
4. **Delivery:** Offer pushed to device; card appears over map.
5. **Redemption:** User accepts → QR token issued → Merchant scans → Spark cashback animation.
6. **Learning:** Interaction pattern (Accept/Decline/Expire) reinforces local preference weights.
