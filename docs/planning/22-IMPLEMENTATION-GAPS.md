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
| OCR transit delay enrichment | Implemented (MVP) | Delay-window fields + deterministic gate are live; OCR parse adapter (`/api/ocr/transit/parse`) now includes retry/timeout policy and typed handoff |
| Wallet pass cold-start seeding | Partial | Wallet seed endpoint and idempotent graph writes are live; source quality calibration still pending |
| Spark Wave social coordination | Partial | Wave schema + create/join/get API are live with replay/expiry semantics, deterministic `catalyst_bonus_pct`, participant cap guard, and cleanup endpoint; stricter rate policy + downstream bonus consumption remain |
| Post-workout advanced signal rollout | Implemented (MVP) | Exercising hard block, post-workout category adjustments, and movement-aware recheck cadence are live |
| TS/Python contract parity for new runtime fields | Implemented (guarded) | Parity checker now targets `models/__init__.py` exports + field-level checks |
| Fluent Bit -> backend density ingestion E2E | Implemented (MVP) | Fluent Bit now forwards payone events to backend ingest and density read path is covered by integration test |
| Runtime distance signal in composite state | Implemented (MVP) | Deterministic distance estimation now replaces fixed distance stubs in composite + decision path |
| OCR/Wallet/Spark Wave test coverage | Partial | Added OCR fixtures/ingest/parse tests, wallet-seed idempotency, and wave progression + cleanup + participant-cap tests; wallet decay and broader failure-mode suites remain |
| Runtime architecture/data-model docs alignment | Implemented (MVP) | `docs/ARCHITECTURE.md` and `docs/DATA-MODEL.md` now include OCR confidence behavior, wave `join_applied`, and payone ingest path |

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
- Fluent Bit ingestion bridge to backend is live:
  - Fluent Bit HTTP output -> `/api/payone/ingest`
  - source: `infra/fluentbit/fluent-bit.yaml`, `apps/api/src/spark/routers/payone.py`
- Deterministic distance signal is live in ranking + composite state:
  - source: `apps/api/src/spark/services/distance.py`, `apps/api/src/spark/services/offer_decision.py`, `apps/api/src/spark/services/composite.py`
- Wallet seed API and graph projection path are live:
  - source: `apps/api/src/spark/routers/graph.py`, `apps/api/src/spark/services/wallet_seed.py`
- Spark Wave baseline flow is live:
  - schema + API + integration test
  - source: `apps/api/src/spark/db/schema.sql`, `apps/api/src/spark/routers/wave.py`, `tests/integration/test_wave_flow.py`
- OCR ingest policy hardening is live:
  - confidence-threshold acceptance + malformed timestamp rejection
  - source: `apps/api/src/spark/routers/ocr.py`, `tests/integration/test_ocr_ingest_endpoint.py`
- OCR parser/provider adapter is live:
  - raw OCR text parsing endpoint with timeout/retry policy and typed payload handoff
  - source: `apps/api/src/spark/services/ocr_transit.py`, `apps/api/src/spark/routers/ocr.py`, `tests/unit/test_ocr_transit_parser.py`
- Spark Wave catalyst/ops hardening is live:
  - deterministic `catalyst_bonus_pct`, participant-cap enforcement, and `/api/waves/cleanup` operational endpoint
  - source: `apps/api/src/spark/repositories/wave.py`, `apps/api/src/spark/routers/wave.py`, `tests/integration/test_wave_flow.py`, `scripts/ops/run_graph_maintenance.py`
- Runtime architecture/data-model docs are now aligned with current endpoints/semantics:
  - source: `docs/ARCHITECTURE.md`, `docs/DATA-MODEL.md`

---

## Gap Backlog (Actionable)

## 1) OCR Transit Delay Enrichment (E2E)

- **Goal:** Turn scanned ticket/screenshot into a deterministic transit delay window that can gate and frame offers.
- **Current:** Delay-window fields, deterministic short-window block, typed ingest checks, and parser/provider adapter (retry/timeout policy) are implemented.
- **Required outputs:**
  - Delay provider expansion beyond current rule-based parser (for higher-fidelity OCR extraction).
  - Context injection (`transit_delay_minutes`, `must_return_by`) into composite state.
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
- **Current:** Runtime write path is now present via `/api/graph/sessions/{session_id}/wallet-seed`; further calibration and source governance remain.
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
- **Current:** Baseline schema + create/join/get API are implemented with replay-safe joins, TTL expiry transitions, deterministic catalyst bonus, participant cap guard, and cleanup endpoint.
- **Required outputs:**
  - Downstream bonus consumption path in offer/redemption economics (if product requires direct payout impact).
  - Abuse protection completion (stricter per-session/per-wave rate policies and additional anti-spam heuristics).
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
- **Current:** Contract guard is aligned with split models architecture and enforces symbol + selected field parity; runtime architecture/data-model docs were refreshed for OCR/Wave/Payone ingestion.
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
- **Current:** Fluent Bit now forwards validated payone events to backend ingest; integration test confirms density read path impact.
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
- **Current:** Deterministic distance estimator now powers both composite state and decision trace/scoring metadata.
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
- **Current:** Dedicated suites added for OCR transit (including parse + Kreuzberg fixtures), wallet seed idempotency, and Spark Wave two-session/cleanup/cap flows.
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

1. Wallet seed source-quality calibration and stronger provenance/explainability.
2. Extended OCR/Wallet/Wave edge-case and failure-mode tests.
3. Spark Wave stricter anti-abuse/rate policy tuning.
4. OCR provider quality improvements beyond current rule-based parser.

---

## Runtime truth sources

- `docs/ARCHITECTURE.md`
- `docs/architecture/neo4j-graph.md`
- `docs/DEVELOPMENT.md`

Planning docs define intent; runtime docs define current behavior.
