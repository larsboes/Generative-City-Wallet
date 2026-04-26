# MVP Scope & Feature Roadmap

## Core Principle: Loop Closure

The MVP focus is on establishing a complete, end-to-end data flow:
`Context Detection → Composite State → Offer Generation → Visual Display → Redemption → Verification`

---

## 1. Must-Have Features (Loop Closure)

### Simulated Payone Feed
- Synthetic transaction generator for demo merchants.
- Detects lulls vs. historical baselines.
- API: `GET /api/payone/density/{merchant_id}`.

### Environmental Context
- Real-time weather integration (OpenWeatherMap).
- Derives "weather need" (e.g., warmth vs. refreshment).

### Composite Context State Builder
- Combines intent vector (mobile) + environment + demand + temporal signals.
- Generates a semantic summary for the LLM.

### Generative Offer Pipeline (Gemini Flash)
- Structured JSON output for content and GenUI parameters.
- Server-side hard rails for financial accuracy.

### Mobile App (Expo)
- On-device IMU classification (browsing vs. commuting).
- Quantized location (grid cell).
- Dynamic GenUI card rendering.
- QR token generation on accept.

---

## 2. Planned Extensions (Roadmap)

### Transit Delay Enrichment
- OCR scanning of tickets to identify wait windows.
- Automatic comfort offer triggering during delays.

### Advanced Mobility Signals
- Post-workout recovery detection.
- Cycling safety blocks.

### Social Coordination (Spark Wave)
- Milestone-based group offers.
- Anonymous momentum signals in cards.

### Knowledge Graph Seeding
- Cold-starting preferences from on-device transaction history and wallet passes.

### Merchant Platform
- Payone Pulse real-time visualization.
- Interactive rule engine for discount management.
