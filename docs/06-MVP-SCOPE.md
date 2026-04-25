# 06 — MVP Scope & Hackathon Build Plan

## The Core Principle: Close the Loop First

A partial but connected flow beats a polished stub. Every build decision should be made through the lens of: **does this help close the loop?**

The loop is: `context detection → composite state → offer generation → display → accept → QR redemption → merchant sees it`

If a feature doesn't directly contribute to closing this loop, it's post-hackathon.

---

## What We're Building (In Priority Order)

### ✅ MUST HAVE (loop closure)

**1. Simulated Payone Feed**
- Python generator that produces realistic transaction patterns for 5-10 Stuttgart merchants
- Patterns: morning rush, lunch peak, **afternoon lull (the trigger window)**, evening
- Gaussian noise + day-of-week variation
- Schema: `{merchant_id, timestamp, amount_eur, category, grid_cell}`
- Endpoint: `GET /api/payone/density/{merchant_id}` → returns density score + label
- Time to build: ~2 hours

**2. OpenWeatherMap Integration**
- Stuttgart weather (city_id: 2825297) pulled every 5 minutes
- Extract: temp, feels_like, condition, weather_need classification
- Endpoint: `GET /api/context/weather/{grid_cell}`
- Time to build: ~1 hour

**3. Composite Context State Builder**
- Combines intent_vector (from mobile) + weather + Payone density + time bucket
- Outputs: `composite_state` object with context summary for LLM
- Endpoint: `POST /api/context/composite` (input: intent_vector, output: composite_state)
- Time to build: ~3 hours

**4. Offer Generation (Claude API)**
- System prompt + dynamic user prompt built from composite state
- Structured JSON output: offer content + GenUI parameters
- Endpoint: `POST /api/offers/generate` (input: composite_state, merchant_id)
- Time to build: ~2 hours

**5. Consumer Mobile App (Expo)**
- IMU → movement mode classification (slow/fast/stationary)
- GPS → quantized grid cell
- Intent vector construction + sending to backend
- Offer card display: GenUI rendering (dynamic colors, imagery, text)
- Accept button → QR token display
- Privacy Pulse indicator
- Time to build: ~6 hours

**6. QR Redemption**
- Token generation on accept: UUID + merchant_id + expiry
- QR code rendered in consumer app
- Merchant validation endpoint: `POST /api/redemption/validate`
- Cashback "Spark" animation on confirmation
- Time to build: ~2 hours

**7. Merchant Dashboard (Next.js) — minimum viable**
- Payone Pulse chart (line chart: current rate vs. historical avg)
- Quiet period detection notification
- Rule engine form (discount %, trigger threshold, offer tone)
- Offer history feed (what was generated, what was accepted)
- Time to build: ~5 hours

**Total must-have: ~21 hours**

---

### 🟡 SHOULD HAVE (differentiation)

**8. Google Places Integration**
- Nearby merchant search (radius 500m from grid cell)
- Merchant details: name, category, rating, address
- Popular times data (supplements Payone for early merchants)
- Time to build: ~2 hours

**9. Luma Events Integration**
- Stuttgart events for tonight
- Event type → demand signal → offer context enrichment
- The "Hackathon Night" scenario: pull the actual event happening tonight
- Time to build: ~2 hours (or 1 if Luma has clean public API)

**10. GenUI Vibe-Shifting (Context Slider)**
- Debug panel showing context sliders (weather ☀️→🌧️, merchant busy→quiet)
- Real-time card re-generation as sliders change
- This is THE demo moment that proves GenUI vs. templates
- Time to build: ~3 hours

**11. Inventory / Capacity Input (Merchant)**
- Simple form: "How many seats available?" + "Surplus items?"
- Passed to offer generation context
- Time to build: ~2 hours

**12. Preference Learning (Basic)**
- On-device: store accepted/declined offers in AsyncStorage
- Weight adjustment on accept/decline
- Pass inferred preferences in intent vector
- Time to build: ~2 hours

**Total should-have: ~11 hours**

---

### 🔵 NICE TO HAVE (wow factors, add if time allows)

**13. VVS / DB Transit Delay**
- VVS API for Stuttgart: check if any U-Bahn/S-Bahn line near user has delay
- If delay > 5 min + user at stop → trigger "waiting room" offer
- The single most Stuttgart-specific feature
- Time to build: ~2 hours

**14. Google Calendar Gap Detection**
- On-device: next meeting time from Calendar API
- Compute gap: "you have 45 minutes before 14:00"
- Add to intent vector: `meeting_gap_min: 45`
- Time to build: ~2 hours

**15. Merchant Analytics Advanced**
- Revenue delta calculation ("€34.50 recovered from quiet periods")
- Community Hero Score
- Acceptance rate by offer type
- Time to build: ~2 hours

**16. Apify Google Maps Merchant Validation**
- For merchant registration: validate business exists
- Pre-seed Stuttgart merchant database
- Time to build: ~2 hours (scraper) + ~1 hour (integration)

**Total nice-to-have: ~9 hours**

---

### ❌ CUT FOR MVP

| Feature | Why Cut |
|---------|---------|
| Microphone / ambient audio | GDPR red flag, complex, judges will question it |
| Google Health API | Deep permissions, complex, not core to loop |
| ElevenLabs voice calls | Cool but zero connection to core loop |
| Meetup / Eventbrite | Luma alone is enough for tonight's demo |
| OSM inclination data | Fun idea, marginal relevance, build time |
| Competitor density mapping | Interesting but not required for loop |
| Real ML model training | Use Bayesian heuristics that look like ML |
| Multi-city support (more than Stuttgart) | Config exists, but one city for demo |

---

## Tech Stack Decision

### Mobile: Expo (React Native)
- Cross-platform (demo on iOS or Android)
- Expo Sensors API for IMU/accelerometer
- Expo Location API for GPS
- AsyncStorage for preference store
- React Native QR code library for redemption
- Expo Notifications for push

### Backend: FastAPI (Python)
- Fast to build, async, great for ML-adjacent code
- Pydantic models for request/response validation
- SQLite (hackathon) → PostgreSQL (production)
- Redis for context caching (optional, simplify to in-memory for MVP)

### Merchant Dashboard: Next.js
- Recharts or Chart.js for Payone Pulse visualization
- Tailwind CSS
- Mapbox for merchant map (optional — can skip for MVP)
- Deployed: Vercel (instant)

### AI: Claude API (claude-sonnet-4-6)
- Offer generation with structured JSON output
- Fast, reliable, handles the prompt complexity well
- Anthropic SDK for Python

### External APIs
- OpenWeatherMap (free tier: sufficient)
- Google Places API (free tier: 28,500 requests/month — sufficient)
- Luma: check if public API exists, otherwise use their embed/scraping
- VVS / DB API: Deutsche Bahn Open Data Portal

---

## Simulated Payone Data Generation

```python
import numpy as np
from datetime import datetime, timedelta
import json

def generate_payone_history(merchant_id, days=28):
    """Generate 4 weeks of realistic transaction history."""
    
    # Base hourly rates by type
    base_rates = {
        "cafe": [0, 0, 0, 0, 0, 0, 0, 2, 8, 6, 4, 3, 10, 12, 8, 5, 4, 3, 2, 2, 1, 0, 0, 0],
        "restaurant": [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 6, 14, 15, 8, 4, 3, 5, 10, 12, 8, 4, 1, 0],
        "bar": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 3, 2, 2, 3, 5, 8, 12, 15, 18, 14, 8],
    }
    
    # Day-of-week multipliers (0=Mon, 6=Sun)
    day_multipliers = [0.8, 0.85, 0.9, 0.85, 1.1, 1.4, 1.2]
    
    category = merchant_db.get_category(merchant_id)
    hourly = base_rates.get(category, base_rates["cafe"])
    
    transactions = []
    start = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        current = start + timedelta(days=day)
        dow = current.weekday()
        multiplier = day_multipliers[dow]
        
        for hour in range(24):
            rate = hourly[hour] * multiplier
            # Gaussian noise
            actual = max(0, np.random.poisson(rate))
            
            for _ in range(actual):
                minute = np.random.randint(0, 60)
                amount = np.random.normal(
                    loc=get_avg_amount(category), 
                    scale=get_std_amount(category)
                )
                transactions.append({
                    "merchant_id": merchant_id,
                    "timestamp": current.replace(hour=hour, minute=minute).isoformat(),
                    "amount_eur": round(max(1.5, amount), 2),
                    "category": category,
                })
    
    return sorted(transactions, key=lambda x: x["timestamp"])
```

This produces data that, when visualized, clearly shows the afternoon lull — the primary demo trigger.

---

## Stuttgart Focus — Pre-Registered Merchants

Seed these for the demo. Use Apify / Google Places to get real data:

1. **Café Königsbau** — Königstr. 40, Stuttgart (city center, high foot traffic)
2. **Konditorei Marquardt** — Schillerplatz 1 (historic, cozy, perfect for "warm up" offers)
3. **Bäckerei Wolf** — multiple locations (bakery with end-of-day inventory angle)
4. **Bar Unter Stuttgart** — near Schlossplatz (evening offers)
5. **Salon für Haare** — (any midweek appointment gap scenario)

Pre-generate 28 days of Payone-style data for each. Set Thursday 14:30 as the demo "trigger time."

---

## Build Timeline (Suggested 24h Sprint)

| Hours | Focus |
|-------|-------|
| 0–3 | Backend setup: FastAPI skeleton, Payone generator, DB schema |
| 3–5 | Context APIs: OpenWeatherMap + Places integration |
| 5–8 | Composite state builder + Claude offer generation |
| 8–13 | Consumer app: Expo setup, IMU, GPS, intent vector, offer card display |
| 13–16 | QR redemption flow + Spark cashback animation |
| 16–19 | Merchant dashboard: Payone pulse + rule engine |
| 19–21 | Luma integration + VVS transit (if time) |
| 21–23 | GenUI context slider demo panel |
| 23–24 | Demo rehearsal + bug fixes |

---

## Demo Hardware

- Phone 1 (Lars or teammate): Consumer app ("Mia's phone")
- Laptop: Merchant dashboard + backend logs visible
- Optional: tablet showing Privacy Ledger / context state in real time

**Pro move:** Show both screens simultaneously side by side during the end-to-end loop. Merchant pulse → offer generated → consumer receives it. Split-screen = one shot, full loop.
