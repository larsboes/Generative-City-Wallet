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
| OCR transit delay enrichment | Implemented (MVP) | Delay-window fields + deterministic gate are live; OCR parse adapter supports model-assisted provider path with deterministic guardrails |
| Wallet pass cold-start seeding | Implemented | Quality-aware weighting, source multipliers, and longitudinal damping are live with calibration tests |
| Spark Wave social coordination | Implemented (MVP) | Wave schema + API are live; catalyst bonus propagates to offer + redemption economics |
| Post-workout advanced signal rollout | Implemented (MVP) | Exercising block and movement-aware category adjustments are live |
| Intent source-of-truth + identity model | Implemented | Authoritative trust normalization, advisory activity policies, and privacy-preserving continuity are live |
| External context source integration | Implemented | Google Places + Luma context enrichment is live |
| Fluent Bit -> backend density ingestion | Implemented | Ingestion bridge is live and connected to density read path |
| Runtime distance signal | Implemented | Geographic distance estimation now powers decision scoring |
| Dynamic transit gating | Implemented | Walking-time vs delay window check is live and merchant-specific |
| TS/Python contract parity | Implemented | Boundary types are synchronized and guarded by CI checks |
| Final demo data cleanup | Implemented | Munich fixture + README submission values are finalized |


---

## Implemented Since Original Gap List

- **Intent trust/provenance normalization is hardened:**
  - Authoritative normalization for `time_bucket` + `weather_need`.
  - Advisory policy for activity signals with source-aware confidence caps.
  - Source: `apps/api/src/spark/services/intent_trust.py`
- **Wallet seed governance is hardened:**
  - Source-specific multipliers and confidence ceilings enforced.
  - Longitudinal damping (history-aware) reduces reinforcement delta monotonically.
  - Calibration matrix tests detect policy drift.
  - Source: `apps/api/src/spark/services/wallet_seed.py`, `tests/unit/test_wallet_seed.py`
- **Spark Wave bonus propagation is complete:**
  - Catalyst bonus applied to both offer generation and redemption cashback.
  - Source: `apps/api/src/spark/services/offer_pipeline.py`, `apps/api/src/spark/services/redemption.py`
- **Pipeline infra consolidation:**
  - Fluent Bit config and validation moved to `infra/pipeline/` for a clean monorepo structure.
  - Graph maintenance (cleanup + decay) moved to `infra/pipeline/graph-maintenance.py`.
  - Root `src/` removed to avoid architectural ambiguity.
- **Geographic distance estimation:**
  - Replaced stubs with `estimate_distance_m` in `offer_decision.py` and `composite.py`.
- **Identity continuity:**
  - Server-side `continuity_id` derivation and reset controls are live.
  - Mobile now persists/reuses `continuity_hint` for continuity across app restarts.
  - Opt-out path now triggers best-effort graph session clear-down/unlink.
  - Source: `apps/mobile/src/api/continuity.ts`, `apps/mobile/src/api/spark.ts`, `apps/api/src/spark/routers/identity.py`, `apps/api/src/spark/graph/store/ops.py`
- **Strava abstraction path:**
  - Mobile OAuth/token lifecycle helpers (`exchange`, `refresh`, `disconnect`) with secure token storage wrappers are live.
  - Mobile activity summarization maps Strava activity into abstracted intent fields only.
  - Backend advisory policy enforces source/signal consistency and confidence capping with provenance.
  - Decision trace now exposes activity confidence bands for explainability.
  - Source: `apps/mobile/src/api/strava.ts`, `apps/mobile/src/api/secureStore.ts`, `apps/mobile/src/local-llm/sourceSignals.ts`, `apps/api/src/spark/services/intent_trust.py`, `apps/api/src/spark/services/offer_decision.py`
- **Dynamic Transit Gating:**
  - Replaced hardcoded blocks with merchant-specific round-trip viability checks.
  - Calculation: `(distance_m / 80m_min) * 2 + 5m buffer`.
  - Intelligent recheck cadence aligned with transit delay window.
  - Source: `apps/api/src/spark/services/offer_decision.py`, `tests/unit/test_dynamic_transit_gating.py`

---

## Gap Backlog (Actionable)

## 1) Long-horizon Identity Strategy

- **Goal:** Support cross-session stable pseudonyms with documented retention and user opt-out controls beyond transient sessions.
- **Current:** `identity_continuity.py` derives HMAC-based `continuity_id`; mobile now persists/reuses `continuity_hint`; reset/opt-out controls are live with best-effort graph purge on opt-out.
- **Required:**
  - Complete end-to-end lifecycle wiring in product surfaces (explicit rotate/reset UX and callback handling of rotated hints).
  - Verify/monitor graph clear-down semantics operationally (metrics/audit visibility and hardening under failure/retry paths).
  - Document and enforce retention lifecycle (generation, reuse window, expiry, reset/opt-out semantics).
- **Definition of done:**
  - Identity lifecycle is wired end-to-end across backend + product surfaces, including explicit rotate/reset/opt-out user flows.
  - Reset/opt-out behavior is operationally hardened with observable purge outcomes (logs/metrics) and reliable behavior under retry/failure scenarios.
  - Retention lifecycle is documented and enforced end-to-end (generation, reuse window, expiry, reset, retention).
- **Tests to run:**
  - `uv run pytest tests/unit/test_identity_continuity.py tests/unit/test_identity_continuity_reset.py tests/unit/test_identity_router.py`
  - `uv run pytest tests/integration/test_identity_continuity_endpoint.py tests/integration/test_composite_graph_integration.py`
- **Demo impact:**
  - Medium/low for judging demo flow; high for trust/compliance narrative and longer-horizon personalization quality.

## 2) Final Demo Data Cleanup

- **Goal:** Finalize Munich merchant list and Hero Score scaling for the live demo.
- **Touchpoint:** `README.md`, `resources/mock_venues_munich.json`.
- **Status:** Implemented.
- **Definition of done:**
  - [x] Munich merchant fixture is the single source used by demo seed/load scripts.
  - [x] Hero Score scaling is explicitly documented with baseline and expected range.
  - [x] `README.md` has no placeholder submission/demo values.
- **Tests to run:**
  - `uv run pytest tests/integration/test_smoke.py tests/integration/test_wave_flow.py`
  - Manual demo dry-run: load data, generate offer, redeem, confirm cashback and score output formatting.
- **Demo impact:**
  - High: ensures all shown numbers and claims are consistent during judging.

## 3) Product Surface Follow-ups (Deferred)

- **Goal:** Track app-surface updates for the user mobile app and business web app after core backend gaps are closed.
- **Current:** Core backend/runtime work is prioritized first; UI/UX and operational adjustments are intentionally deferred.
- **Deferred scope (check later):**
  - Mobile user app: expose identity controls (reset/opt-out), continuity lifecycle messaging, and final UX copy.
  - Business web app: align business-facing views/actions with finalized Spark Wave + identity/retention behavior.
  - End-to-end verification that mobile and web surfaces reflect final backend policies and docs.
- **Trigger to resume:**
  - Resume once the long-horizon identity strategy backlog item is complete or when prep starts for release hardening.
- **Demo impact:**
  - Low/medium now; high for post-demo product readiness and operational clarity.

---

## Suggested Build Order

1. **Long-horizon identity strategy refinement**.
   - Treat this as post-demo unless judges explicitly require cross-session continuity proof.
2. **Product surface follow-ups (deferred).**
   - Mobile user app + business web app adjustments after backend policy finalization.


## Validation Commands (keep as release gate)

- **Contract parity:**
  - `python3 scripts/dev/check_contract_symbols.py`
- **Focused runtime regressions:**
  - `uv run pytest tests/unit/test_intent_trust.py tests/unit/test_ocr_transit_parser.py tests/unit/test_wallet_seed.py tests/unit/test_offer_decision.py tests/unit/test_offer_pipeline_wave_bonus.py tests/unit/test_external_context_services.py tests/integration/test_wave_flow.py tests/integration/test_composite_graph_integration.py tests/integration/test_smoke.py`
- **Optional full sweep before release:**
  - `uv run pytest`

---

## Runtime truth sources

- `docs/ARCHITECTURE.md`
- `docs/architecture/neo4j-graph.md`
- `docs/DEVELOPMENT.md`

Planning docs define intent; runtime docs define current behavior.
