# 03 — Context Sensing Engine

## The Core Idea: Composite Context State

Individual signals are weak. A rainy day doesn't tell you much. A quiet café doesn't tell you much. But `rain + quiet café + user walking slowly + lunchtime` = near-certainty of a warm-drink moment.

The Context Engine's job is to **combine signals into a composite state that has semantic meaning** — a state that a human would recognize as an obvious opportunity.

---

## Signal Categories

### Category 1: Environmental (Weather / Conditions)

**Primary source:** OpenWeatherMap API (Stuttgart: city_id 2825297) / DWD as fallback

| Signal | What we extract | Semantic meaning |
|--------|----------------|-----------------|
| Temperature (°C) | Raw + "feels like" | < 12° = warmth_seeking |
| Weather condition | Rain, sun, clouds, snow | Rain = indoor preference |
| UV Index | 0–11 scale | High = ice cream / shade seeking |
| Humidity | % | High humidity + heat = cold drink |
| Wind speed | m/s | High wind = shelter seeking |
| Precipitation | mm/h | Any = indoor preference |

**Composite outputs:**
- `weather_need`: `warmth_seeking` | `refreshment_seeking` | `shelter_seeking` | `neutral`
- `vibe_signal`: `cozy` | `energetic` | `refreshing` | `neutral`

**Stuttgart note:** Stuttgart is famously rainy and cold in spring — this signal fires often and meaningfully.

---

### Category 2: Merchant Demand (Payone Transaction Density) ⭐

**This is the most important signal. It is the DSV asset.**

**Source:** Simulated Payone feed (Python generator for MVP; real Payone API in production)

**How it works:**
- For each registered merchant, we maintain a rolling 4-week transaction history by hour-of-week (168 buckets)
- Current transaction rate (transactions / last 60 min) compared to historical average for this hour-of-week
- Drop > 30% = "quiet" | Drop > 50% = "unusually quiet" | Drop > 70% = "flash sale trigger"

```python
def compute_density_signal(merchant_id, current_hour_of_week):
    historical_avg = db.get_avg_txn_rate(merchant_id, current_hour_of_week)
    current_rate = payone_feed.get_recent_rate(merchant_id, window_min=60)
    drop_pct = (historical_avg - current_rate) / historical_avg
    
    return {
        "density_score": current_rate / historical_avg,  # 0–1, lower = quieter
        "drop_pct": drop_pct,
        "label": classify_drop(drop_pct),  # "quiet" | "unusually quiet" | "flash"
        "trigger": drop_pct > 0.30
    }
```

**Answer to open question "Wenn Transaction → gegangen oder gekommen?":**
Neither direction matters. We track **volume per time window vs. historical baseline** for that merchant at that hour-of-week. A transaction means "someone was served." Low volume = merchant is underperforming. The direction of individual cash flows is irrelevant to quiet-period detection.

**Simulated Payone Data Schema:**
```json
{
  "merchant_id": "cafe-roemer-stgt-001",
  "timestamp": "2025-04-25T12:47:00Z",
  "amount_eur": 4.50,
  "category": "cafe",
  "grid_cell": "STR-MITTE-047"
}
```

**Synthetic data generation:** Use realistic patterns:
- Morning rush: 08:00–09:30 (high volume)
- Mid-morning dip: 10:00–11:30 (medium)
- Lunch peak: 12:00–13:30 (high)
- **Afternoon lull: 14:30–16:00 (LOW — prime trigger time)**
- Late afternoon: 16:00–17:30 (medium)
- Evening: varies by merchant type

Add Gaussian noise + day-of-week variation (Monday different from Saturday). This produces believable historical data that makes the quiet-period detection impressive in a demo.

---

### Category 3: User Mobility (Intent Classification)

**Source:** On-device IMU (stays on device) → classified output sent as intent vector

| Signal | How measured | What it means |
|--------|-------------|---------------|
| Walking cadence | Step frequency + regularity | Slow/irregular = browsing |
| Walking speed | Step length × cadence | <3 km/h = browsing |
| Dwell time | GPS stability near POI | >45s near shop = decision moment |
| Direction consistency | Path straightness | Zigzag = exploring |
| Device orientation | Tilted = looking at something | Tilt + dwell = window shopping |

**Movement states:**
- `commuting` — fast, rhythmic, directional → **do NOT send offer** (respect attention)
- `browsing` — slow, irregular, non-directional → **prime offer moment**
- `stationary` — stopped for > 2 min → **offer if dwell near merchant**
- `transit_waiting` — at a transit stop → **perfect for transit-delay offers**

**The "browsing" detection directly maps to the Mia persona** in the challenge brief: *"It knows Mia has stopped twice in the last ten minutes and is moving slowly — the behavioural signature of someone browsing, not commuting."*

**Other mobility signals:**
- Battery < 20% → prioritize "places with free charging" offers
- WiFi SSID density (count of detected networks) → high density = dense retail corridor = higher relevance score

---

### Category 4: Temporal Context

No API needed — pure computation, but critical for offer relevance.

| Signal | Derivation | Example meaning |
|--------|-----------|-----------------|
| Hour of day | System time | 12:47 → lunch_window |
| Day of week | System date | Tuesday → typical quiet afternoon ahead |
| Minutes to next meal time | Heuristic | 13 min to 13:00 → lunch urgency |
| Day type | Weekday vs. weekend | Weekday = time-pressured lunch |
| Season | Month → season | April = spring, still cold in Stuttgart |

**Time buckets (localized for German market):**
- `morning_coffee`: 07:30–09:30
- `mid_morning`: 09:30–11:30
- `lunch_window`: 11:30–13:30 (critical window for cafes/restaurants)
- `afternoon_lull`: 13:30–16:00 (critical for offer triggering)
- `after_work`: 16:00–19:00
- `evening`: 19:00–22:00
- `late_night`: 22:00+

---

### Category 5: Local Events (Demand Spikes & Opportunities)

**Sources:** Luma API, Meetup, Eventbrite, (VVS/DB transit for event crowds)

**Why events matter:**
- Pre-event: user hungry/thirsty, time-constrained, near event venue
- Post-event: crowd dispersing, mood elevated (win = celebratory offers), mood frustrated (loss = consolation offers — bold!)
- Hackathon-specific: tonight the hackathon IS the event. Demo this live.

**Stuttgart-specific events to track:**
- Wasen / Volksfest (massive demand spikes in Oct)
- VfB Stuttgart home games (Cannstatter Wasen area)
- Schlossplatz events (outdoor concerts, markets)
- Luma tech meetups (audience matches Spark's early adopters)

**Luma API integration:**
- Pull events within 2km of user's grid cell for the next 8 hours
- Extract: event_type, expected_attendance, start_time, location
- Map to demand signal: "concert starts 19:30, user is 300m away at 18:45 → pre-event food window"

---

### Category 6: Stuttgart-Specific Signals (Hyper-Local Advantage)

These are Stuttgart-only signals that make the hackathon demo immediately relatable to local judges:

**VVS / Deutsche Bahn Integration:**
- VVS API (Verkehrsverbund Stuttgart) provides real-time departure info
- Detect: is user at or near a VVS stop? Is there a delay?
- `"U14 Richtung Heslach: 9 Minuten Verspätung"` → trigger comfort offer for nearest café to that stop
- This is THE killer demo scenario: transit delay → warm drink offer → immediate relevance
- DB Open Data API: `https://apis.deutschebahn.com/db-api-marketplace/apis/fahrplan`

**Stuttgart Specific Merchants to Pre-Register:**
- Markthalle Stuttgart (indoor market — hyper-local)
- Cafés around Königsstraße (main pedestrian zone — highest foot traffic)
- Bars/cafés near the Hackathon venue itself

**Stuttgart Calendar awareness:**
- Is it during Wasen? Adjust all offers to align with festive mood
- Is it Christmas market season? High foot traffic, cold weather → cozy offers spike in value

---

### Category 7: Personal Context (Google Calendar Integration)

**Why keep Calendar:** This is a genuine differentiator for hyper-personalization.

**Integration:**
- Google Calendar API (read-only, on-device processing)
- Extract: next meeting in < 90 min? → "you have 50 minutes before your 14:00" → offer timed to the gap
- Back-to-back meetings? → different offer than free afternoon
- Meeting location? → offer near that location

**Example composite states enabled by Calendar:**
- `"Meeting in 45 min + nearby café quiet + lunch window"` → "Quick lunch break: [café name], 200m, ready in 5 min"
- `"Just finished last meeting at 17:30 + warm evening + bar near office quiet"` → "Team drinks time? [bar] has 3 spots"

**GDPR note:** Calendar data processed entirely on-device. Only the time-bucket signal (e.g., `"meeting_gap_45min"`) included in intent vector. No meeting titles or participants ever leave the device.

---

### Category 8: Preference & Learning Signals (On-Device ML)

**Source:** Local interaction history (on-device SQLite)

| Signal | How collected | Effect on offers |
|--------|-------------|-----------------|
| Accepted categories | Past accepted offers | Boost same category |
| Declined categories | Declined offers | Reduce or filter |
| Price tier sensitivity | Accepted discount % | Calibrate discount level |
| Social preference | User setting + inferred | Busy vs. quiet venues |
| Dietary / allergen | User explicit input | Filter incompatible offers |
| Preferred vibes | Accept patterns by context | "always accepts cozy offers when cold" |

**The "always oat milk" example from Gemini chat:** If the user has accepted 3 coffee offers where oat milk is mentioned, the GenUI prompt explicitly includes "user prefers oat milk" → the generated card shows an oat latte image and says "Oat Flat White." This is visible personalization that feels magical.

**Social preference learning:**
- User explicitly says "I want to meet people tonight" → flag `social_preference: social` → prioritize busier venues, events, shared spaces
- User explicitly says "I want to chill" → `social_preference: quiet` → quiet café with few people
- Learned over time: do they accept offers for loud bars or quiet spots?

---

## The Composite State Machine

The core algorithm. All signals feed into a state vector; the state machine produces a trigger decision and context summary for the generative engine.

```python
class CompositeContextState:
    def compute(self, intent_vector, collected_signals):
        state = {
            "weather": self.classify_weather(collected_signals.weather),
            "demand": self.classify_demand(collected_signals.payone),
            "mobility": intent_vector.movement_mode,
            "temporal": self.classify_temporal(datetime.now()),
            "events": self.classify_events(collected_signals.events),
            "transit": self.classify_transit(collected_signals.vvs),
            "preferences": self.extract_preferences(intent_vector),
        }
        
        # Trigger decision
        state["should_offer"] = (
            state["mobility"] != "commuting"            # Not interrupting commute
            and state["demand"]["trigger"]              # Merchant is quiet
            and state["temporal"]["in_offer_window"]    # Reasonable time of day
            and not state["transit"]["delay_active"]    # (or: yes if delay = special case)
        )
        
        # Context summary for LLM
        state["context_summary"] = self.summarize_for_llm(state)
        
        return state
```

**Example composite states and their natural language summaries:**

| State | Natural language summary |
|-------|------------------------|
| Rain + browsing + café quiet + lunch | "Cold, rainy Tuesday lunch. User browsing slowly. Café Römer is 75% quieter than usual." |
| VVS delay + stationary at stop + afternoon | "User waiting at U14 stop, 9-minute delay. Nearby café is quiet." |
| Sunny + post-workout (Google Health) + thirsty signal | "User finished workout. Warm, high UV. Juice bar 150m away is quiet." |
| Evening + Luma event nearby + social preference | "Hackathon event 200m away in 30 min. User's movement suggests heading that direction." |
| Calendar gap + bakery inventory signal + afternoon | "User has 45-min gap before next meeting. Bakery 120m away has fresh pastries and is quiet." |

---

## Demand Prediction (Forward-Looking Signal)

Not just "merchant is quiet NOW" but "we predict they will be quiet in 45 minutes."

**Why this matters:** If the user is 10 minutes walk away and we know the café will hit its lull at 14:30, we can send the offer at 14:20 so the user *arrives* when the café is at peak quietness and the offer is most appreciated.

**Method (simple for MVP):**
- Historical Payone pattern for this merchant + day-of-week → predict next quiet window
- If quiet window starts in < 30 min and user is within walking distance → pre-emptive offer

**In the pitch:** Call this "anticipatory demand matching" — we send the offer *before* the lull fully hits, turning prediction into action. This is the Amazon "anticipatory shipping" equivalent for local retail.
