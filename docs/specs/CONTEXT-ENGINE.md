# Context Sensing Engine

## Overview: Composite Contextual Awareness

The Context Engine transforms individual raw signals into a semantic **Composite Context State**. Its goal is to identify moments of high relevance by combining environmental, demand, and behavioral data.

---

## Signal Categories

### 1. Environmental (Weather & Conditions)
Extracts real-time conditions (e.g., from OpenWeatherMap) to derive "weather needs."
- **Outputs:** `warmth_seeking`, `refreshment_seeking`, `shelter_seeking`.
- **Vibe:** `cozy`, `energetic`, `refreshing`.

### 2. Merchant Demand (Transaction Density)
The primary trigger for offer generation, derived from real-time transaction volume vs. historical baselines.
- **Trigger:** Drop > 30% below historical average for the current hour-of-week.
- **Classification:** `QUIET` (30%+), `UNUSUALLY_QUIET` (50%+), `FLASH_SALE` (70%+).

### 3. User Mobility (Intent Classification)
Classifies user movement on-device using IMU and GPS sensors.
- **Modes:**
    - `BROWSING`: Prime offer moment (slow, irregular).
    - `COMMUTING`: Offer suppressed (fast, rhythmic).
    - `TRANSIT_WAITING`: Opportunity for transit-stop offers.
    - `EXERCISING`: Hard block on offers.
    - `POST_WORKOUT`: Prime window for recovery offers.

### 4. Temporal Context
Maps system time to behavioral buckets (e.g., `morning_coffee`, `lunch_window`, `afternoon_lull`, `after_work`).

### 5. Local Events
Enriches context with nearby scheduled events (e.g., concerts, sports, meetups) to anticipate demand spikes or social opportunities.

### 6. Transit Enrichment (OCR)
The user can actively provide context by scanning transit tickets or app screenshots. The system parses the departure time and train number to detect delay windows.
- **Delay Window:** If a train is delayed > 5 minutes, Spark identifies merchants within walking distance of the station where the user can wait.
- **Urgency Framing:** The system provides a "return by" countdown to ensure the user doesn't miss their recalculated departure.

---

## The Composite State Machine

All active signals are processed into a unified state vector to determine if an offer should be triggered and to provide a natural language summary for the Generative Engine.

**Example Composite States:**

| Context | Semantic Summary |
|---|---|
| Rain + Browsing + Café Quiet | "Cold, rainy Tuesday lunch. User browsing slowly. Nearby café is 70% quieter than usual." |
| Transit Delay + Stationary | "User waiting at U-Bahn stop with 10-min delay. Nearby bakery is quiet." |
| Sunny + Post-Workout | "User finished workout in warm weather. Nearby juice bar is quiet." |

---

## Anticipatory Demand Matching

The engine uses historical patterns to predict future quiet windows. If a user is 10 minutes away and a lull is predicted to hit in 15 minutes, an offer can be dispatched pre-emptively to synchronize arrival with peak merchant need.
