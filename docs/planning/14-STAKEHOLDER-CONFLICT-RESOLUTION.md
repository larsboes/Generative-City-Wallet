# 14 — Stakeholder Conflict Resolution: Matching Social Intent to Venue State

> Archived in-place: implementation now lives in runtime docs/code (`docs/ARCHITECTURE.md`, `apps/api/src/spark/services/conflict.py`). Keep this file for planning rationale.

## The Real Conflict (It's More Nuanced Than It Looks)

The naive framing: "user wants full venue, merchant needs to fill it." But that's not actually the full problem space. Let's map the actual conflict matrix:

| User wants | Venue state | Conflict? |
|-----------|-------------|-----------|
| Social / busy | Empty (<15%) | **HARD CONFLICT** — social user will hate this |
| Social / busy | Building (30–60%) | **SOFT CONFLICT** — solvable with timing + framing |
| Social / busy | Busy (70%+) | **NO CONFLICT** — natural match, no coupon needed |
| Quiet | Empty | **NO CONFLICT** — perfect for them, coupon is bonus |
| Quiet | Busy | **REVERSE CONFLICT** — don't recommend regardless |

The hard conflict (empty + social user) is the only case that's genuinely unsolvable with a coupon alone. A 20% discount does not create atmosphere. You cannot bribe someone into enjoying an empty nightclub. **The system must detect this case and refuse to recommend, not lower the price further.**

---

## The Prediction Layer Makes Most Conflicts Disappear

The key insight: the conflict is **temporal**, not permanent. An empty venue at 21:00 on a Friday is not an empty venue at 22:30. Payone historical data tells us the fill trajectory.

```
Conflict resolution = f(current_occupancy, fill_rate_prediction, user_arrival_time)
```

```python
def resolve_conflict(venue, user_social_pref, current_time):
    current_occ = venue.current_occupancy_pct  # From Payone txn rate
    
    # Predict occupancy at estimated arrival (walk time + 5 min buffer)
    walk_time = venue.distance_m / 80  # ~80m/min average browsing pace
    arrival_time = current_time + timedelta(minutes=walk_time + 5)
    predicted_occ = venue.predict_occupancy_at(arrival_time)
    
    if user_social_pref == "social":
        if predicted_occ >= 60:
            return "RECOMMEND"           # Will be lively when they arrive
        elif predicted_occ >= 40:
            return "RECOMMEND_WITH_FRAMING"  # "Just warming up" — honest
        else:
            return "DO_NOT_RECOMMEND"    # Won't be lively, don't mislead
    
    elif user_social_pref == "quiet":
        if current_occ <= 40:
            return "RECOMMEND"           # Perfect for them
        elif current_occ <= 65:
            return "RECOMMEND_WITH_FRAMING"  # "Still some quiet spots"
        else:
            return "DO_NOT_RECOMMEND"    # Wrong vibe entirely
```

**The decision is primarily about the predicted state at arrival, not the current state.** A venue at 20% capacity that historically hits 75% in 45 minutes is NOT an empty venue for a user who's 10 minutes away.

---

## When Do We Recommend Without a Coupon?

Four cases where a coupon is irrelevant or unnecessary:

1. **Natural preference match**: User wants quiet → venue is quiet → just recommend it. No coupon needed. The match IS the value.
2. **Venue already busy + social user**: They want this anyway. A coupon would be wasted budget and might even feel weird ("why are you giving me a coupon for the city's hottest bar on a Friday?").
3. **Predictive recommendation**: "This bar fills up at 22:00 every Friday — you're 8 minutes away, and it's 21:52." The time intelligence IS the offer. No discount needed.
4. **Ambient discovery**: User isn't explicitly in offer-seeking mode but passes by a venue they'd enjoy. Show a soft nudge ("Café Römer, 40m — rated highly by people who walk like you") without any commercial mechanism.

**The rule:** Coupons are for bridging a gap between natural preference and current venue state. If no gap exists, no coupon needed. Sending a coupon when none is needed is noise that degrades the signal quality of the whole system over time.

---

## Merchant Coupon Options: Design Philosophy

Merchants don't just choose a discount percentage. They choose a *mechanism* that serves a specific filling strategy. These are meaningfully different:

### Option A: Flash Discount (Simple)
`"X% off for the next Y minutes for Spark users"`

- Best for: cafés, bakeries, restaurants with perishable inventory
- Problem for clubs: incentivizes arrival at any time, doesn't build atmosphere
- When to surface: when venue is 30–60% below baseline, user is nearby and browsing

### Option B: Milestone Coupon (Smart — Perfect for Clubs)
`"When we hit [N] guests tonight, first [M] Spark arrivals get their cover back"`

- Best for: bars and clubs that need critical mass
- The genius: merchant only pays if they succeed at filling. Zero risk. Pure incentive alignment.
- For the social user: honest framing. "Bar X is running a milestone — they're at 22 guests, targeting 50. First arrivals get rewarded."
- User who wants social knows: if the milestone fires, it means the venue got busy. Win-win.
- This resolves the hard conflict: the coupon itself signals "others are coming."

### Option C: Time-Bound Entry Deal
`"Free/discounted entry before [time]"`

- Best for: venues where early arrival creates the atmosphere for later
- Honest signal: "Be first, shape the night"
- Works for users who LIKE being early crowd-setters (a real persona — "I discover places before they're cool")

### Option D: Drink Anchoring
`"First drink on us / 2-for-1 until 22:00"`

- Best for: bars where the first drink commits the customer for 2+ hours
- Low cost per user, high retention value
- Works across all occupancy levels
- Doesn't require honest occupancy claims — purely value-based

### Option E: No Coupon — Visibility Only (New Idea)
Merchant pays for visibility on Spark without a discount. "We're open, we have space, show us to relevant users."

- Lower merchant commitment
- Appropriate for quieter venues that serve quiet-preferring users
- Generates discovery value without discounting their brand
- Especially relevant for premium venues that don't want "discount" associations

---

## The Framing Rules: What the LLM Can and Cannot Say

### The principle (Air Canada applied here):
Framing is soft and LLM-generated. Occupancy facts are hard-railed from Payone data. The LLM chooses the *emotional register* — it cannot invent the *factual state*.

### Allowed framing vocabulary by occupancy band:

```python
FRAMING_VOCABULARY = {
    "empty_but_filling": [   # < 30% now, predicted 60%+ at arrival
        "Just getting started",
        "Be first through the door",
        "Early bird exclusive",
        "VIP arrival window",
        "The pre-game starts here",
    ],
    "building_momentum": [   # 30–60%, predicted 70%+ at arrival
        "Just warming up",
        "Getting lively",
        "Join the crowd forming",
        "It's getting busy — join now",
    ],
    "quiet_intentional": [   # 30–60%, predicted stays similar (for quiet users)
        "Quiet and ready for you",
        "Your table's waiting",
        "No queue, no wait",
        "The calm you need",
    ],
    "busy": [                # 70%+
        "In full swing",     # Don't need this for social users — they'll see it anyway
        "Last spots available",
    ],
}

# Hard rails: LLM CANNOT generate these if current_occ < 60%
BANNED_IF_EMPTY = [
    "buzzing", "packed", "full house", "lively", "electric atmosphere",
    "everyone's here", "the place to be tonight"
]
```

The LLM prompt includes current occupancy as a fact and the allowed vocabulary band. It cannot deviate into banned territory.

---

## Explainability: Every Recommendation Must Be Traceable

The decision chain for every recommendation:

```
Recommendation: Bar Unter, 20:15
├── User context: social_preference=HIGH (set manually at 19:45)
├── Venue: Bar Unter
│   ├── Current occupancy: 31% (from Payone: 8 txn/hr vs. 26 avg on Friday)
│   ├── Predicted at 20:28 (user arrival): 58% (from historical Friday trajectory)
│   ├── Active coupon: Milestone (free entry after 50 guests; current: 16)
│   └── Distance: 140m (~2min walk)
├── Conflict check: social + 31% = SOFT CONFLICT
├── Resolution: predicted_occ_at_arrival=58% → RECOMMEND_WITH_FRAMING
├── Framing band: "building_momentum"
├── Coupon mechanism: Milestone — aligns user + merchant interest
└── Decision: RECOMMEND
   Final message: "Just warming up — join now and get your entry back when Bar Unter hits 50 guests. 140m, 2 min."
```

This trace is stored in the offer audit log. User can see why. Merchant can see why. Regulator can audit why. This is not a "black box" recommendation — it's a deterministic decision with an LLM-generated wrapper.

---

## The Decision Tree (Implementation)

```
Input: user, venue, current_time

1. Get user preference: SOCIAL | QUIET | NEUTRAL
2. Get venue occupancy: current (Payone txn rate → %) + predicted_at_arrival
3. Get active coupon: type, threshold, value

IF social:
    IF predicted_at_arrival >= 60%:
        → RECOMMEND (no coupon needed if 70%+, optional if 60%)
        → Framing: "busy" or "building_momentum"
    ELIF predicted_at_arrival >= 40% AND milestone_coupon_active:
        → RECOMMEND_WITH_FRAMING
        → Framing: "building_momentum", show milestone progress
    ELIF predicted_at_arrival >= 40% AND time_bound_or_drink_deal:
        → RECOMMEND_WITH_FRAMING
        → Framing: "empty_but_filling"
    ELSE:
        → DO_NOT_RECOMMEND
        → Re-check in 30 minutes

IF quiet:
    IF current_occ <= 50%:
        → RECOMMEND (coupon optional, discovery framing)
    ELIF current_occ <= 70%:
        → RECOMMEND_WITH_FRAMING ("still some quiet spots")
    ELSE:
        → DO_NOT_RECOMMEND (wrong vibe)

IF neutral:
    → Standard offer flow (no occupancy constraint)
    → Coupon is the primary driver
```

**This decision tree is implemented as pure rule logic, not LLM. The LLM only executes after RECOMMEND is decided and generates the framing. The LLM never decides whether to recommend.**

---

## What This Means for the Pitch

> "Spark doesn't just detect quiet periods and fire coupons. It resolves the conflict between what a user wants and what a venue needs — in real time. For a social user approaching an empty bar, Spark checks the Payone fill trajectory. If the bar fills in 45 minutes, the user arrives at the right time. If it historically stays empty, Spark doesn't recommend it at all — because a misleading recommendation is worse than no recommendation. The coupon isn't the product. The timing intelligence is."

That's the sentence that separates you from every team doing "weather + discount = offer."
