# 17 — Build Plan: What to Build, In What Order, Who Owns What

## What We Still Haven't Done (Despite 16 Docs)

We've documented everything except the three things that actually unlock parallel development:

1. **Shared JSON contracts** — the exact schema that flows between mobile → backend → Claude → mobile → merchant. Without these, four devs build toward different assumptions and spend hour 18 doing integration surgery.
2. **The complete Claude prompt** — doc 04 has a sketch, but the hard-rails injection, framing vocabulary constraints, and structured output format aren't finished.
3. **The Context Slider** — described as the single most impressive demo moment in the submission README, but nobody has designed or built it.

Those three things are the first work. Everything else is parallelizable after them.

---

## The Demo Loop: The Only Thing That Matters

Every build decision filters through one question: **does this help close the demo loop?**

```
[Phone]                    [Backend]              [Claude API]        [Merchant Dashboard]
  │                            │                       │                      │
  │── intent_vector ──────────►│                       │                      │
  │                            │── composite_state ───►│                      │
  │                            │◄── offer_response ────│                      │
  │◄── offer object ───────────│                       │                      │
  │                            │                       │                      │
  │  [user taps Accept]        │                       │                      │
  │── QR generation ──────────►│                       │                      │
  │◄── QR token ───────────────│                       │                      │
  │                            │                       │                      │
  [show QR at counter]         │── validation ────────────────────────────────►│
                               │◄── confirm ──────────────────────────────────│
  │◄── cashback credit ────────│                       │                      │
  [Spark animation]
```

This loop, working end-to-end, is the submission. Everything else is enhancement.

---

## Step 0: Shared Contracts (30 minutes, all 4 devs agree before splitting)

Create `shared/contracts.ts` in the repo root. Every team member reads it and agrees. No deviating from these schemas without updating this file.

```typescript
// shared/contracts.ts — Single source of truth for all inter-component data

// ─── Mobile → Backend ───────────────────────────────────────────────────────

export interface IntentVector {
  grid_cell: string;           // "STR-MITTE-047" (50m quantization)
  movement_mode: "browsing" | "commuting" | "stationary" | "transit_waiting" 
                 | "exercising" | "post_workout" | "cycling";
  time_bucket: string;         // "tuesday_lunch" | "friday_evening" etc.
  weather_need: "warmth_seeking" | "refreshment_seeking" | "shelter_seeking" | "neutral";
  social_preference: "social" | "quiet" | "neutral";
  price_tier: "low" | "mid" | "high";
  recent_categories: string[]; // ["cafe", "bakery"] — last 3 accepted categories
  dwell_signal: boolean;       // true = user stopped near a POI >45s
  battery_low: boolean;        // true = battery < 20%
  session_id: string;          // anon UUID, no linkage to user identity
}

// ─── Backend → Claude API ────────────────────────────────────────────────────

export interface CompositeContextState {
  timestamp: string;           // ISO 8601
  session_id: string;
  
  user: {
    intent: IntentVector;
    preference_scores: Record<string, number>; // {"cafe": 0.82, "bar": 0.3}
    social_preference: "social" | "quiet" | "neutral";
    price_tier: string;
  };
  
  merchant: {
    id: string;
    name: string;              // From DB — never from LLM
    category: string;
    distance_m: number;
    address: string;
    
    demand: {
      density_score: number;   // 0–1, current/historical
      drop_pct: number;        // 0–1
      signal: "FLASH" | "PRIORITY" | "QUIET" | "NORMAL";
      offer_eligible: boolean;
      current_occupancy_pct?: number;  // bars/clubs only
      predicted_occupancy_pct?: number;
    };
    
    active_coupon: {
      type: "FLASH" | "MILESTONE" | "TIME_BOUND" | "DRINK" | "VISIBILITY_ONLY" | null;
      max_discount_pct: number;  // Hard cap — enforced post-LLM
      valid_window_min: number;  // Offer expiry window
      config?: Record<string, unknown>;
    };
    
    inventory_signal?: string;   // "Fresh croissants (11:30)" — merchant-submitted
    tone_preference?: string;    // Merchant-set: "cozy" | "energetic" | "professional"
  };
  
  environment: {
    weather_condition: string;
    temp_celsius: number;
    feels_like_celsius: number;
    weather_need: string;
    vibe_signal: string;
  };
  
  conflict_resolution: {
    recommendation: "RECOMMEND" | "RECOMMEND_WITH_FRAMING" | "DO_NOT_RECOMMEND";
    framing_band: string | null;
    allowed_vocabulary: string[];    // Pre-filtered list, ready for system prompt injection
    banned_vocabulary: string[];     // LLM must not use these given occupancy level
  };
}

// ─── Claude API → Backend (raw LLM output, before hard rails) ────────────────

export interface LLMOfferOutput {
  content: {
    headline: string;        // ≤6 words
    subtext: string;         // ≤12 words
    cta_text: string;        // ≤4 words
    emotional_hook?: string; // Optional 1-sentence framing
  };
  genui: {
    color_palette: "warm_amber" | "cool_blue" | "deep_green" | "electric_purple" 
                   | "soft_cream" | "dark_contrast" | "sunset_orange";
    typography_weight: "light" | "regular" | "medium" | "bold";
    background_style: "gradient" | "solid" | "texture" | "bokeh" | "frosted";
    imagery_prompt: string;     // ≤20 words, specific visual scene
    urgency_style: "gentle_pulse" | "sharp_countdown" | "soft_fade" | "none";
    card_mood: "cozy" | "energetic" | "refreshing" | "celebratory" | "calm";
  };
  framing_band_used: string;   // Which vocabulary band LLM chose from
}

// ─── Final Offer Object (post hard-rails, sent to mobile) ────────────────────

export interface OfferObject {
  offer_id: string;
  session_id: string;
  
  merchant: {
    id: string;
    name: string;         // From DB
    distance_m: number;
    address: string;
    category: string;
  };
  
  discount: {
    value: number;        // Capped from merchant_rules.max_discount_pct
    type: "percentage" | "cover_refund" | "drink" | "none";
    source: "merchant_rules_db";  // Audit marker
  };
  
  content: LLMOfferOutput["content"];  // From LLM
  genui: LLMOfferOutput["genui"];      // From LLM
  
  expires_at: string;    // Computed server-side: timestamp + valid_window_min
  qr_payload?: string;   // Populated after user accepts: spark://redeem/{offer_id}/{token}/{expiry_unix}
  
  _audit: {
    rails_applied: boolean;
    discount_original_llm: number;
    discount_capped_to: number;
    composite_state_hash: string;
  };
}

// ─── QR Redemption ────────────────────────────────────────────────────────────

export interface QRPayload {
  offer_id: string;
  token_hash: string;    // HMAC of offer_id + session_id + expiry_unix with server secret
  expiry_unix: number;
}
// QR encodes: `spark://redeem/${offer_id}/${token_hash}/${expiry_unix}`

export interface RedemptionValidationRequest {
  qr_payload: string;
  merchant_id: string;  // From merchant dashboard auth context
}

export interface RedemptionValidationResponse {
  valid: boolean;
  offer_id?: string;
  discount_value?: number;
  discount_type?: string;
  error?: "EXPIRED" | "ALREADY_REDEEMED" | "INVALID_TOKEN" | "WRONG_MERCHANT";
}

// ─── Cashback Credit ─────────────────────────────────────────────────────────

export interface CashbackCredit {
  session_id: string;
  offer_id: string;
  amount_eur: number;
  merchant_name: string;
  credited_at: string;
  wallet_balance_eur: number;  // New running total
}
```

**Python equivalent** for the backend (`shared/contracts.py` — use dataclasses or Pydantic):
```python
from pydantic import BaseModel
from typing import Optional, Literal

class IntentVector(BaseModel):
    grid_cell: str
    movement_mode: Literal["browsing","commuting","stationary","transit_waiting",
                            "exercising","post_workout","cycling"]
    time_bucket: str
    weather_need: Literal["warmth_seeking","refreshment_seeking","shelter_seeking","neutral"]
    social_preference: Literal["social","quiet","neutral"]
    price_tier: Literal["low","mid","high"]
    recent_categories: list[str]
    dwell_signal: bool
    battery_low: bool
    session_id: str

# ... etc. Pydantic models for all interfaces above.
# FastAPI uses these as request/response types — auto-docs, type safety.
```

**These contracts are frozen from day 1.** If someone needs to change a field mid-hackathon, call it out explicitly — every team member is building against this.

---

## The Complete Claude Prompt (What Was Missing from Doc 04)

Doc 04 has a partial system prompt. Here's the complete version with hard-rails injection, framing vocabulary constraints, and exact output format — ready to paste into code.

### System Prompt

```python
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
```

### User Prompt Builder

```python
def build_user_prompt(state: CompositeContextState) -> str:
    cr = state.conflict_resolution
    demand = state.merchant.demand
    
    return f"""
CONTEXT STATE — {state.timestamp}

ENVIRONMENT:
- Weather: {state.environment.temp_celsius}°C ({state.environment.weather_condition}), feels like {state.environment.feels_like_celsius}°C
- User need: {state.environment.weather_need}
- Vibe signal: {state.environment.vibe_signal}

USER:
- Movement: {state.user.intent.movement_mode}
- Social preference: {state.user.social_preference}
- Price tier: {state.user.price_tier}
- Top category preferences: {state.user.preference_scores}
- Recent accepts: {state.user.intent.recent_categories}

MERCHANT: [MERCHANT_NAME]
- Category: {state.merchant.category}
- Distance: {state.merchant.distance_m}m (~{state.merchant.distance_m // 80} min walk)
- Demand signal: {demand.signal} ({int(demand.drop_pct * 100)}% below typical volume)
{f'- Current occupancy: ~{int(demand.current_occupancy_pct * 100)}%' if demand.current_occupancy_pct else ''}
{f'- Predicted occupancy at arrival: ~{int(demand.predicted_occupancy_pct * 100)}%' if demand.predicted_occupancy_pct else ''}
- Offer type: {state.merchant.active_coupon.type}
- Discount cap: [DISCOUNT]% (do not exceed, do not guess)
- Offer window: [EXPIRY_MIN] minutes
{f'- Inventory: {state.merchant.inventory_signal}' if state.merchant.inventory_signal else ''}
{f'- Merchant tone: {state.merchant.tone_preference}' if state.merchant.tone_preference else ''}

FRAMING INSTRUCTION: {cr.recommendation} ({cr.framing_band})
ALLOWED vocabulary for atmosphere: {', '.join(cr.allowed_vocabulary)}
BANNED vocabulary (occupancy too low): {', '.join(cr.banned_vocabulary)}

Generate the offer JSON now. German language unless user locale is otherwise. Informal Du-form.
"""
```

**That `build_user_prompt()` function is the most important function in the backend.** Get this right and the AI output is consistently good. Get it wrong and you're fighting the model all night.

---

## Data Engineering Layer: Build Sequence

**Owner: Finn**. This is the foundation. Nothing else can run without it.

### Hour 0–1: Database Setup

```bash
# backend/db/init_db.py — run once
python init_db.py
# Creates:
#   payone_sim.db    (transaction history + density calculations)
#   offers.db        (offer audit log, active offers, wallet balances)
#   merchants.db     (merchant profiles, coupon configs, calibration)
#   sessions.db      (anonymous session state, KG edges — if building KG)
```

**What Finn writes first:**
1. `backend/db/schema.sql` — all table definitions in one file (paste from docs 13, 15)
2. `backend/db/seed.py` — seeder that runs `generate_payone_history()` for all 5 merchants
3. Verify: `sqlite3 payone_sim.db "SELECT COUNT(*) FROM payone_transactions"` → should return 3360 (5 merchants × 28 days × 24 hours)

### Hour 1–3: Core Density Endpoints

```
GET  /api/payone/density/{merchant_id}       → CompositeContextState.merchant.demand
GET  /api/payone/merchants                   → list of all merchants with current density
POST /api/conflict/resolve                   → ConflictResolution
```

These three endpoints are what the composite context builder consumes. Test them with curl before moving on.

**Finn's testing script** (run this to verify everything is sane):
```bash
# Should return density_score < 0.5 for any merchant on a slow hour
curl http://localhost:8000/api/payone/density/MERCHANT_001

# Should return RECOMMEND_WITH_FRAMING for social user at bar at 21:00
curl -X POST http://localhost:8000/api/conflict/resolve \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"MERCHANT_003","user_social_pref":"social","current_txn_rate":2.8,"current_dt":"2025-06-14T21:14:00","active_coupon":{"type":"MILESTONE","threshold":50,"current_guests":16}}'
```

### Hour 3–5: Composite Context Builder + Offer Pipeline

```
POST /api/context/composite    → CompositeContextState (assembles all signals)
POST /api/offers/generate      → OfferObject (calls Claude, enforces hard rails, logs to audit)
```

`/api/context/composite` is the assembler. It calls:
- Weather API (OpenWeatherMap)
- Payone density endpoint (local)
- Conflict resolver (local)
- KG preference query (if KG is built) OR flat preference defaults

`/api/offers/generate` is:
1. Build `CompositeContextState`
2. Build `build_user_prompt(state)`
3. Call Claude API with `SYSTEM_PROMPT` + user prompt
4. Parse JSON response → `LLMOfferOutput`
5. `enforce_hard_rails(llm_output, merchant_rules, state)` → `OfferObject`
6. `log_offer(offer)` → audit log
7. Return `OfferObject` to mobile

### Hour 5–7: Redemption Pipeline

```
POST /api/redemption/validate  → RedemptionValidationResponse (merchant scans QR)
POST /api/redemption/confirm   → CashbackCredit (merchant confirms payment)
GET  /api/wallet/{session_id}  → balance + transaction history
```

After these endpoints exist, the full demo loop is functional. Everything after this is UI.

---

## Frontend Phasing

### Phase 1 (User Side): The Offer Moment

**Goal: The phone shows an offer and accepts it into a QR. Everything else is scaffolding.**

**Component build order:**

1. **`ContextSender`** (background service, no UI)
   - Reads GPS → quantizes to grid_cell
   - Reads IMU → classifies movement_mode (start with mock: `"browsing"`)
   - Polls every 60s → `POST /api/context/composite` → stores result in state
   - If `offer_eligible: true` → trigger `OfferCard` display

2. **`OfferCard`** (the hero component)
   ```tsx
   // Props: OfferObject
   // Renders:
   // - Dynamic background color from genui.color_palette
   // - Imagery (generated, or placeholder during dev — same URL every time)
   // - Headline, subtext from content.*
   // - Distance badge, expiry timer
   // - Accept button → triggers QR flow
   // - Dismiss button → cooldown logic
   
   // Build order within this component:
   // 1. Static layout with hardcoded styles
   // 2. Wire genui.color_palette to Tailwind/StyleSheet
   // 3. Add countdown timer
   // 4. Add accept/dismiss handlers
   // 5. Add GenUI typography variation
   // 6. Add imagery (last — can use placeholder)
   ```

3. **`QRScreen`**
   - Renders `react-native-qrcode-svg` with `offer.qr_payload`
   - Shows merchant name, address, discount value, expiry countdown
   - Works offline after accept (QR is local — validation is server-side on scan)

4. **`SparkAnimation`** (Lottie or CSS animation)
   - Plays when cashback confirmed
   - Lightning bolt from top → wallet balance number
   - Balance counter ticks up
   - This is 2 hours of pure animation work — delegate to whoever is most comfortable with Lottie

5. **`WalletScreen`** + **`PrivacyLedger`**
   - Simple list views
   - WalletScreen: `GET /api/wallet/{session_id}` → render transactions
   - PrivacyLedger: static for demo, shows intent vector contents

6. **`ContextSlider`** (demo-only panel — not a real user feature)
   ```tsx
   // A bottom sheet or slide-out panel (only visible in demo mode)
   // Sliders:
   //   Temperature: 0°C → 35°C → changes weather_need
   //   Time of day: 08:00 → 23:00 → changes time_bucket
   //   Merchant occupancy: 0% → 100% → affects framing_band
   //   User social pref: quiet ←→ social
   // Each change triggers a new /api/offers/generate call
   // The card re-renders with new GenUI in real time
   // THIS IS THE DEMO MOMENT — this needs to be beautiful and fast
   
   // Implementation: local state updates intent_vector mock, 
   // sends to /api/offers/generate with debounce 300ms
   ```

**Phase 1 Feature Prioritization:**

| Feature | Must Have | Nice to Have | Skip |
|---------|-----------|-------------|------|
| OfferCard rendering | ✅ | | |
| GenUI dynamic styling | ✅ | | |
| Accept → QR flow | ✅ | | |
| Spark animation | ✅ | | |
| Countdown timer | ✅ | | |
| Context Slider (demo tool) | ✅ | | |
| Privacy Ledger | | ✅ | |
| Wallet balance + history | | ✅ | |
| Onboarding / consent screen | | ✅ | |
| Social preference toggle | | ✅ | |
| Post-workout scenario | | ✅ | |
| OCR ticket scan | | | ✅ (pitch it) |
| Wallet pass seeding | | | ✅ (pitch it) |
| Spark Wave | | | ✅ (pitch it) |

---

### Phase 2 (Business Side): The Merchant Dashboard

**Goal: Show the Payone Pulse drop, the offer firing, the QR validation, the cashback.**

**Component build order:**

1. **`PayonePulse`** (the first thing judges will ask about)
   ```tsx
   // Recharts LineChart
   // Two lines: historical_avg (dashed) + current_rate (solid)
   // When current drops 30%+ below historical: area fill turns amber
   // When drops 50%+: fill turns red + pulsing border
   // When offer fires: a marker dot + timestamp label appears on the chart
   // Real-time: polling /api/payone/density/{merchant_id} every 30s
   
   // This chart is the whole pitch for DSV judges in one visual.
   // Build this FIRST. Everything else in the dashboard can be simple.
   ```

2. **`MerchantAlerts`** (active offers panel)
   - List of currently active offers for this merchant
   - Status: SENT | ACCEPTED | REDEEMED | EXPIRED
   - Show how many users are "en route" (anonymous accept count)

3. **`QRValidator`** (the redemption moment)
   - Camera button → reads QR → `POST /api/redemption/validate`
   - Green flash + discount amount on success
   - "Confirm payment received" button → triggers `POST /api/redemption/confirm` → fires cashback

4. **`RuleEngine`** (coupon setup)
   - Form to create active coupon: type picker, discount %, time window
   - Milestone coupon: set target guest count, reward value
   - For demo: pre-seed with a MILESTONE coupon for Bar Unter
   - The form exists but doesn't need full validation in 24h

5. **`Analytics`** (simple metrics)
   - Today: offers sent, accepts, redemptions, estimated revenue impact
   - This week: same
   - "€X kept in local economy" counter (total redeemed cashback)

**Phase 2 Feature Prioritization:**

| Feature | Must Have | Nice to Have | Skip |
|---------|-----------|-------------|------|
| PayonePulse chart | ✅ | | |
| "Offer fired" event marker on chart | ✅ | | |
| QR validator | ✅ | | |
| Redemption confirmation | ✅ | | |
| Active offers list | | ✅ | |
| Rule engine form | | ✅ | |
| Merchant analytics | | ✅ | |
| Inventory signal input | | | ✅ |
| Occupancy calibration settings | | | ✅ |

---

## Team Split

| Dev | Primary ownership | Parallel secondaries |
|-----|------------------|---------------------|
| **Finn** | Data engineering (docs 15 + this doc, Phase: Hours 0–7) | Redemption pipeline, offer audit log |
| **Lars** | Claude prompt + offer generation endpoint + GenUI schema | ContextSlider, integration testing |
| **Dev 3** | Mobile app — OfferCard, QR, SparkAnimation | Connect to backend |
| **Dev 4** | Merchant dashboard — PayonePulse, QRValidator | Rule engine form |

**Sync points (critical — don't skip):**
- Hour 2: Finn's density endpoint is live → Lars confirms composite context builder can call it
- Hour 6: Backend offer endpoint is live → Dev 3 confirms mobile can receive and render OfferObject
- Hour 10: QR flow works end-to-end → Dev 4 confirms merchant dashboard can validate
- Hour 16: Full demo loop dry run → everyone together, find integration bugs NOW not hour 22
- Hour 20: Demo dry run #2 → the one you'll actually present

---

## The 30-Minute First Move

Before anyone opens their IDE:

1. All 4 devs read `shared/contracts.ts` above → confirm the schemas
2. One person creates the repo structure:
   ```
   /mobile         (Expo)
   /backend        (FastAPI)
   /dashboard      (Next.js)
   /shared         (contracts.ts + contracts.py)
   /backend/db     (schema.sql, seed.py)
   ```
3. Finn: `python backend/db/seed.py` — data seeded, endpoints work
4. Lars: `POST /api/offers/generate` returns a real OfferObject — Claude is connected
5. Dev 3: `OfferCard` renders the hardcoded example OfferObject from doc 04
6. Dev 4: `PayonePulse` renders with hardcoded historical + current data

When all four of those are true simultaneously, the integration is trivially easy. You're just wiring up HTTP calls between things that already work in isolation.

---

## What to Say in the Pitch About the Architecture

> "We started by writing shared JSON contracts before a single line of code. Every engineer knew exactly what they were building toward. The data flows from Payone transaction history through a density calculation, through a conflict resolver, through Claude with hard-rail constraints, into a mobile card. Every step is deterministic, logged, and auditable. The LLM is the creative layer. The data is the intelligence layer. They don't mix."

That sentence separates you from every team that built a chatbot that generates offers.
