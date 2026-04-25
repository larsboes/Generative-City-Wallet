# 16 — Advanced Context Signals: Exercise States, OCR Enrichment, Wallet Seeds, and Social Coordination

## The Unifying Insight

Every concept in this document is about the same thing: **more precise knowledge of what the user is about to do next.** The sensor signals we've built so far are reactive — they describe the user's current state. The concepts here are either predictive (where are they going, what will they need) or explicitly user-contributed (the user actively tells us something). Both dramatically improve signal quality without increasing passive surveillance. The privacy story actually gets *better* with each of these, not worse.

---

## Part 1: Exercise State — The Post-Workout Recovery Window

### New Movement Modes

The current IMU classifier has two states: `browsing` and `commuting`. That's too coarse. There's a third behavioral mode — `exercising` — that has specific characteristics worth handling explicitly:

```python
MOVEMENT_MODES = {
    "browsing":     "slow/stopped, frequent direction changes, dwell signals",
    "commuting":    "sustained directional movement, transit-speed, no stops",
    "exercising":   "elevated pace (>7 km/h GPS or high accelerometer freq), sustained",
    "post_workout": "pace decelerating from running → walking, within 10 min of exercising",
    "cycling":      "smooth oscillation pattern, 12-25 km/h GPS, no pedestrian context",
}
```

**Detection signals:**
- Accelerometer: running produces a characteristic ~2Hz vertical oscillation at high amplitude. Walking is ~1Hz at lower amplitude. This is deterministic — not an ML problem, just a threshold.
- GPS speed (when available): >7 km/h sustained for >3 min = exercising
- Step frequency via accelerometer FFT: ~160-180 steps/min = running, ~100-120 = brisk walking
- Combined: GPS + accelerometer agreement increases confidence

```python
def classify_movement_mode(accel_data, gps_speed, step_freq):
    # Exercising detection
    if gps_speed > 7 and step_freq > 140:
        return "exercising"
    
    # Post-workout: pace falling from exercise threshold
    # Check if mode was exercising in the last 8 minutes
    if recent_mode_was("exercising", within_minutes=8) and gps_speed < 5:
        return "post_workout"
    
    # Cycling
    if gps_speed > 12 and gps_speed < 28 and step_freq < 30:
        return "cycling"
    
    # Standard modes
    if gps_speed < 2 and step_freq < 50:
        return "browsing"
    return "commuting"
```

### The Critical Rule: Do NOT Interrupt Exercising Users

This is explicit and non-negotiable. Someone mid-run should receive zero offers. They're in a flow state — interrupting is annoying, and an offer they can't act on (running past a café) is pure noise that degrades the system's signal quality over time.

```python
if composite_state.movement_mode == "exercising":
    return None  # Never generate an offer. Period.
```

### The Post-Workout Window: The Real Opportunity

`post_workout` is the best possible moment to recommend hydration, food, and recovery venues. The user is:
- Warm and cooling down — cold drinks, protein, something refreshing
- Walking pace (can actually go in somewhere)
- Dopamine elevated (endorphins) — more likely to try somewhere new
- Near wherever they finished their run (might be near cafés, sports bars, health food shops)

**What changes in the composite state when `post_workout` is detected:**

```python
if movement_mode == "post_workout":
    # Boost category weights that serve recovery
    context_state["category_boost"] = {
        "smoothie_bar": 1.8,
        "sports_nutrition": 1.8,
        "healthy_cafe": 1.6,
        "regular_cafe": 1.3,
        "bakery": 1.2,
        "bar": 0.1,  # Strong suppress — nobody wants a beer immediately post-run
        "club": 0.0,
    }
    context_state["weather_need"] = "cold" if weather.temp > 18 else "warm"
    context_state["offer_framing"] = "recovery_reward"  # New framing band for LLM
```

**New framing vocabulary for post-workout:**
```python
FRAMING_VOCABULARY["recovery_reward"] = [
    "You earned this",
    "Refuel after your run",
    "Power down with us",
    "Cold and waiting for you",
    "You deserve this",
]
```

### Demo Scenario: The Stuttgart Morning Runner

> Mia just finished a 5km run along the Schlossgarten. Spark detects pace drop from 8.2 km/h to 3.1 km/h at 7:42am. Movement_mode flips to `post_workout`. Nearby: Café Feierabend (80m), "organic, smoothies, protein bowls." Payone shows 2 of 8 typical morning transactions — quiet, space available. Offer fires: "You earned this — protein bowl + juice at Café Feierabend, 80m. 15% off to refuel." 

This is a scenario no other team will have. Not "user is hungry" — "user just ran 5km and needs recovery calories RIGHT NOW." The context precision is real.

---

## Part 2: User Enrichment Pipeline — Scan, Parse, Act

### The Philosophy Shift

All our other signals are passive: we sense what the user is doing without their involvement. The enrichment pipeline inverts this: the user **actively contributes** information to improve their own experience. This is:
- More accurate (explicit > inferred)
- More GDPR-friendly (user-initiated, user-controlled)
- More engaging UX (user feels like a participant, not a subject)
- Admissible in the "I choose what to share" model

The entry point in the app: small "+" button on the idle screen. "Add context: 📷 Train ticket | 🧾 Receipt | 🎫 Event ticket" — all processed locally, only structured output leaves the device.

### 2a: Train Ticket OCR → Delay Window Detection

#### Without OCR: Probabilistic inference

Even before OCR, we can do meaningful transit inference. If the user is at Stuttgart Hauptbahnhof (inferred from 50m grid cell) and movement mode is `commuting` heading toward platform area at 17:54 on a Tuesday, the DB API shows which trains depart in the next 20 minutes. We don't know which one they're taking, but we can:
- Check ALL departing trains for delays in the next 15 minutes
- If any have a >8min delay AND user is at the station = offer window likely
- Serve a soft offer: "S1 toward Schwabstraße running 12 min late — grab something?"

This already works. It's already in the demo script. The OCR makes it precise.

#### With OCR: Exact delay window

```
User taps "+" → "Scan train ticket"
Camera opens
User photographs ticket / DB app screenshot / platform display
↓
On-device ML Kit Text Recognition (not Tesseract — ML Kit is faster, 
more accurate, works offline, integrated in React Native via Firebase)
↓
OCR output → parser
```

**Parser targets:**
```python
import re

def parse_transit_info(ocr_text: str) -> dict:
    """
    Handles: DB paper tickets, DB app screenshots, VVS display boards.
    Extracts what we need, nothing else.
    """
    result = {}
    
    # Train number: "RE 4", "ICE 598", "S1", "U15", "Bus 42"
    train_match = re.search(r'\b(ICE|IC|RE|RB|S\d+|U\d+|Bus)\s*(\d+)\b', ocr_text)
    if train_match:
        result["train_type"] = train_match.group(1)
        result["train_number"] = train_match.group(2)
    
    # Departure time: "18:02" or "18.02"
    time_match = re.search(r'\b(\d{1,2})[:\.](\d{2})\b', ocr_text)
    if time_match:
        result["departure_time"] = f"{time_match.group(1)}:{time_match.group(2)}"
    
    # Platform: "Gleis 2" or "Gleis 12" or "Gl. 5"
    platform_match = re.search(r'Gl(?:eis)?\.?\s*(\d+)', ocr_text, re.IGNORECASE)
    if platform_match:
        result["platform"] = platform_match.group(1)
    
    # Destination — look for station names after "nach" or "→" 
    dest_match = re.search(r'(?:nach|→|>)\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s[A-ZÄÖÜ][a-zäöüß]+)*)', ocr_text)
    if dest_match:
        result["destination"] = dest_match.group(1)
    
    return result
```

**Then query the DB Fahrplan API:**
```python
async def get_transit_delay(train_info: dict) -> dict:
    """Query DB Fahrplan (open API, no auth needed for basic delay info)."""
    # DB Open Data: api.deutschebahn.com/freeplan/v1
    # Alternatively: marudor.de API — excellent, community-maintained, very accurate
    
    endpoint = f"https://marudor.de/api/iris/v2/abfahrten/{station_eva}"
    response = await httpx.get(endpoint, params={"lookahead": 60})
    
    trains = response.json()["departures"]
    
    matching = [t for t in trains 
                if train_info.get("train_number") in str(t.get("train", {}))]
    
    if matching:
        train = matching[0]
        delay_minutes = train.get("delayDeparture", 0)
        scheduled_departure = train.get("scheduledDeparture")
        platform = train.get("platform")
        
        return {
            "delay_minutes": delay_minutes,
            "actual_departure": train.get("departure"),
            "platform": platform,
            "window_available": delay_minutes >= 5,  # 5min minimum to bother
            "window_minutes": delay_minutes,
        }
    
    return {"delay_minutes": 0, "window_available": False}
```

**The trigger logic:**
```python
if transit_info and delay_data["window_available"]:
    window_minutes = delay_data["delay_minutes"]
    
    # Find merchants within ~200m of current location (the station)
    nearby = get_nearby_merchants(user_location, radius_m=250)
    
    # Time filter: only recommend if user can go and come back in time
    qualifying = [m for m in nearby if m.avg_visit_minutes < window_minutes - 3]
    
    if qualifying:
        generate_offer(
            merchant=qualifying[0],
            context_override={
                "urgency_minutes": window_minutes,
                "framing": "delay_window",
                "cta_tone": "precise",  # "You have exactly 11 minutes"
            }
        )
```

**The demo moment:**
> Milan is at Stuttgart Hauptbahnhof. He photographs his ticket: "S1 → Schwabstraße, 18:02, Gleis 2." OCR parses it. marudor API confirms: S1 running 14 minutes late. Spark immediately: "Your train's running 14 minutes late. Bäckerei Wolf is 90m away — grab a pretzel. We'll ping you 4 minutes before you need to head back." 

That "ping you 4 minutes before you need to head back" is the feature that makes judges gasp. Not just the offer — the awareness that we *know the deadline*.

### 2b: Extending the Pipeline Beyond Trains

The same OCR infrastructure handles other enrichment:

| What user scans | OCR extracts | What we infer |
|-----------------|-------------|---------------|
| Event ticket | Artist/event name, venue, time | Post-event venue preference (bar near venue at 22:00) |
| Restaurant receipt | Merchant name, items, price | Dining preference, price tier, cuisine affinity |
| Loyalty card | Card name, program | Same as wallet pass seeding (see Part 3) |
| Gym membership | Gym name | Exercise frequency persona → post_workout mode more likely |

This is a general enrichment API. In the app, one camera tap can update a user's KG with genuinely useful, high-confidence preference data. The user *chose* to share it. The signal is explicit rather than inferred.

---

## Part 3: Wallet Passes as Knowledge Graph Cold-Start Seeds

### The Cold-Start Problem

A new Spark user has zero interaction history. The first time they open the app, the KG has no edges. Every recommendation is generic. The preference learning needs interactions to work — but users will churn before we accumulate enough interactions to be useful.

Wallet passes solve this cleanly. Most people's Apple/Google Wallet already contains 5-15 passes that reveal their lifestyle, preferences, and spending patterns. And they added those passes themselves — fully consensual.

### What PassKit Actually Gives You

**iOS PassKit** (`PKPassLibrary`):
```swift
import PassKit

let library = PKPassLibrary()
let passes = library.passes()  // All passes the user has added

for pass in passes {
    print(pass.organizationName)    // "Starbucks"
    print(pass.passTypeIdentifier)  // "pass.com.starbucks.rewardcard"
    print(pass.localizedName)       // "Starbucks Rewards"
    // Note: pass.userInfo is empty unless you're the pass issuer
    // We CANNOT read star balance, stamp count, or transaction history
    // We CAN read: exists, organization name, pass type, relevant date
}
```

**What we CAN read**: Pass existence and organization name.
**What we CANNOT read**: Balance, points, transaction history, personal info. This requires being the issuer.

That's fine. The *existence* of a pass is enough for KG seeding. Here's why:

### The Inference Table

| Pass | Inference | KG edges created |
|------|-----------|-----------------|
| Starbucks Rewards | Coffee preference, medium-high price tolerance | `PREFERS Cafe (weight:0.80)`, `PREFERS Attribute:Premium (0.65)` |
| REWE Payback | Supermarket shopper, price-aware | `PREFERS Attribute:Value (0.55)`, `context: grocery_habits` |
| DB BahnBonus | Regular rail commuter | `commute_mode: rail`, `station_context: HIGH`, boost for transit-window offers |
| Lufthansa Miles & More | Frequent traveler, above-average income | `PREFERS Attribute:Premium (0.70)`, likely `price_tier: high` |
| Deichmann Pass | Retail-oriented, value-focused | `PREFERS retail`, `PREFERS Attribute:Value` |
| Burgerkarte (any) | Fast-casual diner | `PREFERS MerchantCategory:FastCasual (0.65)` |
| Fitnessstudio card | Regular exerciser | `exercising mode: HIGH_PROBABILITY`, recovery offers more likely |
| Museum/city loyalty card | Culture-oriented, local | `PREFERS Attribute:Local`, boost for artisanal/independent venues |
| Local coffee shop stamp card | Highly local-loyal | Strong `PREFERS Cafe`, `AVOIDS Chains (0.50)` |

The confidence of these inferences is lower than explicit behavior — about 50-65% starting weight vs. 70-80% from direct interaction. We label them as `source: wallet_seed` in the KG edge metadata so they decay faster and get overridden quickly by actual interactions.

```python
def seed_kg_from_wallet_passes(passes: list[dict], user_id: str, conn):
    """
    Run once at first launch. Seeds KG with low-confidence priors from wallet.
    All inferences labeled as wallet_seed for appropriate weighting.
    """
    PASS_INFERENCE_MAP = {
        "starbucks": [
            ("PREFERS", "MerchantCategory:Cafe", 0.75, None),
            ("PREFERS", "Attribute:Premium", 0.60, None),
        ],
        "db bahnbonus": [
            ("PREFERS", "context:transit_window", 0.80, None),
            ("tag", "persona:commuter", 0.90, None),
        ],
        "lufthansa": [
            ("PREFERS", "Attribute:Premium", 0.70, None),
            ("tag", "price_tier:high", 0.65, None),
        ],
        "rewe": [
            ("PREFERS", "Attribute:Value", 0.55, None),
        ],
        # ... extend as needed
    }
    
    for pass_info in passes:
        org = pass_info["organization_name"].lower()
        for keyword, inferences in PASS_INFERENCE_MAP.items():
            if keyword in org:
                for relation, to_node, weight, context in inferences:
                    insert_kg_edge(
                        user_id, to_node, relation, weight,
                        context_conditions=context,
                        source="wallet_seed",       # Lower trust than behavior
                        decay_rate=1.5,             # Decays faster than real interactions
                        conn=conn
                    )
```

**React Native implementation:**
```javascript
// react-native-wallet (iOS) — read passes
import { WalletManager } from 'react-native-wallet';

const passes = await WalletManager.getPasses();
// Returns: [{ organizationName, localizedName, passTypeIdentifier, relevantDate }]
// Processed locally, KG seeds written to SQLite — nothing uploaded
```

**The pitch angle:**
> "When a user installs Spark, we ask if we can glance at their wallet. Most people have 8-10 loyalty passes. That's 8-10 preference signals we don't have to infer from scratch. A Starbucks Rewards holder's first café offer isn't a guess — we already know they're a coffee person. The cold start problem disappears."

---

## Part 4: Social Coordination — The Spark Wave

### The Problem with Traditional Referral Mechanics

"Share this for a discount" is spammy, self-interested, and people know it. It feels extractive — you're turning your friends into leads. Nobody respects that, nobody does it enthusiastically.

The Spark Wave mechanic is different because:
1. It's time-bounded and venue-specific — not a generic referral code
2. The benefit is symmetric — everyone in the group benefits equally (or the catalyst benefits more specifically)
3. It's built on top of the milestone coupon mechanic that already exists — not a new system

### The Anonymous Co-Movement Signal

Here's the non-creepy version of social proof. We DON'T need a social graph. We don't need users to share contacts. We just track **anonymous active sessions** moving toward a venue.

When 3+ anonymous Spark sessions have accepted offers for Bar Unter in the last 25 minutes, the backend knows this. It can include this signal in future offers for the same venue:

```python
def get_momentum_signal(merchant_id: str, window_minutes: int = 30) -> dict:
    """
    Count anonymous active sessions heading to or recently at this merchant.
    No identity. No social graph. Just a count.
    """
    recent_accepts = offer_audit_log.count_recent_accepts(
        merchant_id=merchant_id,
        since=datetime.now() - timedelta(minutes=window_minutes),
        status=["ACCEPTED", "REDEEMED"]
    )
    
    return {
        "active_sessions": recent_accepts,
        "momentum": "HIGH" if recent_accepts >= 4 else "BUILDING" if recent_accepts >= 2 else "LOW",
        "social_signal": f"{recent_accepts} Spark users heading there" if recent_accepts >= 2 else None,
    }
```

This feeds into the framing vocabulary:
```python
if momentum_signal["active_sessions"] >= 3:
    # Honest social proof — real users, not bots
    framing_context["social_count"] = momentum_signal["active_sessions"]
    # LLM can use: "3 Spark users are already heading there"
```

### The Spark Wave Mechanic

When a user accepts a milestone-type offer:
1. The offer includes a shareable "Wave Link" (optional, user taps to generate)
2. Wave Link is a short deep link: `spark://wave/{offer_id}/{anon_sharer_token}`
3. When friends click it → they get the same offer, tied to the same milestone
4. **The social incentive**: if the sharer's wave tips the milestone over the threshold, the sharer gets a "catalyst bonus" — e.g., double cashback on their own redemption

```
Milestone: Bar Unter → 50 guests → first 20 get entry refund
Current: 16 guests
─────────────────────────────────────────────────────
User accepts offer: gets standard entry refund offer
                         ↓
            [Optional: Share this wave]
                         ↓
User shares link with 4 friends → all 4 come
                         ↓
Milestone fires at 20 → user gets: entry refund + catalyst bonus (€5 extra)
Friends get: standard entry refund
```

**What makes this work:**
- Physical redemption = no fake accounts (you have to show up to get the reward)
- Time bounded = urgency is genuine (milestone is tonight)
- Symmetric benefit = not extractive of friends
- Catalyst bonus = actual incentive to share, beyond social obligation

**What makes this NOT creepy:**
- User initiates sharing (no auto-share)
- Deep link reveals nothing about the sender (anonymous token)
- Friends don't need an account to see the offer (but need one to redeem)
- No contact harvesting, no social graph, no "invite from contacts" dark pattern

### Integration with Milestone Coupon Backend

The wave mechanic is an extension of Finn's milestone progress tracking:

```sql
-- Extend milestone_progress with wave tracking
ALTER TABLE milestone_progress ADD COLUMN wave_arrivals INTEGER DEFAULT 0;
ALTER TABLE milestone_progress ADD COLUMN catalyst_user_session TEXT;  -- anon session that created the wave

-- Wave links table
CREATE TABLE wave_links (
    wave_token TEXT PRIMARY KEY,
    offer_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL,
    created_by_session TEXT,    -- anonymous session ID
    created_at TEXT,
    expires_at TEXT,
    uses INTEGER DEFAULT 0,
    milestone_fired INTEGER DEFAULT 0
);
```

### The Demo Scenario

> "Lars accepts the Bar Unter milestone offer on his Spark. He taps 'Start a Wave' and shares the link to his friend group on WhatsApp. 3 friends click it and accept. 15 minutes later, the milestone fires. Lars gets: entry refund + €5 catalyst bonus. Friends get: entry refund. Bar Unter: went from 16 to 24 guests — that initial crowd creates the atmosphere that pulls in the remaining 26 organically."

---

## Part 5: How All of This Flows Into the Knowledge Graph

The KG is not just preference storage. With these new signals, it becomes the integrating layer for every context input source. Here's how each new signal updates the graph:

### Post-Workout Signal → KG

```python
# On post_workout mode detection:
update_kg_edge(
    user_id, "Attribute:HealthConscious", "SEEKS",
    weight_delta=+0.02,   # Small nudge per detection
    context_conditions={"when": ["post_workout"]},
    source="imu_state"
)
# On post-workout offer acceptance:
update_kg_edge(
    user_id, f"MerchantCategory:{accepted_merchant.type}", "PREFERS",
    weight_delta=+0.12,
    context_conditions={"when": ["post_workout"]},
    source="offer_acceptance"
)
```

### Wallet Pass Seed → KG

Already described in Part 3. Seeds low-weight edges labeled `wallet_seed` that decay faster than behavioral signals.

### OCR Train Scan → KG (Commute Pattern)

```python
# When user scans a DB ticket:
update_kg_edge(
    user_id, "context:transit_window", "RESPONDS_TO",
    weight_delta=+0.15,
    source="user_enrichment_ocr"
)
# Tag their commute route if scanned multiple times:
if destination in user_commute_history:
    update_kg_node_metadata(user_id, {"primary_commute_dest": destination})
```

### Wallet/Loyalty Card Scan → KG (if user scans a physical card via OCR)

Some loyalty programs aren't in digital wallets but users carry physical cards. The same OCR pipeline handles these — same inference logic, slightly lower confidence (`source: card_scan_ocr`).

### Spark Wave Participation → KG

```python
# User INITIATES a wave (social personality signal):
update_kg_edge(
    user_id, "Attribute:Social", "PREFERS",
    weight_delta=+0.08,
    context_conditions={"when": ["evening"]},
    source="wave_initiation"
)
# User ACCEPTS via someone else's wave (open to social recommendations):
update_kg_edge(
    user_id, "Attribute:Social", "PREFERS",
    weight_delta=+0.05,
    source="wave_acceptance"
)
```

### The Unified KG Update Model

Every signal source has a weight policy. The KG reflects this — edges from explicit behavior matter more than passive inference:

| Signal Source | Starting Weight | Decay Rate | Override Priority |
|--------------|----------------|-----------|-------------------|
| Direct accept/decline | 0.70-0.80 | Normal (1.0×) | Highest |
| OCR scan (user-initiated) | 0.65-0.75 | Normal (1.0×) | High |
| Wallet pass seed | 0.50-0.65 | Fast (1.5×) | Medium |
| IMU state inferred | 0.45-0.55 | Fast (1.5×) | Medium |
| Wave participation | 0.40-0.55 | Normal | Low-Medium |

Decay is logarithmic with time. An edge from 6 weeks ago matters ~40% less than a fresh one. Social mode toggle is a session-scoped temporary edge that expires at `session_end` — no decay needed, just time-bounded.

---

## Hackathon Build Priority for These Features

Not everything here is worth building in 24h. Honest assessment:

| Feature | Build Time | Demo Value | Risk |
|---------|-----------|-----------|------|
| Post-workout movement mode | 1h | High — new scenario, nobody else has it | Low |
| OCR transit ticket scan | 3-4h | Very High — the "4 min warning" moment is demo gold | Medium (ML Kit setup) |
| Wallet pass seed (iOS) | 2h | High — clean cold-start story for pitch | Low (PassKit is stable) |
| Anonymous co-movement count | 1h | Medium — adds honest social proof framing | Low |
| Spark Wave mechanic | 4-5h | High — viral/social story for merchants | High (multi-device demo) |

**Recommendation:**
- Build post-workout mode: fast, unique, impactful
- Build OCR transit scan: the delay scenario is already in the demo — this makes it perfect
- Build wallet seed: adds the cold-start story to the KG pitch
- Skip Spark Wave for the demo (hard to show without two phones and live coordination), but pitch it as the next feature — it's compelling on paper

---

## The Sentence That Connects All of This

> "Most apps know where you are. Spark knows what you're about to do next — because it listens to your body, reads what you choose to share, and remembers what you've shown it you value. The result isn't a notification app with personalization. It's a local intelligence layer that gets smarter without getting creepier."

That's the close for the architecture section of the pitch. Every piece in this doc earns a line in that sentence.
