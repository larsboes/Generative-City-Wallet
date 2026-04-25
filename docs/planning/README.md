# Spark — Docs Navigation

---

## Quick Start by Role

| You are... | Read first | Then |
|---|---|---|
| **Designing merchant dashboard (David)** | `20-MERCHANT-DASHBOARD.md` | `05-MERCHANT-PLATFORM.md` for rule logic detail |
| **Designing consumer app** | `21-CONSUMER-APP.md` | — |
| **Building backend** | `17-BUILD-PLAN.md` | `15-FINN-BRIEFING.md` for Finn's data layer |
| **Building mobile** | `17-BUILD-PLAN.md` → shared contracts | `21-CONSUMER-APP.md` for screen spec |
| **Preparing the pitch** | `18-DSV-GAP-ANALYSIS.md` | `07-DEMO-SCRIPT.md` |
| **New to the project** | `BACKGROUND.md` (10 min) | This README → pick your lane |

---

## Active Files

### Design & Product
| File | What it answers |
|---|---|
| **`20-MERCHANT-DASHBOARD.md`** ⭐ | **David's file** — all merchant screens, wireframes, component list, Figma direction |
| **`21-CONSUMER-APP.md`** ⭐ | All consumer screens + notifications + lock screen + widgets + feature inventory |
| `19-PRODUCT-OVERVIEW.md` | Combined overview + key user flows (references 20 + 21) |
| `05-MERCHANT-PLATFORM.md` | Merchant platform deep spec (rule engine logic, analytics detail) |
| `10-OFFER-SELECTION.md` | Why one offer at a time, ranking algorithm, anti-spam rules |
| `14-STAKEHOLDER-CONFLICT-RESOLUTION.md` | Empty venue + social user conflict — framing rules, coupon mechanics |

### Technical Architecture
| File | What it answers |
|---|---|
| **`17-BUILD-PLAN.md`** ⭐ | Shared TypeScript contracts, Gemini prompt, data engineering sequence, team split |
| `02-ARCHITECTURE.md` | System overview diagram, GDPR boundary, data flow |
| `03-CONTEXT-ENGINE.md` | Every signal: IMU modes, Payone density, weather, events, transit |
| `04-GENERATIVE-ENGINE.md` | GenUI system, Gemini Flash integration, offer schema, preference learning |
| `13-ON-DEVICE-AI-AND-KNOWLEDGE-GRAPH.md` | User KG (SQLite), FunctionGemma, hard rails, audit trail, transaction KG seeding |
| **[`../USER-KNOWLEDGE-GRAPH-NEO4J.md`](../USER-KNOWLEDGE-GRAPH-NEO4J.md)** ⭐ | **Implemented server graph (Neo4j)** — personalization, rules, writes, explainability, retention, migrations |
| `16-ADVANCED-SIGNALS.md` | Exercise states, OCR transit scan, wallet pass KG seeds, Spark Wave |

### Build & Implementation
| File | What it answers |
|---|---|
| `15-FINN-BRIEFING.md` | Finn's full spec: Payone generator, density signal, occupancy, conflict engine |
| `06-MVP-SCOPE.md` | Must/Should/Nice-to-Have tiers, build timeline, tech stack |
| `08-OPEN-QUESTIONS.md` | Unresolved platform decisions (mobile platform, APIs, discount ranges) |

### Pitch & Positioning
| File | What it answers |
|---|---|
| **`18-DSV-GAP-ANALYSIS.md`** ⭐ | TreueWelt shutdown, S-POS Cube gap, business case — Q&A prep |
| `07-DEMO-SCRIPT.md` | 3-min demo narrative, Stuttgart scenarios, killer moments, Q&A prep |
| `BACKGROUND.md` | Vision, product strategy, challenge analysis, pitch glossary |
| `12-SUBMISSION-README.md` | Template for the final GitHub README |

---

## Archive (`archive/` folder — don't update)

| File | Superseded by |
|---|---|
| `00-VISION.md` | `BACKGROUND.md` |
| `01-CHALLENGE-ANALYSIS.md` | `BACKGROUND.md` |
| `09-CRITIQUE.md` | Historical record — decisions already implemented |
| `11-CONSUMER-UX.md` | `19-PRODUCT-OVERVIEW.md` (wireframes merged in) |

---

## The Three Files That Matter Most Right Now

```
19-PRODUCT-OVERVIEW.md   ←  designers start here
17-BUILD-PLAN.md         ←  engineers start here
18-DSV-GAP-ANALYSIS.md   ←  pitch team start here
```

---

## What's Where (by topic)

| Topic | Primary doc | Supporting |
|---|---|---|
| Offer card design + wireframes | 19 | — |
| GenUI — what changes per context | 19 (table) | 04 |
| Context Slider (demo panel) | 19 (Screen 9) | — |
| Payone density signal | 15 (code) | 03 |
| Composite context state | 03 | 02 |
| Gemini Flash prompt + JSON schema | 17 | 04 |
| Hard rails / Air Canada liability | 13 | 17 |
| User knowledge graph | 13 | 17 |
| **Server Neo4j graph (implemented)** | [`../USER-KNOWLEDGE-GRAPH-NEO4J.md`](../USER-KNOWLEDGE-GRAPH-NEO4J.md) | [`../REPOSITORY-OVERVIEW.md`](../REPOSITORY-OVERVIEW.md) |
| Transaction history KG seeding | 13 (Part 4) | — |
| Conflict resolution (empty venue + social user) | 14 | 15 |
| Coupon mechanics (milestone coupon) | 14 | 15 |
| Demo narrative + Stuttgart scenarios | 07 | 19 (flows) |
| Privacy Ledger screen | 19 (Screen 7) | — |
| Merchant rule engine | 05 | 19 (Screen M2) |
| DSV pitch Q&A | 18 | 07 |
| Team split / sync points | 17 | — |
| Exercise / post-workout signals | 16 | 03 |
| OCR transit scan | 16 | 07 (Scenario B) |
| Spark Wave social feature | 16 | 14 |
| Gemma 3n on-device | 13 | 17 |
| Vision + why we built this | BACKGROUND | — |
