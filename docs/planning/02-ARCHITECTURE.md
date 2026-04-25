# 02 — System Architecture

**Runtime add-on:** an optional **Neo4j user knowledge graph** on the Spark backend (session preferences, offer lifecycle, deterministic pre-LLM rules, explainability) is described in **[`../NEO4J-GRAPH.md`](../NEO4J-GRAPH.md)**. The diagram below is the original privacy boundary; the graph augments the backend box when enabled.

## Overview: Privacy-First, Context-Driven

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER'S DEVICE (On-Device)                     │
│                                                                   │
│  GPS (quantized)  ──┐                                            │
│  IMU / Pedometer  ──┤──► Local Intent Engine ──► Intent Vector   │
│  User History DB  ──┘   (Phi-3 / rule model)       │            │
│                                                     │            │
│  ← Nothing personal leaves this boundary ──────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │ Intent Vector (no PII)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SPARK CLOUD BACKEND                           │
│                                                                   │
│  Context Aggregator                                              │
│  ├── OpenWeatherMap (Stuttgart)                                  │
│  ├── Payone Simulated Feed (merchant density)                    │
│  ├── Google Places API (merchant proximity + busyness)           │
│  ├── Luma Events API (tonight's local events)                    │
│  └── VVS / DB API (Stuttgart transit delays)                     │
│                              │                                   │
│                              ▼                                   │
│            Composite Context State Builder                       │
│                              │                                   │
│                              ▼                                   │
│          ┌────────────────────────────────┐                      │
│          │   AI Offer Generation Agent    │                      │
│          │   (Gemini Flash — JSON mode)   │                      │
│          │   - generates offer content    │                      │
│          │   - generates GenUI parameters │                      │
│          │   - validates GDPR compliance  │                      │
│          └────────────────────────────────┘                      │
│                              │                                   │
│                              ▼                                   │
│           Offer Object + GenUI Spec ──► Push to Device           │
│                                                                   │
│  Merchant Registry DB                                            │
│  Payone Simulation Engine                                        │
│  Analytics Store (aggregate, anonymized)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  MERCHANT DASHBOARD (Next.js)                    │
│  - Rule engine (set discount %, trigger conditions)              │
│  - Inventory input (stock levels, available capacity)            │
│  - Real-time Payone pulse visualization                         │
│  - Offer performance analytics                                   │
│  - Registration & Google Maps listing validation                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## On-Device Layer: What Stays Local

### Purpose
Protect user PII. Comply with GDPR. Demonstrate Sparkasse-level trust.

### Components

**1. GPS Quantizer**
- Raw GPS coordinates never leave the device
- Quantized to a ~50m grid cell (e.g., `"STR-MITTE-047"`)
- Grid cell is what reaches the server — not coordinates

**2. IMU / Motion Classifier**
- Uses phone accelerometer + gyroscope
- Classifies movement into: `commuting` | `browsing` | `stationary`
- Cadence analysis: slow irregular steps = browsing, fast rhythmic = commuting
- If commuting: no offer triggered (respect user's attention)
- Also: dwell time — if user is stationary near a merchant window > 45s = "decision moment"

**3. Local Intent Engine**
- Lightweight model (Phi-3 / transformers.js or heuristic for MVP)
- Inputs: movement state, time of day, day of week, recent interaction history, device battery
- Outputs: Intent Vector (see below)
- Runs entirely on-device

**4. Local Preference Store**
- SQLite / AsyncStorage on device
- Stores: past accepted/declined offers (anonymized offer IDs), inferred preferences (warm vs cold drinks, cuisine type, price tier, social preference)
- Preference learning: accept patterns → update preference weights
- Never synced to cloud — stays on device

**5. Privacy Ledger (visible to user)**
- Visual log of what is being processed locally
- Shows the "Cloud Exit Gate" — what the intent vector contains
- The "Privacy Pulse" demo feature: green pulsing dot that expands to show on-device reasoning

---

## Intent Vector Schema

What leaves the device. No PII. No raw location.

```json
{
  "grid_cell": "STR-MITTE-047",
  "movement_mode": "browsing",
  "time_bucket": "tuesday_lunch",
  "weather_need": "warmth_seeking",
  "social_preference": "quiet",
  "price_tier": "mid",
  "recent_categories": ["coffee", "bakery"],
  "dwell_signal": false,
  "battery_low": false,
  "session_id": "anon-uuid-no-linkage"
}
```

The server never knows who this user is. It knows an anonymous intent profile.

---

## Cloud Backend: Context Aggregation

### Tech Stack
- **FastAPI** (Python) — REST API
- **Redis** — context state caching (per grid cell, TTL ~5 min)
- **PostgreSQL** — merchant registry, offer history, analytics
- **Celery** — async task queue for offer generation

### Context Signal Collectors (per grid cell, runs on schedule + on-demand)

```python
# Each is a configurable plugin — "different city or data source slots in as configuration"
collectors = [
    WeatherCollector(api="openweathermap", city="Stuttgart"),
    PayoneCollector(feed="simulated", merchants_in_cell=True),
    PlacesCollector(api="google_places", radius_m=500),
    EventsCollector(api="luma", city="Stuttgart"),
    TransitCollector(api="vvs", stations_in_cell=True),
]
```

### Composite Context State

The state machine output for a given (grid_cell, timestamp, intent_vector):

```json
{
  "weather": {
    "condition": "overcast",
    "temp_c": 11,
    "feel": "cold",
    "need": "warmth_seeking"
  },
  "merchant_demand": {
    "nearest_quiet_merchants": [
      {
        "id": "cafe-roemer-stgt",
        "name": "Café Römer",
        "category": "cafe",
        "distance_m": 80,
        "payone_density_score": 0.28,
        "density_label": "unusually quiet",
        "current_txn_rate": 3,
        "historical_avg_rate": 12,
        "drop_pct": 75
      }
    ]
  },
  "user_state": {
    "movement_mode": "browsing",
    "weather_need": "warmth_seeking",
    "social_preference": "quiet",
    "price_tier": "mid"
  },
  "temporal": {
    "time": "12:47",
    "day": "tuesday",
    "bucket": "lunch_window",
    "minutes_to_next_transit": 14
  },
  "events": {
    "nearby_tonight": ["Hackathon Night Stuttgart — 200m"],
    "event_type": "tech"
  },
  "transit": {
    "delay_active": false,
    "delay_line": null,
    "delay_minutes": null
  }
}
```

---

## AI Offer Generation Agent

### Architecture: Agentic System with Tools

The offer generation is not a single LLM call. It's an agent with tools:

```python
tools = [
    get_composite_context(grid_cell, intent_vector),  # Pulls state above
    get_merchant_details(merchant_id),                 # Full merchant info
    get_user_preferences(session_id),                  # From intent vector
    check_merchant_rules(merchant_id),                 # Discount limits, blackout periods
    generate_offer_object(context, preferences, rules), # Gemini Flash API call
    validate_gdpr_compliance(offer),                   # No PII in offer
    generate_genui_spec(offer, context),               # Visual parameters
    push_to_user(session_id, offer),                   # Delivery
]
```

Why agents matter for the pitch: this is not "we call GPT and show the output." It's an orchestrated system where AI tools coordinate to produce a compliant, contextually valid, merchant-approved offer. That's a real architecture.

### Offer Generation Prompt Structure

System prompt sets: brand voice (warm, direct, local), GDPR constraints, output schema.

User prompt contains: composite context state + merchant rules + user preference profile.

Output: structured offer object (see `04-GENERATIVE-ENGINE.md`).

---

## Merchant Dashboard

**Tech:** Next.js + Tailwind CSS + Mapbox

Two core views:

### 1. Merchant Command Center
- Real-time "Payone Pulse" — line chart showing transaction density vs. historical average
- Quiet period detection: "Unusually quiet detected — 75% below Tuesday average"
- Offer generation status: "Generating campaign..." → "Offer sent to 3 users in range"
- Rule engine (set once, runs automatically):
  - Trigger: `density_drop > 40%`
  - Max discount: `20%`
  - Offer tone: `cozy`
  - Valid window: `60 min`
  - Blackout: never before 8am, never after 22:00

### 2. Analytics & Performance
- Acceptance rate by offer type
- Redemption conversions
- Revenue delta: "This week, quiet-period offers generated €340 in otherwise-lost revenue"
- Community Hero Score: "€1,240 kept in local economy this month"

### 3. Inventory / Capacity Input
The "TooGoodToGo Pro Max" panel:
- "Available capacity right now": toggle (+ seats, + appointment slots)
- "Surplus inventory": input (e.g., "8 croissants, best by 17:00")
- These become additional offer triggers: scarcity + sustainability framing

---

## Data Flows Summary

```
[User walks past café]
         │
         ▼
[IMU → browsing mode detected on device]
         │
         ▼
[Intent vector sent: {grid_cell, browsing, warmth_seeking, tuesday_lunch}]
         │
         ▼
[Cloud: context aggregator pulls weather + Payone density for grid cell]
         │
         ▼
[Composite state: overcast + café unusually quiet + user browsing + lunch window]
         │
         ▼
[AI agent: calls generate_offer_object with merchant rules (max 20% off)]
         │
         ▼
[Gemini Flash: generates offer + GenUI spec]
         │
         ▼
[Offer pushed to user device]
         │
         ▼
[User sees card: warm imagery, cozy tone, "Flat white + croissant 15% off, 80m, 12 min left"]
         │
         ▼
[User taps accept → QR token generated]
         │
         ▼
[Merchant scans / validates QR → transaction confirmed]
         │
         ▼
[Spark cashback animation → €0.80 credited to wallet]
         │
         ▼
[Analytics updated: 1 redemption, offer type A, acceptance latency 23s]
```

---

## Configurability by City

From the brief: *"A different city or data source should slot in as a configuration, not a rewrite."*

```yaml
# config/cities/stuttgart.yaml
city: Stuttgart
country: DE
timezone: Europe/Berlin
weather_api: openweathermap
weather_city_id: "2825297"
transit_api: vvs
transit_region: Stuttgart
events_api: luma
events_city_slug: stuttgart
payone_feed: simulated  # → real in production
grid_cell_size_m: 50
language: de
currency: EUR
```

Adding Munich is changing one YAML file. This is architecturally sound and shows the judges scalability.
