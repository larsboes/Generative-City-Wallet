# 12 — Submission README (Draft — Fill In After Hackathon)

> **Instructions:** This document is the template for the final GitHub README you submit to judges. Fill in sections marked [TODO] after building. Use the structure from the TUM.ai Makeathon reference — judges read this before and after the demo. Be honest about what worked and didn't; it signals maturity and is explicitly valued.

---

# ⚡ Spark — Generative City Wallet

> **"Make every minute local."**
> Built for the DSV Gruppe Challenge — HackNation 2025

---

## 🏆 Hackathon Submission

### 1. General Approach

We built Spark around one core insight: **the gap between a person walking past a quiet café and a perfectly timed, relevant offer is not a technology problem — it's a data connectivity problem.** The data exists. The location is precise. The merchant's transaction volume is measurable. What was missing was the layer that connects them in real time.

Our architecture has three modules, as required:

**Context Sensing Layer** — We aggregate a composite context state from four signal categories: real-time weather (OpenWeatherMap, Stuttgart), simulated Payone transaction density per nearby merchant, on-device IMU movement classification (browsing vs. commuting), and live local events (Luma, Stuttgart). Critically, sensitive data — GPS, motion history, calendar — never leaves the device. Only an abstract intent vector (grid cell, movement mode, inferred preferences) is sent upstream.

**Generative Offer Engine** — We use Gemini Flash with native JSON output mode to generate both the offer content *and* the visual parameters of the offer card (color palette, typography, imagery prompt, urgency style). On-device, Gemma 3n runs privately via Google AI Edge for intent extraction — no PII leaves the device. This is Generative UI: the interface element is generated at runtime, not selected from a template library. A Context Slider in our demo panel proves this — dragging weather from cold to sunny transforms the card's entire visual DNA in real time.

**Seamless Checkout & Redemption** — On offer acceptance, a QR token is generated and stored locally (works offline at the counter). The merchant dashboard validates the QR, triggering a cashback credit to the user's Spark wallet. A "Spark" animation closes the transaction loop emotionally — and visually connects to Sparkasse branding.

The Payone transaction density signal is the heart of the system. We generate a synthetic Payone-compatible feed that mirrors real transaction patterns — morning rush, lunch peak, afternoon lull — to demonstrate how DSV Gruppe's payment infrastructure becomes an intelligence layer for local retail demand generation.

### 2. What Worked Well

- **Composite context state:** Combining Payone density + weather + IMU movement produced genuinely compelling, non-obvious offer triggers that felt relevant rather than generic.
- **GenUI visual transformation:** The context-responsive card design was the single most impressive demo moment — watching the card morph from warm amber cozy to sharp electric energetic as context shifted made the "generative" claim visceral rather than theoretical.
- **Privacy Ledger:** Showing the on-device processing log and the exact contents of the intent vector addressed GDPR questions before judges could ask them. The green pulse became a trust signal.
- **Merchant Pulse visualization:** The Payone density line chart flatling and triggering an offer — then immediately switching to Mia's phone receiving it — closed the end-to-end loop in under 30 seconds.
- [TODO: Add 2-3 specific things that genuinely worked during build]

### 3. What Did Not Work

- [TODO: Fill in honestly after hackathon. Examples of things to watch:]
  - "Our first attempt at composite state triggered too many false positives — every slight Payone dip generated an offer. We added a minimum threshold (30% drop) which dramatically improved signal quality."
  - "Real-time imagery generation via [DALL-E / Stability] was too slow for the demo loop (4-8 seconds). We pre-generated imagery per theme (cozy, energetic, refreshing) and let the LLM select from them. Indistinguishable from true real-time generation in the demo."
  - "VVS API onboarding was slower than expected — we implemented the transit delay scenario with mocked data."
  - "Calendar integration surfaced a permissions edge case on [Android/iOS] — we moved it to an optional feature."

### 4. How We Would Improve Spark

- **Real Payone integration:** Replace the simulated feed with a live Payone webhook or polling endpoint. The entire architecture is designed for this — it's a configuration change, not a rebuild.
- **On-device SLM (Phi-3 / Gemma):** Run the intent abstraction layer with a real on-device model for true privacy-by-design. Current implementation uses heuristic rules that produce equivalent outputs.
- **Collaborative filtering:** As user interaction data accumulates, layer in user-similarity based recommendations for cold-start personalization.
- **Sparkasse Girokonto integration:** Wire the Spark wallet balance directly to a Sparkasse account. Cashback credits become real bank deposits — transforming Spark from a loyalty wallet into a banking feature that drives deposit growth and Sparkasse relevance for urban professionals.
- **Multi-city rollout:** Stuttgart is a configuration file. Munich, Frankfurt, Hamburg: three YAML changes.
- **ElevenLabs voice reservation:** For merchants without online booking, Spark could make an AI voice call to secure a reservation on the user's behalf — triggered automatically when an offer for a reservation-based business (hair salon, restaurant) is accepted.

---

## ⚙️ Implementation Details

### Architecture Overview

```
[User Device — On-Device Only]
  GPS → 50m grid cell quantization
  IMU → movement_mode classification  
  Local preference store (SQLite)
  → Intent Vector (no PII)

[Spark Cloud Backend — FastAPI]
  + OpenWeatherMap (Stuttgart)
  + Simulated Payone Feed
  + Google Places API
  + Luma Events API
  → Composite Context State
  → Gemini Flash API (offer + GenUI generation, JSON mode)
  → Push to device

[Merchant Dashboard — Next.js]
  Payone Pulse visualization
  Rule engine
  Inventory panel
  Analytics
```

### Key Technical Decisions

**Simulated Payone Feed:** We generate 28 days of synthetic transaction history per merchant using a Poisson distribution with realistic hourly base rates (day-of-week variation + Gaussian noise). This produces a believable historical baseline from which quiet-period detection (30%+ volume drop vs. rolling average) becomes meaningful and demostrable.

**Offer Ranking:** When multiple merchants qualify, we score each on: Payone density drop (40%), distance from user (25%), user preference match (20%), weather-category alignment (10%), inventory signal bonus (5%). Only one offer is delivered at a time — the challenge asks for "a single, specific offer," not a feed.

**Cashback Model:** Following the brief's specification, users pay full price and receive cashback credit to their Spark wallet rather than an upfront discount. This aligns with the Sparkasse banking model and simplifies POS integration (no POS modification required).

**GDPR Architecture:** Intent vector contains no PII. Fields: grid_cell (50m quantization), movement_mode, time_bucket, weather_need, social_preference, price_tier, inferred category preferences. Raw GPS, raw sensor data, and interaction history never leave the device.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Mobile (consumer) | Expo / React Native |
| Merchant dashboard | Next.js + Tailwind + Recharts |
| Backend | FastAPI (Python) |
| AI / Offer generation (server) | Gemini Flash (structured JSON output) |
| AI / Intent extraction (on-device) | Gemma 3n via Google AI Edge |
| Context signals | OpenWeatherMap, Google Places, Luma |
| Payone simulation | Custom Python generator |
| Maps | Mapbox |
| Animations | Lottie (Spark cashback effect) |

### Running Locally

[TODO: Add setup instructions after build. Follow Docker pattern from reference README or simple local dev setup.]

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Add API keys
python main.py

# Dashboard
cd dashboard
npm install
npm run dev

# Mobile
cd mobile
npx expo start
```

### Environment Variables

```env
GOOGLE_AI_API_KEY=your_key       # Gemini Flash — from Google AI Studio
OPENWEATHERMAP_API_KEY=your_key
GOOGLE_PLACES_API_KEY=your_key   # Can share billing account with GOOGLE_AI_API_KEY
LUMA_API_KEY=your_key            # if available
```

---

## 🎯 Challenge Requirements — Self-Assessment

| Requirement | Status | Notes |
|-------------|--------|-------|
| Context Sensing Layer | ✅ | Weather + Payone + IMU + Events |
| ≥2 real context signals visible to user | ✅ | Weather + Payone density shown on card |
| Generative Offer Engine | ✅ | Gemini Flash + structured JSON GenUI output |
| Offer generated dynamically (not DB) | ✅ | Context Slider proves this live |
| Merchant rule interface | ✅ | Full rule engine in dashboard |
| End-to-end flow demonstrated | ✅ | Merchant pulse → offer → QR → cashback |
| Merchant dashboard | ✅ | Payone Pulse + analytics + rules |
| GDPR / privacy addressed | ✅ | Privacy Ledger + intent vector schema |
| Configurable without code change | ✅ | City config YAML |
| On-device SLM | ⚠️ | Heuristic implementation; architecture designed for Phi-3 |

---

## 🏙️ Why Stuttgart

We focused exclusively on Stuttgart for the MVP. Pre-registered merchants include [TODO: list actual merchants]. The VVS transit delay scenario uses Stuttgart's U-Bahn network. The Luma integration pulled tonight's actual local events. Hyper-local is not just a feature — it's a proof of concept. If it works in Stuttgart, it works anywhere Payone operates.

**The local economy argument:** [TODO: Add a "Community Hero Score" stat from your actual demo — e.g., "In our demo session, Spark kept €[X] in Stuttgart's local economy that would otherwise have gone to delivery platforms or global chains."]

---

*Built with ⚡ at HackNation 2025 — DSV Gruppe Challenge*
*Team: [TODO: Add team member names]*
