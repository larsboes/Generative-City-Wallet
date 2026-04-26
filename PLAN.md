# PLAN — Implementation Gaps (Planning -> Runtime)

This document tracks what is still missing between planning design and current implementation.

Use this as the execution checklist after the core deterministic offer-selection pipeline.

---

## Status Summary

| Area | Status | Notes |
|---|---|---|
| Deterministic offer selection + trace | Implemented | Rules-first engine, thresholding, audit trace in runtime docs/code |
| Graph rule gate + explainability | Implemented | Pre-LLM guardrails and explainability path are live |
| KG projection idempotency | Implemented | SQLite-backed idempotency guard for graph write side-effects |
| OCR transit delay enrichment | Partial | Delay-window fields + deterministic gate are live; OCR parse adapter now includes retry/timeout policy and hybrid rule-based provider extraction (line/station/return-by confidence), but non-rule provider expansion remains |
| Wallet pass cold-start seeding | Partial | Wallet seed endpoint now includes quality-aware weighting/decay by source type, per-source base impact multipliers, and stronger longitudinal damping; production replay calibration still pending |
| Spark Wave social coordination | Partial | Wave schema + create/join/get API are live with replay/expiry semantics, deterministic `catalyst_bonus_pct`, participant cap guard, cleanup endpoint, stricter anti-abuse rate guards, and redemption cashback consumption of completed-wave catalyst bonus; broader economics propagation remains |
| Post-workout advanced signal rollout | Implemented (MVP) | Exercising hard block, post-workout + cycling + transit-waiting category adjustments, and movement-aware recheck cadence are live |
| TS/Python contract parity for new runtime fields | Implemented (guarded) | Parity checker now covers continuity reset symbols and expanded field-level checks (`IntentVector.continuity_hint`, `GenerateOfferRequest` transit/OCR fields, `WalletSeedResponse` guardrail counters) |
| Fluent Bit -> backend density ingestion E2E | Implemented (MVP) | Fluent Bit now forwards payone events to backend ingest and density read path is covered by integration test |
| Runtime distance signal in composite state | Implemented (MVP) | Deterministic distance estimation now replaces fixed distance stubs in composite + decision path |
| OCR/Wallet/Spark Wave test coverage | Implemented (MVP) | Added OCR fixtures/ingest/parse tests (including threshold boundary), wallet seed idempotency/decay + graph-unavailable failure path, and wave progression + cleanup + participant-cap + create-rate-limit tests |
| Runtime architecture/data-model docs alignment | Implemented (MVP) | `docs/ARCHITECTURE.md` and `docs/DATA-MODEL.md` now include OCR confidence behavior, wave `join_applied`, and payone ingest path |
| Intent source-of-truth + identity continuity model | Partial | Server-side trust normalization/provenance for `time_bucket` + `weather_need` is live, plus privacy-preserving continuity pseudonym derivation (`continuity_id`) and reset/opt-out API path; raw sensor ingestion and richer identity controls remain |

---

## Implemented Since Original Gap List

- Movement-aware deterministic rollout is active in runtime:
  - exercising hard block
  - post-workout category boost/suppression
  - cycling recovery-vs-nightlife weighting and recheck cadence
  - transit-waiting quick-stop weighting and faster recheck cadence
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
- OCR provider quality has advanced beyond baseline rule parsing:
  - `hybrid_rule_based` parser adds stronger deterministic extraction (`line`, `station`, normalized `must_return_by`) and confidence scoring
  - parser-provider selection is now explicit in parse request contracts
  - source: `apps/api/src/spark/services/ocr_transit.py`, `apps/api/src/spark/models/ocr.py`, `packages/shared/src/contracts.ts`, `tests/unit/test_ocr_transit_parser.py`
- Spark Wave catalyst/ops hardening is live:
  - deterministic `catalyst_bonus_pct`, participant-cap enforcement, and `/api/waves/cleanup` operational endpoint
  - source: `apps/api/src/spark/repositories/wave.py`, `apps/api/src/spark/routers/wave.py`, `tests/integration/test_wave_flow.py`, `scripts/ops/run_graph_maintenance.py`
- Spark Wave anti-abuse hardening has advanced:
  - active-wave cap per creator session and create/join burst limits per session are enforced
  - per-wave join burst guard added to prevent concentrated spam joins
  - source: `apps/api/src/spark/repositories/wave.py`, `tests/integration/test_wave_flow.py`
- Spark Wave catalyst bonus is now consumed in redemption economics:
  - completed wave `catalyst_bonus_pct` is deterministically applied to redemption cashback
  - redemption response now exposes `base_amount_eur` and `catalyst_bonus_pct` for auditability
  - source: `apps/api/src/spark/repositories/wave.py`, `apps/api/src/spark/services/redemption.py`, `apps/api/src/spark/models/redemption.py`, `tests/unit/test_redemption_idempotency.py`, `tests/integration/test_wave_flow.py`
- Wallet seed quality/provenance hardening is live:
  - source-aware decay + quality multiplier and preference provenance fields (`decay_rate`, `source_confidence`, `artifact_count`) exposed in graph debug endpoint
  - source: `apps/api/src/spark/services/wallet_seed.py`, `apps/api/src/spark/routers/graph.py`, `tests/unit/test_wallet_seed.py`, `tests/unit/test_graph_preferences_provenance.py`
- Wallet seed source-governance tuning has advanced:
  - per-source `base_delta_multiplier` is now enforced (`wallet_pass` > `receipt_ocr` > `manual_import`)
  - stronger longitudinal damping curve applied by per-session source history
  - deterministic tests now verify monotonic reinforcement reduction as history grows
  - source: `apps/api/src/spark/services/wallet_seed.py`, `tests/unit/test_wallet_seed.py`
- Intent trust/provenance normalization is live for high-impact fields:
  - server-side trust policy (`authoritative`/`advisory`) normalizes `time_bucket` + `weather_need`
  - per-field provenance is emitted in composite user context + decision trace metadata (`intent_trust_normalization`)
  - source: `apps/api/src/spark/services/intent_trust.py`, `apps/api/src/spark/services/composite.py`, `apps/api/src/spark/models/context.py`, `tests/unit/test_intent_trust.py`
- Identity continuity baseline is now explicit in runtime:
  - server derives privacy-preserving `continuity_id` from optional `intent.continuity_hint` (fallback to session-derived pseudonym)
  - continuity source + expiry metadata are included in user context and provenance (`derived`)
  - source: `apps/api/src/spark/services/identity_continuity.py`, `apps/api/src/spark/services/composite.py`, `apps/api/src/spark/models/context.py`, `tests/unit/test_identity_continuity.py`, `tests/integration/test_composite_graph_integration.py`
- Identity continuity reset controls are now exposed:
  - `POST /api/identity/continuity/reset` supports continuity rotation and explicit opt-out behavior
  - response includes updated continuity metadata (`continuity_id`, `continuity_hint`, `expires_at`, `opt_out`)
  - source: `apps/api/src/spark/routers/identity.py`, `apps/api/src/spark/services/identity_continuity.py`, `apps/api/src/spark/models/api.py`, `tests/unit/test_identity_continuity_reset.py`, `tests/unit/test_identity_router.py`, `tests/integration/test_identity_continuity_endpoint.py`
- Runtime architecture/data-model docs are now aligned with current endpoints/semantics:
  - source: `docs/ARCHITECTURE.md`, `docs/DATA-MODEL.md`
- Contract parity guard has been tightened for newer boundary types:
  - includes continuity reset request/response symbols
  - validates expanded field-level parity for continuity/transit/guardrail response fields
  - source: `scripts/dev/check_contract_symbols.py`, `apps/api/src/spark/models/__init__.py`, `packages/shared/src/contracts.ts`

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
- **Current:** Runtime write path is present via `/api/graph/sessions/{session_id}/wallet-seed`; source-aware decay and quality-weighted reinforcement are live, and provenance is exposed via `/api/graph/sessions/{session_id}/preferences`.
- **Required outputs:**
  - Longitudinal calibration of source-quality multipliers with production-like replay/eval data.
  - Source governance policy refinements (allowed source taxonomy + confidence defaults by source) beyond current multiplier tiering.
  - Extended decay-behavior test coverage over multi-step/session timelines.
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
  - Broader downstream bonus propagation beyond redemption cashback path (if product requires additional payout impact surfaces).
  - Additional anti-spam heuristics beyond current per-session/per-wave rate limits (for example reputation/risk weighting).
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
- **Current:** Core deterministic behavior is implemented in runtime (hard block, post-workout + cycling + transit-waiting category weighting, movement-aware recheck cadence). Remaining work is additional movement contexts only.
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

## 9) Intent Source-of-Truth + Identity Continuity

- **Goal:** Make runtime context derivation and identity continuity explicit, auditable, and less dependent on unverified client-side shaping.
- **Current:**
  - Backend trust normalization is active for `time_bucket` (authoritative) and `weather_need` (advisory) with auditable provenance.
  - Privacy-preserving continuity pseudonym derivation is active (`continuity_id`, source, expiry) in composite user context, with reset/opt-out API control and integration coverage.
  - No backend raw sensor pipeline for GPS/IMU processing; backend still assumes client-side sensor-level intent extraction.
  - Identity continuity is session-scoped (`session_id`) rather than a richer long-horizon user model.
- **Required outputs:**
  - Introduce a backend verification/normalization layer for intent fields that can be cross-checked against server-side signals (time, weather, merchant proximity window).
  - Define a server-side trust policy per field (`authoritative`, `advisory`, `derived`, `ignored`) and enforce it in request handling.
  - Add a continuity strategy beyond transient sessions (for example privacy-preserving stable pseudonym strategy or explicit session-link policy), with documented retention and user controls.
  - Add explicit audit metadata recording field provenance and whether values were accepted, overridden, or rejected.
- **Likely touchpoints:**
  - `apps/api/src/spark/models/api.py`
  - `apps/api/src/spark/models/context.py`
  - `apps/api/src/spark/services/composite.py`
  - `apps/api/src/spark/services/offer_pipeline.py`
  - `docs/ARCHITECTURE.md`
  - shared contracts and mobile bridge code
- **Acceptance criteria:**
  - Deterministic tests verify server-side normalization/override behavior for mismatched client inputs.
  - Offer audit output includes per-field provenance/trust decisions.
  - Continuity behavior is documented end-to-end (generation, reuse, expiry, reset) and validated in integration tests.

---

## Suggested Build Order

1. Identity continuity strategy beyond session scope (privacy-preserving linkage + controls).
2. OCR provider expansion beyond deterministic rule-based family (for example model-backed OCR extraction path).
3. Spark Wave broader bonus propagation + anti-spam heuristics refinement.

---

## Runtime truth sources

- `docs/ARCHITECTURE.md`
- `docs/architecture/neo4j-graph.md`
- `docs/DEVELOPMENT.md`

Planning docs define intent; runtime docs define current behavior.
