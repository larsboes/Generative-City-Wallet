# 10 — Offer Selection, Ranking & Anti-Spam

## The Brief's Most Important Design Rule (That We Almost Ignored)

From the challenge: *"What is missing is the layer that connects these signals in real time and turns them into a single, specific, well-timed offer."*

**Single. Not a feed. Not a list. One offer.**

This is both a UX principle and an algorithmic problem. If 5 Stuttgart cafés are all quiet at 14:30 and the user is browsing — which one gets the offer? How do we decide? What stops the user from being spam-blasted with 5 cards at once?

These questions aren't answered anywhere else in the docs. This file answers them.

---

## The "One Offer at a Time" Principle

Spark sends exactly one offer at a time. This is non-negotiable for three reasons:

1. **The brief says so** — "a single, specific, well-timed offer... not a generic discount, but *this café, this drink, right now, because the moment is right.*" A feed of options destroys the "magic feeling" of precision.

2. **3-second comprehension** — one offer can be understood in 3 seconds. Five cannot. The moment you show a list, you've created a decision burden, which is the opposite of what Spark is for.

3. **Psychological commitment** — a single offer feels like it was made for you. A list feels like a marketplace. The former triggers spontaneous action; the latter triggers deliberation and abandonment.

**Implementation rule:** Before any offer is delivered, check: does the user have an active unresolved offer? If yes → do not deliver another. Wait for accept, decline, or expiry first.

---

## The Offer Ranking Algorithm

When multiple merchants qualify (quiet period detected, user in range), Spark scores each and selects the top one.

### Scoring Formula

```python
def score_merchant(merchant, composite_state, user_preferences):
    score = 0.0
    
    # 1. Payone Density Score (0-40 points) — most important
    # The quieter the merchant relative to baseline, the higher the urgency
    density_drop = 1 - merchant.density_score  # 0=normal, 1=completely silent
    score += density_drop * 40
    
    # 2. Distance Score (0-25 points)
    # Closer = more actionable = higher score
    # Sweet spot: 50-200m. Too close (<30m) = user already there.
    # Too far (>500m) = not "right now."
    if merchant.distance_m < 30:
        score += 5   # Already there, less urgency
    elif merchant.distance_m <= 200:
        score += 25  # Prime range
    elif merchant.distance_m <= 400:
        score += 15
    else:
        score += 5   # Far, low score
    
    # 3. User Preference Match (0-20 points)
    category_weight = user_preferences.category_weights.get(
        merchant.category, 0.5
    )
    score += category_weight * 20
    
    # 4. Weather-Merchant Alignment (0-10 points)
    # Cold weather → café/bakery gets bonus. Hot → juice bar bonus.
    alignment = compute_weather_alignment(
        composite_state.weather_need, 
        merchant.category
    )
    score += alignment * 10
    
    # 5. Inventory Bonus (0-5 points)
    # Merchant has submitted a surplus inventory signal
    if merchant.has_inventory_signal:
        score += 5
    
    # Penalties
    if merchant.recently_offered:  # Offered this merchant < 2h ago
        score -= 50  # Effectively eliminates from consideration
    
    if merchant.user_has_declined_before:
        score -= 15
    
    return score
```

### Tiebreaker
If two merchants score within 5 points of each other: prefer the one with the higher Payone density drop (more urgent situation) → more emotionally compelling offer narrative.

### Minimum Threshold
A merchant must score ≥ 30 points to trigger an offer at all. Below this, the composite state is not strong enough — don't interrupt the user.

---

## Anti-Spam Rules

### User-Side Limits

| Rule | Value | Rationale |
|------|-------|-----------|
| Max offers per day | 3 | Respect attention. After 3, even relevant offers feel like spam. |
| Cooldown after accept | 4 hours | User just redeemed, leave them alone |
| Cooldown after decline | 2 hours | They weren't in the mood; don't push |
| Cooldown after expiry | 90 minutes | They saw it but didn't act; try again later |
| Same merchant cooldown | 24 hours | Never re-offer the same merchant within a day |
| Commuting mode | Permanent block | Never interrupt a commute |
| After 21:00 | Block (unless user in bar category + evening mode) | Respect end-of-day |

### Merchant-Side Limits

| Rule | Value | Rationale |
|------|-------|-----------|
| Max offers sent per day | 20 | Prevents flooding users from one desperate merchant |
| Cooldown between offers | 30 minutes | One at a time; let one expire before the next |
| Max concurrent active offers | 3 | Cap on outstanding unaccepted offers |

### System-Level

- **Cooldown after consecutive non-acceptance:** If user has seen 3 offers today and declined all 3, pause for 6 hours. The context is wrong — stop guessing.
- **Geographic clustering prevention:** If 4 merchants in the same 100m block all qualify, only offer from the top-scoring one. Don't let one street corner spam a user from multiple angles.

---

## Offer Timing: Anticipatory vs. Reactive

Two delivery modes:

### Reactive (default)
Merchant hits quiet threshold NOW → offer delivered immediately to nearby users.

### Anticipatory (bonus feature)
Historical Payone pattern shows merchant will hit quiet period in 25 minutes. User is 10 min walk away. Deliver offer now so user *arrives* when the lull begins.

```python
def should_anticipate(merchant, user_distance_m):
    walking_speed_mps = 1.2  # ~4.3 km/h average
    walk_time_min = (user_distance_m / walking_speed_mps) / 60
    
    predicted_lull_in_min = merchant.predict_next_quiet_period()
    
    # Deliver offer if user will arrive ~5 min into predicted lull
    return abs(walk_time_min - (predicted_lull_in_min + 5)) < 8
```

**In the pitch:** Call this "anticipatory demand matching." It's the Amazon anticipatory shipping equivalent — the system acts before the problem is fully manifest. Very impressive sounding, very simple to implement.

---

## Offer Lifecycle State Machine

```
GENERATED
    │
    ▼
QUEUED (waiting for right moment to deliver)
    │
    ▼ (user in browsing mode + not on cooldown)
DELIVERED ──────────────────────────────────────┐
    │                                           │
    ├──► ACCEPTED (within valid window)         │
    │         │                                 │
    │         ▼                                 │
    │    QR_ISSUED (15 min validity)            │
    │         │                                 │
    │         ├──► REDEEMED ──► CASHBACK        │
    │         └──► QR_EXPIRED (graceful)        │
    │                                           │
    ├──► DECLINED (user swipes away)            │
    │         │                                 │
    │         └──► [2h cooldown starts]         │
    │                                           │
    └──► EXPIRED (valid window elapsed) ◄───────┘
              │
              └──► [90min cooldown starts]
```

Every state transition is logged (anonymized) for analytics and preference model updates.
