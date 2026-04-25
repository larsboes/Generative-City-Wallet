# 04 — Generative Offer Engine & ML Intent Model

## What "Generative" Actually Means Here

The brief says "Generative UI (GenUI) techniques." Most teams will interpret this as "LLM generates the offer text." That's correct but insufficient.

**GenUI means the interface element itself is generated** — not selected from a template library. The visual DNA of the offer card (color palette, imagery description, typography weight, urgency indicator style, CTA framing, emotional tone) is an output of the generation process, not a pre-designed template that gets text swapped in.

Think of it as: the LLM doesn't fill a form — it designs the form and fills it.

---

## The Offer Object Schema

Every generated offer is a structured object with both content AND visual parameters:

```json
{
  "offer_id": "uuid",
  "merchant_id": "cafe-roemer-stgt-001",
  "generated_at": "2025-04-25T12:47:00Z",
  "expires_at": "2025-04-25T13:07:00Z",
  
  "content": {
    "headline": "Warm up on us",
    "subtext": "Flat white + croissant, just 80m away",
    "offer_detail": "15% off your order",
    "cta": "Grab it now",
    "urgency_text": "12 minutes left",
    "emotional_hook": "It's cold out there. Café Römer is quiet and warm right now."
  },
  
  "discount": {
    "type": "percentage",
    "value": 15,
    "max_eur": 5.00,
    "applies_to": "any_item"
  },
  
  "genui": {
    "card_theme": "cozy",
    "color_palette": {
      "primary": "#8B4513",
      "secondary": "#F5E6D3",
      "accent": "#FF8C42",
      "text": "#2C1810"
    },
    "typography_weight": "serif_warm",
    "background_style": "frosted_warm_amber",
    "imagery_prompt": "A ceramic mug of coffee with steam rising, warm amber light, shallow depth of field, bokeh cafe background",
    "urgency_style": "radial_timer",
    "animation_type": "gentle_fade_warm",
    "card_size": "full_card"
  },
  
  "metadata": {
    "context_triggers": ["weather:overcast_cold", "demand:unusually_quiet", "mobility:browsing"],
    "distance_m": 80,
    "merchant_category": "cafe",
    "preference_match_score": 0.87
  }
}
```

---

## LLM Prompt Architecture

### System Prompt (constant, defines Spark's brand voice)

```
You are Spark's Offer Generation AI. Your job is to create a single, 
hyper-relevant offer for a user who is in a specific real-world context. 

Rules:
- The offer must be understood in 3 seconds. No walls of text.
- The headline must be ≤ 6 words. The subtext ≤ 12 words.
- The CTA must be ≤ 4 words and action-oriented.
- Match the emotional tone to the context: cold/rainy = warm/cozy; 
  sunny/energetic = fresh/quick; evening event = celebratory.
- Generate GenUI parameters that make the card FEEL like the context.
  A cozy card has warm colors, serif fonts, soft animations.
  An energetic card has high contrast, sans-serif, sharp edges.
- Include GDPR-safe language only: no user names, no location names 
  beyond the merchant's public name.
- Output valid JSON matching the offer schema exactly.
```

### User Prompt (dynamic, built from composite context state)

```
Context State:
- Weather: 11°C, overcast, feels like 8°C. User likely wants warmth.
- Merchant: Café Römer, 80m away, category: cafe.
  Transaction density: 3 txn/hr vs. historical avg of 12 txn/hr on Tuesday lunch.
  Status: unusually quiet (75% below average).
  Merchant rules: max 20% discount, cozy tone preferred, offers valid 20 min max.
  Inventory signal: fresh batch of croissants (merchant-submitted at 11:30).
- User state: browsing (slow walking), Tuesday lunch window, social preference: quiet.
- User preferences: warm drinks (high confidence), mid-price tier, no known restrictions.
  Has accepted 2 coffee offers in past 5 days.

Generate: one compelling offer for this user at Café Römer.
Output: complete offer JSON matching schema.
```

### Why Gemini Flash specifically:
- `response_mime_type: "application/json"` enforces valid JSON output natively — no markdown stripping, no parse errors
- Fast: Flash models are optimized for low latency, which matters when the offer card needs to appear in under 2 seconds
- Cheap: ideal for a hackathon with high demo call volume during the presentation
- Same Google ecosystem as Gemma on-device — one API key, one platform, consistent tooling
- `system_instruction` is a first-class parameter — cleaner constraint enforcement than concatenation
- **Model string:** confirm in Google AI Studio. Expected: `"gemini-2.5-flash-preview-05-20"` or `"gemini-2.0-flash-lite"`. Lars has this.
- **On-device counterpart:** Gemma 3n (E2B/E4B) via Google AI Edge for intent extraction. See doc 13.

---

## Vibe-Shifting GenUI

The single most visually impressive feature for the demo. The card's entire visual language changes as context shifts.

### Scenario A: Rainy + Cold + Quiet Café
```
Theme: cozy
Colors: warm amber (#8B4513), cream (#F5E6D3), burnt orange (#FF8C42)
Font: serif, medium weight
Background: frosted glass, warm amber glow
Animation: gentle fade in, soft pulse on timer
Imagery: steam rising from ceramic mug, warm bokeh
Headline: "Warm up on us" (emotional)
```

### Scenario B: Sunny + Energetic + Quick-Service
```
Theme: energetic  
Colors: electric blue (#0066FF), white, neon accent (#00FF88)
Font: bold sans-serif, tight tracking
Background: clean white, sharp edges
Animation: quick slide in, sharp countdown timer
Imagery: iced drink top-down, high saturation, outdoor light
Headline: "Ice cold. 150m away." (factual-direct)
```

### Scenario C: Evening Event Nearby + Social Mood
```
Theme: celebratory
Colors: deep purple (#1A0033), gold (#FFD700), hot pink accent
Font: display/fashion weight
Background: gradient dark, subtle sparkle
Animation: dramatic reveal, star burst
Imagery: cocktails, people laughing, warm venue lights
Headline: "Your evening starts here" (emotional-social)
```

### Context Slider (Demo Feature):
A debug panel (shown in demo) that lets you drag a "Weather" slider from ☀️ to 🌧️ and watch the card morph in real time. This demonstrates GenUI viscerally in 10 seconds.

---

## ML Intent Model & Preference Learning

### What we're actually doing vs. what we say we're doing

**For the hackathon (what we build):** A Bayesian scoring system with heuristic weights that *behaves like* a trained ML model.

**For the pitch (how we frame it):** A preference learning system with online Bayesian updating, seeding a future RL optimization layer.

Both descriptions are true. The Bayesian heuristic IS the foundation for real ML later.

### The Bayesian Intent Model

For each potential offer (merchant_id, offer_type), compute:

```python
P(accept | context, user_prefs) = 
    P(accept | weather_match) 
    × P(accept | distance)
    × P(accept | category_preference)
    × P(accept | price_tier_match)
    × P(accept | time_of_day)
    × P(accept | merchant_quiet)  # Payone signal
```

Each factor is a learned weight from interaction history. Cold start = use population averages. Warm start = user's own history.

**Example:**
- User has accepted 3/4 coffee offers when it was cold → P(accept | weather=cold, category=cafe) = 0.75
- User has declined all offers > 20% discount → price sensitivity signal
- User always accepts within 5 seconds when distance < 100m → distance is high-weight

### Online Learning: How Preferences Update

```python
class PreferenceModel:
    def update_on_accept(self, offer, context):
        # Increase weights for:
        self.weights["category"][offer.merchant_category] += 0.1
        self.weights["weather_match"][context.weather_need] += 0.05
        self.weights["distance"][offer.distance_bucket] += 0.05
        
    def update_on_decline(self, offer, context):
        # Decrease weights for:
        self.weights["category"][offer.merchant_category] -= 0.05
        # But don't over-correct: minimum weight = 0.1
```

**Key insight:** A declined offer is NOT always a signal that the category is wrong. Sometimes the timing was wrong. The model should track decline reasons if possible (timeout vs. explicit dismiss vs. "already nearby").

### Collaborative Filtering Concept

Beyond individual preferences: "users with similar movement patterns in similar weather conditions tend to prefer [X]." This allows cold-start personalization for new users.

Not implemented for MVP, but mention in pitch: "As we gather interaction data, we layer in collaborative filtering — the Spotify model for local offers."

### The "Social Intent" Learning

User says: "I want to meet people" → flag `social_preference: high` for this session
User says: "I want to chill" → flag `social_preference: low`

Over time, correlate with accept/decline patterns:
- Does the user accept busy-bar offers? Update social preference weight up
- Does the user accept quiet-café offers? Update social preference weight down

This becomes part of the intent vector implicitly, without the user having to set it explicitly every time.

---

## Privacy Architecture: On-Device Inference

### The principle
*"Local preference and movement data should not reach the cloud. Only an abstract 'intent' signal is sent upstream."*

### What this means technically

**On device:**
- Full GPS history → only quantized grid cell sent
- IMU data → only movement_mode classification sent
- Preference model → only aggregate preference signals (price_tier, weather_need, etc.) sent
- Past interactions → never sent; influence intent vector locally

**What leaves the device:**
The intent vector (see `02-ARCHITECTURE.md`) — abstract, non-linkable, session-ID only.

### The Privacy Pulse (Demo Feature)

A small pulsing green dot in the corner of the app UI. When tapped:

```
⚡ Privacy Ledger — What's happening right now:

🔒 Processing on your device:
   └── GPS: Quantized to grid cell "STR-MITTE-047"
   └── Movement: Classified as "browsing" 
   └── Preferences: 3 signals derived locally

📤 Sent to Spark servers:
   └── {grid_cell: "STR-MITTE-047", movement: "browsing", 
         weather_need: "warmth_seeking", time: "tuesday_lunch"}

❌ Never sent:
   └── Your exact location
   └── Your name or account details  
   └── Your past interactions
   └── Raw sensor data
```

This is the single most powerful GDPR moment in the demo. German savings bank judges will respond to this.

---

## Offer Lifecycle

```
GENERATED → DELIVERED → [ACCEPTED | DECLINED | EXPIRED]
                              │
                         ACCEPTED
                              │
                         QR TOKEN ISSUED (valid 15 min)
                              │
                         MERCHANT VALIDATES
                              │
                         CASHBACK CREDITED
                              │
                         "SPARK" ANIMATION
                              │
                         ANALYTICS UPDATED
```

**Offer timing:**
- Offer valid window: set by merchant rule (default 20 min)
- QR token valid: 15 min after acceptance (urgency maintained)
- Auto-expire: card disappears with fade animation (intentional, not broken)
- Dismiss: swipe down → card disappears, offer cancelled, mild haptic feedback

**After decline:**
- Soft dismiss: "Got it. We'll find you a better moment." → no negative UX
- Cooldown: don't re-offer the same merchant for 2 hours
- Learn: update preference model

---

## The "Magic Receipt" Cashback

The transaction close moment is emotionally critical.

After merchant validates QR:
1. User's phone gets a push: "Payment confirmed ✓"
2. A Spark (lightning bolt / sparkle) animation flies from notification area into a wallet balance indicator
3. Text appears: "+€0.68 Local Reward credited"
4. Sub-text: "Saved at Café Römer · Today, 12:51"

Why this matters:
- It closes the loop emotionally (the offer had a satisfying ending)
- It reinforces the Sparkasse branding (Spark = Sparkasse = trustworthy)
- It makes the cashback feel real even in a simulated checkout
- It's the "satisfying clink" that makes people tell others about the product
