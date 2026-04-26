# User Knowledge Graph

## Overview: Conditional Personalization

Standard preference models use flat vectors (e.g., "likes coffee"). Spark uses an on-device property graph to represent **conditional preferences** (e.g., "prefers cozy cafés when it is cold and they are alone").

This model allows for high-fidelity personalization while maintaining complete data sovereignty on the user's device.

---

## Schema Design

The graph is implemented locally (e.g., using SQLite or a specialized mobile graph library).

### Node Types
- **User:** The primary node.
- **MerchantCategory:** (e.g., Café, Bar, Bakery).
- **Attribute:** (e.g., Cozy, Loud, Quiet, Artisanal).
- **ContextCondition:** (e.g., Cold, Hot, Post-Workout, Social, Evening).
- **Offer:** Historical interaction records.
- **Merchant:** Specific visited venues.

### Edge Relationships
- **PREFERS / SEEKS:** Weighted preference edges, often conditional on a `ContextCondition`.
- **AVOIDS:** Negative preference weights.
- **ACCEPTED / DECLINED:** Historical interaction edges used for reinforcement learning.

---

## Intent Derivation Logic

Given a current context, the engine traverses the graph to find overlapping preference paths.

**Example Query:**
*Context: Cold + Tired + Alone*
1. User → [PREFERS when:Cold] → Café
2. User → [PREFERS when:Tired] → ComfortFood
3. Result → **Warm Comfort Café** (intersection of active paths).

### Reinforcement Learning: Online Updates

Weights on edges are updated based on user interactions:
- **Accept:** Boost weights for category, attributes, and context conditions associated with the offer.
- **Decline:** Symmetrically reduce weights, applying temporal decay to historical data.

---

### Behavioral Seeding (Cold Start)

Spark bootstraps the Knowledge Graph using on-device signals before the first interaction.

1. **Transaction Categories:** Analyzing purchase history (e.g., "coffee shops > 3/week") seeds initial `PREFERS` edges.
2. **Wallet Pass Seeding:** The existence of loyalty passes (e.g., Starbucks Rewards, Airline miles, Gym memberships) revealed through on-device PassKit access is used to seed lower-confidence preference priors.

### Safety Boundaries (GDPR Article 9)

Inferences are strictly limited to behavioral preferences. The system is architecturally blocked from inferring health states, medical needs, or reproductive life events based on purchase patterns.

---

## User Control & Transparency

The Knowledge Graph is user-visible and user-editable. Users can inspect "What Spark thinks" and manually adjust or delete preference edges, satisfying GDPR Article 22 requirements for transparency in automated decision-making.
