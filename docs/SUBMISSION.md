# 📝 Hack Nation Submission Form — Spark

*Pre-filled answers for the Hack Nation submission form. Copy-paste ready.*

---

## 🏗️ Project Basics

**Project Title:**  
Spark — The Generative City Wallet

**Event:**  
5th Hack Nation — Deadline: Apr 26, 9:00 AM ET

**Challenge:**  
Generative City-Wallet (Agentic AI & Data Engineering)

**Program Type:**  
VC Big Bets

---

## ⚡ Short Description
Spark is the generative city wallet — an on-device SLM that fuses live connector signals (weather, places, events, health, wallet history) with an integrated knowledge graph and decides on-device what to offer, when and why. Privacy-first: raw data never leaves the phone, only a 32-byte intent token; federated learning improves the global model via gradients only. Already live in market: 6 merchant partners and €104 in verified, in-store revenue redeemed by real customers in a 24-hour pilot.

---

## 📄 Structured Project Description

### 1. Problem & Challenge
Local retail is in a lost decade. Amazon reprices its catalog every minute; the café across the street uses the same paper coupon at 9am and 9pm. We call this Context Blindness: 2% redemption on local coupons, 38% revenue swings driven by weather alone, 73% of promo spend wasted. Existing loyalty apps and ad-tech retrofit privacy after the fact and still fail to react to real-world context.

### 2. Target Audience
- **Primary**: Independent local merchants in DACH (cafés, bakeries, pizzerias, boutique retail) who can't afford a data team but lose margin to context blindness.
- **Secondary**: Urban consumers (25–45) who want relevant, in-the-moment offers without surrendering their data.
- **Distribution**: Sparkasse / DSV-Gruppe customers — 50M+ banked users in DACH where a privacy-first wallet is a regulatory and trust fit.

### 3. Solution & Core Features
**SparkPulse — Sense → Generate → Redeem.**
- **Sense**: Fuse weather, location, walking speed, time, merchant demand, opt-in health & calendar signals on-device.
- **Generate**: A small language model on the phone writes one offer for this exact moment (e.g. 'drizzling, you're 4 min away, 3 empty tables — €2 off the next 20 minutes').
- **Redeem**: Tap to walk in, redeem in-store, settle through the wallet.
- **Federated Learning**: Only mathematical gradients (weights) leave the device; the global brain improves without ever seeing raw user data.
- **Pluggable Signal Sources**: OpenWeather/DWD, Google Places, OpenStreetMap, Luma events, Neo4j knowledge graph, Apple Health, Google Health Connect, Strava, first-party wallet history.

### 4. Unique Selling Proposition (USP)
The most GDPR-secure fintech wallet on the market — privacy is the architecture, not a policy page.
- **On-device SLM**: Raw signals never leave the phone (only a 32-byte intent token is sent).
- **Federated learning**: Aggregates gradients, never people.
- **Generative, single-shot offers**: No static coupon catalog, no ad-tech retargeting.
- **Sparkasse / DSV-Gruppe distribution**: Trusted local-bank rails into 50M+ DACH users, an angle no US ad-tech player can replicate.

### 5. Implementation & Technology
- **On-device SLM**: Gemma 3n via Google AI Edge for offer generation — runs locally on iOS/Android.
- **Federated learning pipeline**: Device-side gradient computation, secure aggregation server, model sync.
- **Feature vector**: Fused on-device from Context (Temp, Weather, Day, Time, User_Speed), User (Affinity, Avg_Spend, Discount_Sensitivity), and Merchant (Demand_Level, Category, Rating).
- **Knowledge graph (Neo4j)**: For merchant/place relationships and substitution.
- **Frontend**: React 18 + Vite + TypeScript + Tailwind.
- **Backend**: FastAPI + Neo4j + SQLite (Audit Trail).
- **Wire format**: 32-byte intent token; three privacy guarantees baked into the protocol.

### 6. Results & Impact
Already live, already generating real revenue — this is not a concept, it is running in market:
- **6 signed merchant partners**: Local cafés & pizzerias across Stuttgart, München and Karlsruhe live and transacting.
- **€104 in verified revenue**: Redeemed by real customers in a 24-hour window — zero marketing spend.
- **50+ trendsetter users**: Acquired purely via word of mouth.
- **Market opportunity**: €420B EU local retail TAM, €48B SAM in DACH, €1.2B SOM via Sparkasse distribution.

---

## 📈 Additional Information

### Why Now
- Cheap on-device SLMs make per-moment generation economical for the first time.
- EU enforcement (DMA, GDPR, AI Act) penalizes ad-tech retrofits and rewards privacy-by-design.
- Post-Klarna appetite in DACH for local fintech with a trust story.

### The Data Vector (on-device fusion)
```json
{
  "context":  {"temp": 11, "weather": "Rain", "day": 2, "time": "14:30", "user_speed": 0.8},
  "user":     {"affinity_coffee": 0.9, "avg_spend": 12.50, "discount_sensitivity": 0.4},
  "merchant": {"demand_level": 0.2, "category": "Cafe", "rating": 4.6}
}
```

### Federated Learning Loop
1. **Local training**: Phone runs a small model that learns the user's specific habits.
2. **Gradient upload**: Phone sends only mathematical weight adjustments, never raw data.
3. **Global aggregation**: Server combines weights from 10,000+ users to learn general truths.
4. **Model sync**: Improved global brain is pushed back to all phones.

---

## 🔗 Links

**Live Project URL:**  
[https://id-preview--32254bae-22ae-449f-9a8e-51182174199b.lovable.app](https://id-preview--32254bae-22ae-449f-9a8e-51182174199b.lovable.app)

**GitHub Repository URL:**  
[https://github.com/larsboes/Generative-City-Wallet](https://github.com/larsboes/Generative-City-Wallet)

---

## 🏷️ Technologies / Tags
`Agentic AI`, `On-device SLM`, `Federated Learning`, `Privacy-by-Design`, `GDPR`, `Generative UI`, `Local Commerce`, `Fintech Wallet`, `Context-Aware`, `Knowledge Graph`, `Neo4j`, `React`, `TypeScript`, `Supabase`, `OpenWeather`, `Google Places`, `Apple Health`, `Strava`

## 🏷️ Additional Tags
`DACH`, `Sparkasse`, `Local Retail`, `Stuttgart Pilot`, `Hack Nation 2026`
