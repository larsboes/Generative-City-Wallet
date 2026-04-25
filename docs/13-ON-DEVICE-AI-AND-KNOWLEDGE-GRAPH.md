# 13 — On-Device AI, Knowledge Graph & Liability Architecture

## Three Threads That Connect Into One Design

Three things landed at once: the knowledge graph idea, the on-device LLM options (Gemma 3n, Qwen3), and the Air Canada AI liability Reddit thread. On the surface they're separate topics. They're actually the same argument.

**The argument:** The only way to build a trustworthy, GDPR-compliant, legally defensible AI-personalization system for a German savings bank is to keep sensitive inference on-device, represent user knowledge in a transparent local graph, and enforce hard constraints on every AI output that has business or legal consequence.

The three threads enforce each other. Here's how.

---

## Part 1: The User Knowledge Graph

### Why Flat Preference Vectors Are Not Enough

Our current preference model (documented in `04-GENERATIVE-ENGINE.md`) uses weighted flat vectors:
```json
{"price_tier": "mid", "category_weights": {"cafe": 0.8, "bar": 0.4}}
```

This works, but it can't represent conditional preferences — and most real preferences are conditional.

- "I like coffee shops" is not the same as "I like coffee shops *when it's cold and I'm alone*"
- "I avoid bars" is not the same as "I avoid bars *on weekday lunchtimes but actively seek them on Friday evenings with the social mode on*"
- "I want to meet people" said at 20:00 is categorically different from the same words at 13:00

Flat vectors treat all context as independent dimensions. A knowledge graph treats them as relationships — which is how human preferences actually work.

### The User Knowledge Graph Schema

An on-device property graph. Nodes are entities; edges are relationships with context conditions and weights.

**Node types:**
- `User` (singleton, the user)
- `MerchantCategory` (Cafe, Bar, Bakery, HairSalon, ...)
- `Attribute` (Cozy, Loud, Quiet, Artisanal, Sustainable, Quick, ...)
- `ContextCondition` (Cold, Hot, PostWorkout, Tired, Social, Alone, Evening, ...)
- `Offer` (past offers the user interacted with)
- `Merchant` (specific merchants user has visited)

**Edge types with examples:**
```
User ──[PREFERS | weight:0.85, when:Cold]──► MerchantCategory:Cafe
User ──[PREFERS | weight:0.80, when:Evening+Social]──► Attribute:Loud
User ──[AVOIDS  | weight:0.70, when:WorkdayLunch]──► MerchantCategory:Bar
User ──[SEEKS   | weight:0.90, when:PostWorkout]──► Attribute:Cold
User ──[ACCEPTED| ts:2025-04-22, context:{cold,tuesday_lunch}]──► Offer:ABC
Offer:ABC ──[AT]──► Merchant:CafeRoemer
Offer:ABC ──[GENERATED_WHEN]──► Context:{cold,quiet,browsing}
MerchantCategory:Cafe ──[HAS_ATTRIBUTE]──► Attribute:Cozy
Merchant:CafeRoemer ──[IS_A]──► MerchantCategory:Cafe
Merchant:CafeRoemer ──[TAGGED]──► Attribute:Cozy
```

### What the Graph Enables That Flat Vectors Can't

**1. Conditional preference inference:**
Query: "User is cold + tired + alone. What merchant type?"
Graph traversal: User → [PREFERS when:Cold] → Cafe + [PREFERS when:Tired] → ComfortFood → overlapping result = warm comfort café. **Not derivable from flat weights.**

**2. Cross-category transfer:**
User has accepted 5 coffee shop offers (all tagged: Artisanal, Local, Quiet). New merchant type appears: craft beer bar (tagged: Artisanal, Local). Graph similarity: 2/3 attributes match. Cold start solved without explicit beer history.

**3. Explicit "social mode" from user input:**
User says: "I want to meet people tonight" → temporary high-weight edge added:
```
User ──[SEEKS | weight:0.95, expires:session_end]──► Attribute:Lively
```
This traverses to bar > café > quiet bookshop. **Directly implements Lars's original idea.**

**4. Temporal decay:**
Edge weights decay logarithmically with time. Last week's accept pattern matters 4× more than last month's. Natural, no separate decay logic needed — just timestamp on edges.

**5. User-visible, user-editable:**
The graph can be rendered as a simple preference list: "You tend to prefer: quiet cafés when cold (strong), social bars in evenings (moderate), avoid fast food (always)." User can tap to edit. This is GDPR Article 22 compliance (right to contest automated decisions) built into the UX.

**6. Right to erasure:** Delete the graph file. Done. Zero server call needed.

### Implementation for Hackathon

A full graph DB is overkill. Use SQLite with two tables:

```sql
CREATE TABLE kg_nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- 'category', 'attribute', 'offer', 'merchant'
    label TEXT NOT NULL,
    metadata JSON
);

CREATE TABLE kg_edges (
    id TEXT PRIMARY KEY,
    from_node TEXT NOT NULL,
    to_node TEXT NOT NULL,
    relation TEXT NOT NULL,  -- 'PREFERS', 'AVOIDS', 'SEEKS', 'ACCEPTED', etc.
    weight REAL DEFAULT 0.5,
    context_conditions JSON,  -- {"when": ["cold", "alone"]}
    created_at INTEGER,
    last_reinforced INTEGER,
    expires_at INTEGER  -- null = permanent
);
```

Graph query for intent derivation:

```python
def query_intent(user_id, current_context):
    """Given current context, return ranked merchant categories + attributes."""
    
    # Get all PREFERS/SEEKS edges from User
    edges = db.query("""
        SELECT to_node, relation, weight, context_conditions
        FROM kg_edges 
        WHERE from_node = ? AND relation IN ('PREFERS', 'SEEKS', 'AVOIDS')
        ORDER BY weight DESC
    """, user_id)
    
    scored = {}
    for edge in edges:
        # Check if context conditions match current context
        match_score = compute_context_match(
            edge.context_conditions, 
            current_context
        )
        # Weight × context match → effective preference score
        effective_weight = edge.weight * match_score
        if edge.relation == 'AVOIDS':
            effective_weight *= -1
        
        scored[edge.to_node] = scored.get(edge.to_node, 0) + effective_weight
    
    return sorted(scored.items(), key=lambda x: x[1], reverse=True)
```

**This replaces the flat preference vector in the intent computation. The output is still a compact set of signals that go into the intent vector — the graph is the computation layer, not the transmission format.**

---

## Part 2: On-Device LLM Options — Real Capabilities

### The Model Landscape (April 2025)

| Model | Params | On-Device? | Function Calling | License | Best For Spark |
|-------|--------|-----------|-----------------|---------|----------------|
| **FunctionGemma** | 270M | ✅ Native (Google AI Edge) | ✅ Designed for it | Gemma | Intent extraction → tool calls |
| **Gemma 3 1B** | 1B | ✅ MediaPipe LLM SDK | ✅ With prompting | Gemma (gated) | Lightweight general reasoning |
| **Gemma 3n E2B** | eff. 2B | ✅ Google AI Edge | ✅ | Gemma (gated) | Multimodal (image+audio+text) |
| **Gemma 3n E4B** | eff. 4B | ⚠️ Flagship only | ✅ | Gemma (gated) | Richer reasoning on premium devices |
| **Qwen3-1.7B** | ~2B | ✅ With quantization | ✅ Native | Apache 2.0 | Best open license; strong reasoning |
| **Qwen3-4B** | 4B | ⚠️ High-end devices | ✅ Native | Apache 2.0 | Best small model for complex tasks |
| **Qwen3-35B-A3B** | 3B active | ❌ Server only | ✅ Native | Apache 2.0 | Server-side enrichment |

### FunctionGemma: The Key Discovery

From the Google AI Edge Gallery blog: **FunctionGemma is a 270M parameter model specifically designed for on-device function calling.** It routes user intent to tool definitions — entirely offline, on mobile.

This is architecturally perfect for Spark's on-device layer:

```
Sensor signals → FunctionGemma → Structured tool calls

FunctionGemma receives:
  - Movement: "slow walking, stopped twice"
  - Time: "Tuesday 12:47"
  - User context: [from knowledge graph query]
  - Available tools: [get_weather_need(), compute_time_bucket(), 
                      query_preference_graph(), build_intent_vector()]

FunctionGemma outputs:
  tool_call: build_intent_vector({
    grid_cell: "STR-MITTE-047",  // from quantized GPS
    movement_mode: "browsing",
    weather_need: "warmth_seeking",  // tool computed locally
    time_bucket: "tuesday_lunch",
    social_preference: "quiet",     // from graph query
    price_tier: "mid"               // from graph query
  })
```

**Nothing with PII runs through FunctionGemma.** It processes signals, not personal data. The tool calls it makes are to local functions only.

### Gemma 3n: The Multimodal Wildcard

Gemma 3n (E2B, E4B) uses **MatFormer architecture** — a nested model that can run at different parameter budgets depending on device capability. Tagged: image, audio, video, text-to-text.

**Spark opportunity:** Gemma 3n can process the merchant's photos (from Google Places) to extract visual attributes for GenUI. Instead of static imagery_prompt generation via text, the on-device model could analyze the actual merchant photo and describe its vibe: "warm, wooden interior, soft lighting → cozy amber palette." This feeds directly into the GenUI spec.

This is ambitious for hackathon but worth noting as a feature direction.

### Qwen3: The Open Alternative

Qwen3-1.7B (~2B actual params, Apache 2.0) is the strongest open-license option:
- Runs on-device with INT4 quantization (~1GB model)
- Native function calling support
- No Google dependency
- No gated license (Gemma requires Google account acceptance)

For a hackathon where you need to move fast: Qwen3-1.7B via `transformers.js` or `llama.cpp` WebAssembly binding is faster to set up than Google AI Edge.

**Qwen3-35B-A3B (MoE) for the server:**
35B total parameters, but Mixture-of-Experts means only 3B parameters are active per token. Server-side cost similar to a 3B dense model but quality closer to a much larger model. Could replace Claude for the server-side offer generation if API costs are a concern. Still needs proper GPU server though.

### Recommended Architecture for Spark

```
ON-DEVICE:
├── FunctionGemma (270M) — intent extraction + tool calling
│   └── OR Qwen3-1.7B INT4 if faster to set up (no Google account)
├── User Knowledge Graph (SQLite) — local preference store
└── Intent Vector — output (no PII)

SERVER-SIDE:
├── Claude API (claude-sonnet-4-6) — offer generation + GenUI
│   └── OR Qwen3-35B-A3B if self-hosted (open license)
├── Context aggregation (weather, Payone, places, events)
└── Offer ranking + anti-spam enforcement

GDPR BOUNDARY: Intent vector only crosses this line
```

### What to Actually Build for Hackathon

Real on-device LLM in 24h is possible but risky. **Recommended approach:**

**Option A (if time allows): Google AI Edge + FunctionGemma**
- Download Google AI Edge Gallery Android/iOS app
- Use MediaPipe LLM Inference API in Expo via native module
- Show FunctionGemma running: Privacy Pulse displays "FunctionGemma: intent computed on-device"
- ~4 hours setup time

**Option B (faster): transformers.js in React Native**
- Qwen3-1.7B or a smaller classification model
- Use ONNX runtime for mobile
- More flexible but less "native" story
- ~2-3 hours setup

**Option C (MVP fallback): Heuristic rules + label it**
- Call it "our lightweight intent classification layer" not "LLM"
- Present the FunctionGemma/Gemma 3n architecture as the production design
- Say: "For this demo we're running a heuristic implementation; production deploys FunctionGemma via Google AI Edge."
- Completely honest, much faster to build

**Current decision:** We're building Option C for the demo (honest framing, no LLM risk), with the SQLite KG as the preference layer. The KG is NOT optional — see the revised implementation plan below.

---

## Part 3: The Air Canada Lesson — Liability Architecture

### What Happened

Air Canada's chatbot told a customer he could get a bereavement refund within 90 days. Customer booked flights based on this. Chatbot was wrong. Air Canada argued the chatbot was a "separate legal entity." Judge said: **if your AI says it, you own it. The company is responsible for everything on its website or app, regardless of whether it comes from a human or a model.**

### Why This Is Directly Relevant to Spark

Every generated offer is a commercial promise. When Spark says "15% off at Café Römer, valid 20 minutes" — that is Spark (and through Spark, DSV Gruppe) making a commitment to the user.

If the merchant rejects the QR → user was misled → liability.
If the LLM hallucinates "20% off" when merchant capped at 15% → merchant refuses → liability.
If the offer says "vegan-friendly" and the user is allergic → health liability.
If the offer generates an incorrect expiry time → user arrives after close → liability.

**And here's the twist for a German savings bank hackathon:** the judges KNOW this case. German financial regulators are extremely sensitive to AI liability. Showing that you've thought about this is a signal of maturity that no other team will demonstrate.

### The Solution: Hard Rails on Business-Critical Values

The Reddit thread's key insight: "Forcing policy answers to come from approved source material instead of freehand generation." Applied to Spark:

**What the LLM is allowed to generate (soft values):**
- Headline text (marketing copy)
- Subtext framing
- Emotional tone
- GenUI parameters (colors, typography weight, animation type)
- CTA phrasing
- Urgency language

**What the LLM is NEVER allowed to generate (hard values — always sourced from DB):**
- Discount percentage → always from `merchant.rules.max_discount` (server-enforced cap)
- Merchant name → always from `merchant.name` in DB
- Offer expiry time → always from `composite_state.timestamp + merchant.rules.valid_window_min`
- Distance to merchant → always from real-time calculation
- Any allergen, dietary, or health claims → merchant-submitted data only, LLM forbidden from adding

```python
def enforce_hard_rails(llm_output, merchant_rules, composite_state):
    """Override any LLM-generated business-critical values with ground truth."""
    
    offer = llm_output.copy()
    
    # Hard cap: discount cannot exceed merchant's configured maximum
    offer["discount"]["value"] = min(
        llm_output["discount"]["value"],
        merchant_rules.max_discount_pct
    )
    
    # Override: merchant name from DB, never from LLM
    offer["merchant_name"] = merchant_db.get(merchant_rules.merchant_id).name
    
    # Override: expiry always computed server-side
    offer["expires_at"] = (
        composite_state.timestamp 
        + timedelta(minutes=merchant_rules.valid_window_min)
    ).isoformat()
    
    # Safety check: remove any allergen/health claims if present
    offer["content"] = strip_health_claims(offer["content"])
    
    return offer
```

**The system prompt addition:**
```
CRITICAL CONSTRAINTS:
- Do NOT generate specific discount percentages. Use placeholder [DISCOUNT]%.
- Do NOT generate merchant names. Use placeholder [MERCHANT_NAME].
- Do NOT make any claims about allergens, dietary suitability, or health.
- Do NOT generate specific times or expiry durations.
All business-critical values will be injected server-side from verified sources.
```

### The Audit Trail (Legal Evidence Layer)

From the Reddit thread: *"You need technical evidence that the system was operating within defined parameters. An acceptable use policy in an internal doc doesn't count."*

Every generated offer must be logged with:

```python
offer_log = {
    "offer_id": offer.id,
    "generated_at": timestamp,
    "merchant_rules_snapshot": merchant_rules.to_dict(),  # Snapshot at generation time
    "composite_state_hash": hash(composite_state),        # Full state verifiable
    "llm_raw_output": llm_output_before_rails,            # What model actually said
    "rails_enforced": diff(llm_output_before_rails, final_offer),  # Changes made
    "final_offer": final_offer,                           # What user received
    "delivered_at": delivery_timestamp,
    "user_action": None,                                  # Updated on accept/decline
    "redeemed_at": None,                                  # Updated on redemption
}
```

This log is the legal audit trail. If a user disputes an offer, you can show exactly: what the model generated, what was overridden by the hard rails, and what the user actually received.

**In the pitch:** 
> "Every Spark offer is generated with hard schema constraints — discount amounts, merchant names, and expiry times are always sourced from our verified merchant rules database, never from the language model. Business-critical values cannot be hallucinated. And every offer is logged with a full audit trail that satisfies the evidentiary standard established by the Air Canada case. This is how you deploy AI in financial services."

That's a sentence that will make a DSV Gruppe legal team stand up.

### Pre-Flight Validation (User Protection)

Before the user sees the "Grab it now" CTA, a silent pre-flight call verifies with the merchant backend that the offer is still valid:

```
User receives offer card
        │
        ▼
[Invisible pre-flight: validate_offer_still_active(offer_id)]
        │
        ├──► Active ──► Show CTA "Grab it now" (normal)
        │
        └──► Expired/rejected ──► Card auto-fades: 
                                  "This moment just passed — we'll find you another."
                                  (No broken state, no user frustration)
```

The user never sees an offer that the merchant has since rejected. No walking 200m for nothing. This is the UX corollary to the liability architecture.

---

## How All Three Connect: The Architecture Statement

> Spark's on-device layer runs a lightweight intent model (FunctionGemma / Qwen3) that queries a local user knowledge graph to derive conditional preferences — all without any personal data leaving the device. The intent vector that reaches our servers is abstract and non-linkable. Server-side, Claude generates the offer framing and GenUI parameters, but all business-critical values (discount, merchant, expiry) are sourced from our verified merchant rules database and injected post-generation. Every offer is logged with a complete audit trail. This is a system designed to be trusted — by users, by merchants, by regulators, and by courts.

That's the sentence you say at the end of the technical section of your pitch. No other team in this hackathon will have thought at this depth about what it means to deploy AI offers in a financial services context.

---

## Hackathon Implementation Priority

The Knowledge Graph is being built. With 4 devs + AI assistance, it's doable — the schema is straightforward SQLite, the traversal logic is ~100 lines of Python, and the payoff in the demo is real (social mode toggle, conditional preference inference, GDPR Article 22 compliance story). Don't treat this as optional.

### KG Build Plan (~4.5 hours, one dev)

| Step | What | Time |
|------|------|------|
| 1 | Create SQLite schema (nodes + edges tables, indices) | 30 min |
| 2 | Seed with realistic demo data (5 merchants, 10 attributes, user edges) | 30 min |
| 3 | Implement `query_intent()` graph traversal | 1 hour |
| 4 | Implement `update_on_accept()` and `update_on_decline()` weight updates | 1 hour |
| 5 | Wire social mode toggle → temporary session edge (SEEKS Lively, expires=session_end) | 30 min |
| 6 | Hook `query_intent()` output into intent vector construction | 1 hour |

Total: 4.5 hours. One dev. No exotic dependencies — just Python + SQLite.

### Full Component Priorities

| Component | Build Time | Owner | Impact |
|-----------|-----------|-------|--------|
| Payone synthetic data + density signal | 2-3 hours | Finn | Critical — the core signal |
| Conflict resolution rule engine | 2 hours | Finn | Critical — the smart logic |
| Hard rails enforcement (discount cap) | 1 hour | Finn | Critical — liability protection |
| Offer audit log | 1 hour | Finn | Strong — maturity signal to judges |
| KG: SQLite schema + seed data | 1 hour | Open | Strong — enables conditional prefs |
| KG: `query_intent()` traversal | 1 hour | Open | Strong — social mode feature |
| KG: preference updates on accept/decline | 1 hour | Open | Good — live learning in demo |
| KG: social mode session toggle | 30 min | Open | Good — directly wows judges |
| Pre-flight offer validation | 30 min | Open | Polish — no broken UX |
| Heuristic on-device intent (Option C) | 0 hours | — | No risk, honest |
| FunctionGemma/Qwen3 on-device (Option A/B) | 2-4 hours | If time | High reward if you have time |

**Bottom line:** Hard rails + audit log first (non-negotiable, 2h). KG next (4.5h, one dev, do it). On-device LLM: Option C for MVP with architecture story; upgrade if time allows after everything else is working.
