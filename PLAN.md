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
| External context source integration | Implemented | Google Places + Luma context enrichment is live; Strava abstraction path is wired for mobile OAuth + advisory trust normalization |
| Fluent Bit -> backend density ingestion | Implemented | Ingestion bridge is live and connected to density read path |
| Runtime distance signal | Implemented | Geographic distance estimation now powers decision scoring |
| TS/Python contract parity | Implemented | Boundary types are synchronized and guarded by CI checks |

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
  - Fluent Bit config and validation moved to `src/pipeline/` for cleaner service boundaries.
- **Geographic distance estimation:**
  - Replaced stubs with `estimate_distance_m` in `offer_decision.py` and `composite.py`.
- **Identity continuity:**
  - Server-side `continuity_id` derivation and reset controls are live.
- **Strava abstraction path:**
  - Mobile OAuth/token lifecycle helpers (`exchange`, `refresh`, `disconnect`) with secure token storage wrappers are live.
  - Mobile activity summarization maps Strava activity into abstracted intent fields only.
  - Backend advisory policy enforces source/signal consistency and confidence capping with provenance.
  - Decision trace now exposes activity confidence bands for explainability.
  - Source: `apps/mobile/src/api/strava.ts`, `apps/mobile/src/api/secureStore.ts`, `apps/mobile/src/local-llm/sourceSignals.ts`, `apps/api/src/spark/services/intent_trust.py`, `apps/api/src/spark/services/offer_decision.py`

---

## Gap Backlog (Actionable)

## 1) Dynamic Transit Gating (Refinement)

- **Goal:** Replace the 14-minute hardcode with a dynamic round-trip viability check.
- **Current:** `offer_decision.py` uses a hardcoded `min_round_trip_minutes = 14` for all merchants.
- **Required:**
  - Calculate `walking_time_min = (distance_m / 80)` (assuming 80m/min walking speed).
  - Add 5 minutes for "purchase/interaction buffer."
  - Only allow offer if `(walking_time_min * 2) + 5 <= transit_delay_minutes`.
- **Likely touchpoints:**
  - `apps/api/src/spark/services/offer_decision.py`

## 2) Long-horizon Identity Strategy

- **Goal:** Support cross-session stable pseudonyms with documented retention and user opt-out controls beyond transient sessions.
- **Current:** `identity_continuity.py` derives `continuity_id` but it is still largely session-bound in practice.
- **Required:**
  - Implement stable hashing strategy for longer-term preference linkage.
  - Add explicit "Identity Reset" clear-down in Neo4j.

## 3) Final Demo Data Cleanup

- **Goal:** Finalize Munich merchant list and Hero Score scaling for the live demo.
- **Touchpoint:** `README.md`, `resources/mock_venues_munich.json`.
- **Status:** Munich fixture is available; `README.md` placeholders need replacing.

---

## Suggested Build Order

1. **Dynamic Transit Gating** (High impact for demo realism).
2. **Final Demo Data replacement** in `README.md`.
3. **Long-horizon identity strategy refinement**.

---

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
