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
| Post-workout advanced signal rollout | Implemented (MVP) | Exercising hard block, post-workout category adjustments, and movement-aware recheck cadence are live |
| TS/Python contract parity for new runtime fields | Partial | Python contracts ahead of shared TS in some places |
| Fluent Bit -> backend density ingestion E2E | Partial | Fluent Bit validation exists, but no end-to-end feed into backend table used by density scoring |
| Runtime distance signal in composite state | Missing | Composite and ranking still use deterministic distance stubs |
| OCR/Wallet/Spark Wave test coverage | Missing | No dedicated unit/integration coverage for these roadmap features |
| Neo4j runtime doc path references | Partial | Runtime docs moved to `docs/architecture/neo4j-graph.md`, but this file still references legacy path |

---

## Implemented Since Original Gap List

- Movement-aware deterministic rollout is active in runtime:
  - exercising hard block
  - post-workout category boost/suppression
  - movement-aware `recheck_in_minutes`
  - source: `apps/api/src/spark/services/offer_decision.py`
- Graph operational surface and preference explainability are live:
  - `/api/graph/health`, `/api/graph/stats`, `/api/graph/migrations`, `/api/graph/cleanup`, `/api/graph/decay-preferences`
  - source: `apps/api/src/spark/routers/graph.py`
- Graph idempotency/retention/decay primitives are live in repo + schema:
  - source: `apps/api/src/spark/graph/repository.py`, `apps/api/src/spark/db/schema.sql`

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
- **Current:** Core deterministic behavior is implemented in runtime (hard block, category weighting, movement-aware recheck cadence). Remaining work is expansion scenarios only.
- **Required outputs:**
  - Expand beyond current `post_workout` set into additional movement contexts (if product requires it).
  - Align mobile/app-facing movement semantics with backend rule labels.
  - Add scenario tests for edge transitions between movement modes.
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
  - Keep `docs/ARCHITECTURE.md` and `docs/architecture/neo4j-graph.md` in lockstep with code.
- **Acceptance criteria:**
  - CI contract checks pass with new symbols.
  - No undocumented response fields in live API routes.

---

## 6) Fluent Bit -> Backend Density Ingestion (E2E)

- **Goal:** Ensure validated ingress events actually influence offer decision density in runtime.
- **Current:** `infra/fluentbit` migration is complete, but output is currently stdout + DLQ file only; no direct handoff into backend table used by density scoring.
- **Required outputs:**
  - Connect Fluent Bit output to backend-ingested path (or explicit bridge service).
  - Align runtime density reads with the live ingestion table (currently density reads `payone_transactions`).
  - Add an integration test proving an ingress event changes downstream density response.
- **Likely touchpoints:**
  - `infra/fluentbit/fluent-bit.yaml`
  - `apps/api/src/spark/services/density.py`
  - `apps/api/src/spark/services/transactions.py`
  - ingestion/integration tests
- **Acceptance criteria:**
  - Ingested sample event is queryable in the table used for density scoring.
  - Density endpoint/composite call reflects the ingested event.
  - DLQ behavior remains unchanged for invalid events.

---

## 7) Replace Distance Stubs with Runtime Signal

- **Goal:** Remove hardcoded distance proxies from scoring/composite outputs.
- **Current:** Composite response and decision scoring both use fixed distance assumptions.
- **Required outputs:**
  - Compute deterministic distance from available location abstraction (for example from grid-cell or provided location input).
  - Feed computed value into composite merchant context and decision scoring metadata.
  - Preserve deterministic fallback only when distance input is unavailable.
- **Likely touchpoints:**
  - `apps/api/src/spark/services/composite.py`
  - `apps/api/src/spark/services/offer_decision.py`
  - `apps/api/src/spark/models/contracts.py`
  - tests + fixtures
- **Acceptance criteria:**
  - `merchant.distance_m` in composite output is no longer constant for all merchants.
  - Decision trace distance metadata reflects computed values.
  - Existing deterministic tests remain stable with explicit fixture coordinates.

---

## 8) Missing Test Coverage for Roadmap Features

- **Goal:** Add regression protection for high-impact planned features still under implementation.
- **Current:** Strong coverage for current deterministic/graph rails; no dedicated suites for OCR transit, wallet seed ingestion, or Spark Wave flows.
- **Required outputs:**
  - Add OCR transit window rule tests (allow/block paths).
  - Add wallet seed idempotency + decay-behavior tests.
  - Add Spark Wave two-session progression integration test.
- **Likely touchpoints:**
  - `tests/unit/`
  - `tests/integration/`
  - feature services/routers as implemented
- **Acceptance criteria:**
  - CI fails on regressions for each new feature family.
  - Test fixtures cover both positive and negative scenarios.
  - New tests document intended deterministic behavior clearly.

---

## Suggested Build Order

1. Contract parity + tests hardening.
2. Fluent Bit -> backend density ingestion E2E.
3. Runtime distance signal (remove stubs).
4. Wallet seed ingestion (high leverage, moderate complexity).
5. OCR transit delay E2E (high demo value, external dependency risk).
6. Spark Wave (largest integration surface).

---

## Runtime truth sources

- `docs/ARCHITECTURE.md`
- `docs/architecture/neo4j-graph.md`
- `docs/DEVELOPMENT.md`

Planning docs define intent; runtime docs define current behavior.
