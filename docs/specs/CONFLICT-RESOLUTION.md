# Stakeholder Conflict Resolution

## Overview: Balancing User & Merchant Needs

Spark's resolution engine prevents poor user experiences (e.g., sending a social user to an empty nightclub) by analyzing the predicted state of a venue at the user's arrival time, rather than just the current state.

---

## Conflict Matrix

The engine evaluates recommendations based on user preference and venue occupancy:

| User Preference | Venue State | Recommendation Decision |
|---|---|---|
| **Social / Busy** | Empty (<15%) | **HARD CONFLICT:** Suppress recommendation. |
| **Social / Busy** | Building (30-60%) | **SOFT CONFLICT:** Recommend with momentum framing. |
| **Quiet** | Empty | **NO CONFLICT:** Natural match; recommend. |
| **Quiet** | Busy | **REVERSE CONFLICT:** Suppress recommendation. |

---

## The Temporal Prediction Layer

Decisions are based on the **predicted state at arrival**, computed using Payone historical trajectories and real-time walk distance.

```python
# Predicted Occupancy = f(Current Rate, Historical Trend, Arrival Window)
if user_social_pref == "social" and predicted_occ_at_arrival < 40:
    return "DO_NOT_RECOMMEND"
```

---

## Coupon Mechanisms

Coupons are used to bridge the gap between user intent and venue state. Merchants select strategies based on their specific needs:

### 1. Flash Discount
Simple percentage off for a limited time. Best for cafés and bakeries with perishable inventory.

### 2. Milestone Coupon (Proof of Social)
"Discount fires when 50 guests arrive." The coupon itself acts as a signal of expected busyness, resolving the social user's hesitation.

### 3. Time-Bound Entry
"Free entry before 22:00." Incentivizes early arrival to build atmosphere.

### 4. Visibility Only
Merchant pays for discovery without discounting. Appropriate for premium venues or quiet spots matching quiet-preferring users.

---

## Framing Rules: Factual Integrity

While the LLM generates the creative "wrapper," the factual occupancy state is hard-railed.

- **Band: Empty but Filling:** Used when current occupancy is low but predicted to rise before arrival.
- **Band: Quiet Intentional:** Used when the user explicitly seeks a quiet environment.
- **Prohibited Vocabulary:** The LLM is architecturally blocked from using terms like "buzzing" or "packed" if current occupancy is below 60%.
