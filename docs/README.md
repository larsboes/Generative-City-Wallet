# Spark — Documentation

Spark is a real-time contextual intelligence layer for urban retail.

---

## 🏗️ Core Architecture
| File | Description |
|---|---|
| **[`ARCHITECTURE.md`](ARCHITECTURE.md)** | **System Overview:** Main architecture, privacy boundaries, and data flow. |
| **[`architecture/self-learning-api-reference.md`](architecture/self-learning-api-reference.md)** | **Self-Learning Ops/API:** Attribution, idempotency, guardrails, and maintenance endpoints. |
| **[`DATA-MODEL.md`](DATA-MODEL.md)** | **Schema & Contracts:** Canonical API contracts, SQLite schema, and graph projection. |
| **[`DEVELOPMENT.md`](DEVELOPMENT.md)** | **Dev Guide:** Local setup, toolchain, and contribution rules. |
| **[`CONCEPT.md`](CONCEPT.md)** | **Vision:** Stable product principles and "Why" behind Spark. |

---

## 🛠️ Functional Specifications (`specs/`)
Technical deep-dives into the system's core logic engines.

- **[`CONTEXT-ENGINE.md`](specs/CONTEXT-ENGINE.md)**: Signal aggregation and the composite state machine.
- **[`GENERATIVE-ENGINE.md`](specs/GENERATIVE-ENGINE.md)**: AI offer pipeline, GenUI, and prompting strategy.
- **[`INTENT-MODEL.md`](specs/INTENT-MODEL.md)**: On-device mobility classification and intent extraction.
- **[`KNOWLEDGE-GRAPH.md`](specs/KNOWLEDGE-GRAPH.md)**: User preference graph and behavioral seeding.
- **[`CONFLICT-RESOLUTION.md`](specs/CONFLICT-RESOLUTION.md)**: Balancing user intent with venue occupancy.
- **[`SOCIAL-COORDINATION.md`](specs/SOCIAL-COORDINATION.md)**: Anonymous momentum signals and Spark Waves.
- **[`SAFETY-AND-LIABILITY.md`](specs/SAFETY-AND-LIABILITY.md)**: Hard rails, audit trails, and legal defensive design.
- **[`ANALYTICS-ENGINE.md`](specs/ANALYTICS-ENGINE.md)**: "Community Hero Score" and Recovered Revenue algorithms.
- **[`REDEMPTION-PROTOCOL.md`](specs/REDEMPTION-PROTOCOL.md)**: Secure QR handshake and HMAC validation.
- **[`DATA-PRIVACY-LIFECYCLE.md`](specs/DATA-PRIVACY-LIFECYCLE.md)**: On-device sensor TTL and the "Cloud Exit Gate."
- **[`TRANSIT-WAIT-LOGIC.md`](specs/TRANSIT-WAIT-LOGIC.md)**: Visit window calculations for VVS/transit delays.
- **[`MERCHANT-INVENTORY-SIGNAL.md`](specs/MERCHANT-INVENTORY-SIGNAL.md)**: "TooGoodToGo Pro Max" and inventory-driven ranking.

---

## 📱 Product & UX (`product/`)
Specifications for user-facing surfaces.

- **[`OVERVIEW.md`](product/OVERVIEW.md)**: The "Two Products, One System" concept and key flows.
- **[`CONSUMER-APP.md`](product/CONSUMER-APP.md)**: Mobile app screens, interactions, and privacy pulses.
- **[`MERCHANT-DASHBOARD.md`](product/MERCHANT-DASHBOARD.md)**: Rule engine, analytics, and redemption flows.

---

## 🚀 Pitch & Strategy (`pitch/`)
Materials for presentation and business analysis.

- **[`BACKGROUND.md`](pitch/BACKGROUND.md)**: Vision, strategy, and challenge analysis.
- **[`DEMO-SCRIPT.md`](pitch/DEMO-SCRIPT.md)**: The end-to-end presentation narrative.
- **[`GAP-ANALYSIS.md`](pitch/GAP-ANALYSIS.md)**: DSV-specific business case and competitive mapping.

---

## 🗺️ Roadmap & Planning (`roadmap/`, `planning/`)
- **[`../PLAN.md`](../PLAN.md)**: Consolidated implementation status and backlog.
- **[`planning/OPEN-QUESTIONS.md`](planning/OPEN-QUESTIONS.md)**: Live decision log and blockers.
- **Planning notes in `planning/`**: Historical context and decision rationale.

---

## Learning Loop Notes

Current runtime includes a server-side self-learning graph loop for personalization:

- event-granular idempotency for learning writes
- per `(session_id, category)` update-rate guardrails
- preference attribution ledger for explainability
- lifecycle automation for decay + source-tier retention
- learning metrics logging for drift/suppression monitoring

Primary implementation paths:

- `apps/api/src/spark/services/redemption.py`
- `apps/api/src/spark/services/wallet_seed.py`
- `apps/api/src/spark/repositories/redemption.py`
- `infra/pipeline/graph-maintenance.py`
