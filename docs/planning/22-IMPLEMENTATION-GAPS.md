# 22 — Implementation Gaps (Planning -> Runtime)

This document tracks what is still missing between planning design and current implementation.

Use this as the execution checklist after the core deterministic offer-selection pipeline.

---

## Status Summary

| Area | Status | Notes |
|---|---|---|
| Deterministic offer selection + trace | Implemented | Rules-first engine, thresholding, audit trace in runtime docs/code |
| Graph rule gate + explainability | Implemented | Pre-LLM guardrails and explainability path are live |
| KG projection idempotency | Implemented | SQLite-backed idempotency guard for graph write side-effects |
| OCR transit delay enrichment | Missing | Planned, not end-to-end implemented |
| Wallet pass cold-start seeding | Missing | Planned, no production pipeline yet |
| Spark Wave social coordination | Missing | Planned concept only |
| Post-workout advanced signal rollout | Partial | Core movement semantics exist; full scenario orchestration still missing |
| TS/Python contract parity for new runtime fields | Partial | Python contracts ahead of shared TS in some places |

---

## Gap Backlog (Actionable)

## 1) OCR Transit Delay Enrichment (E2E)

- **Goal:** Turn scanned ticket/screenshot into a deterministic transit delay window that can gate and frame offers.
- **Current:** Planned in `16-ADVANCED-SIGNALS.md`; not fully implemented in runtime path.
- **Required outputs:**
  - OCR ingestion API + parser confidence score.
  - Delay provider adapter with retries and timeout policy.
  - Context injection (`urgency_minutes`, `must_return_by`) into composite state.
  - Offer rule gate: only show if walk + purchase + return fits delay window.
- **Likely touchpoints:**
  - `apps/api/src/spark/services/composite.py`
  - `apps/api/src/spark/services/offer_decision.py`
  - `apps/api/src/spark/models/contracts.py`
  - `apps/mobile/src/local-llm/*` (or dedicated mobile enrichment bridge)
  - `tests/unit/` + fixtures
- **Acceptance criteria:**
  - Deterministic test for `delay=14m` path that yields recommendation.
  - Deterministic test for short delay path that blocks recommendation.
  - Audit trace includes transit-window reason metadata.

---

## 2) Wallet Pass Cold-Start KG Seeding

- **Goal:** Seed preference priors from user-approved wallet passes with lower confidence and faster decay.
- **Current:** Design documented, runtime write path not fully present.
- **Required outputs:**
  - Seed ingestion endpoint/model (`source=wallet_seed`).
  - Mapped category/attribute edge creation with bounded initial weights.
  - Explicit decay policy per source type.
  - Idempotent seed events (no duplicate edges on re-import).
- **Likely touchpoints:**
  - `apps/api/src/spark/graph/repository.py`
  - `apps/api/src/spark/services/redemption.py` (pattern reuse for idempotency)
  - `apps/api/src/spark/models/contracts.py`
  - `apps/mobile` wallet bridge code
  - graph tests + migration metadata
- **Acceptance criteria:**
  - Seed run is idempotent.
  - Seeded preferences influence ranking but are overridden by interaction data over time.
  - Source + decay metadata visible in graph debug endpoints.

---

## 3) Spark Wave Social Coordination

- **Goal:** Add optional social coordination mechanic without contact scraping/social graph coupling.
- **Current:** Concept and SQL sketch only.
- **Required outputs:**
  - Wave link creation/validation endpoints.
  - Anonymous attribution (`created_by_session`, limited TTL).
  - Milestone tie-in and catalyst bonus calculation rules.
  - Abuse protection (rate limits, replay protection, expiry checks).
- **Likely touchpoints:**
  - `apps/api/src/spark/db/schema.sql`
  - `apps/api/src/spark/routers/offers.py`
  - `apps/api/src/spark/routers/redemption.py`
  - mobile offer UI / deep-link handling
  - integration tests
- **Acceptance criteria:**
  - Two-session integration test validates wave progression.
  - No direct identity exposure in payloads or logs.
  - Bonus is deterministic and auditable.

---

## 4) Advanced Signals Rollout (Post-workout + Movement Expansion)

- **Goal:** Complete movement-mode driven context updates for post-workout recommendations.
- **Current:** Movement enum and planning logic exist; full scoring/eligibility integration is partial.
- **Required outputs:**
  - Explicit `post_workout` boosts in decision scoring path.
  - Category suppressions/boosts encoded in deterministic rules.
  - Session-level cooldowns adapted for movement transitions.
- **Likely touchpoints:**
  - `apps/api/src/spark/services/offer_decision.py`
  - `apps/api/src/spark/services/composite.py`
  - tests + fixtures
- **Acceptance criteria:**
  - `exercising` always blocks.
  - `post_workout` scenario promotes recovery categories over nightlife.
  - Decision trace explains movement-driven weighting.

---

## 5) Contract Parity + Docs Alignment

- **Goal:** Keep runtime behavior, shared contracts, and docs synchronized.
- **Current:** Some runtime fields are documented in Python first.
- **Required outputs:**
  - Mirror newly added runtime fields in `packages/shared`.
  - Extend contract symbol checks for new cross-boundary types.
  - Keep `docs/ARCHITECTURE.md` and `docs/NEO4J-GRAPH.md` in lockstep with code.
- **Acceptance criteria:**
  - CI contract checks pass with new symbols.
  - No undocumented response fields in live API routes.

---

## Suggested Build Order

1. Contract parity + tests hardening.
2. Post-workout deterministic rollout (smallest feature risk).
3. Wallet seed ingestion (high leverage, moderate complexity).
4. OCR transit delay E2E (high demo value, external dependency risk).
5. Spark Wave (largest integration surface).

---

## Runtime truth sources

- `docs/ARCHITECTURE.md`
- `docs/NEO4J-GRAPH.md`
- `docs/DEVELOPMENT.md`

Planning docs define intent; runtime docs define current behavior.
