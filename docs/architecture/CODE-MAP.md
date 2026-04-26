# Code Map

Quick placement guide for new work. If you are unsure where code belongs, start here.

> [!TIP]
> Pair this with [`ARCHITECTURE-GUARDRAILS.md`](./ARCHITECTURE-GUARDRAILS.md) during implementation and review.

---

## Where to place code

| You are adding | Place it in | Avoid |
|---|---|---|
| New API endpoint / request-response wiring | `apps/api/src/spark/routers/` | Embedding business policy in router |
| Pure domain scoring rule or category constant | `apps/api/src/spark/services/scoring_rules.py` | Burying pure functions inside orchestration services |
| Repository interface (ABC) | `apps/api/src/spark/domain/interfaces.py` | Concrete implementations in domain layer |
| Deterministic business rule or ranking logic | `apps/api/src/spark/services/` | SQL or HTTP-specific code in service |
| Wave rate-limit policy | `apps/api/src/spark/services/wave_rate_limiter.py` | Rate logic in the repository |
| SQL reads/writes and persistence helpers | `apps/api/src/spark/repositories/` | Response formatting in repository |
| Graph event idempotency / event log | `apps/api/src/spark/repositories/graph_event.py` | Mixed with wallet or redemption logic |
| Preference attribution / learning metrics | `apps/api/src/spark/repositories/preference_event.py` | Mixed with redemption flows |
| Cross-session identity linking | `apps/api/src/spark/repositories/identity.py` | Mixed with HMAC token logic |
| New typed payload/model/contract | `apps/api/src/spark/models/` | Runtime side effects in models |
| Venue/occupancy/density/Payone signal models | `apps/api/src/spark/models/demand.py` | Adding demand models to transactions.py |
| Vendor dashboard / analytics models | `apps/api/src/spark/models/vendor.py` | Adding dashboard models to transactions.py |
| Transaction generation request/response | `apps/api/src/spark/models/transactions.py` | Vendor or demand models here |
| DB bootstrap/schema connection code | `apps/api/src/spark/db/` | Decision logic in `db` |
| LLM/tool orchestration adapter logic | `apps/api/src/spark/agents/` | Canonical domain policy in agents |
| Ingress runtime config/Lua filter | `infra/pipeline/` | Business policy in Lua that needs DB truth |
| Shared TS boundary types | `packages/shared/src/contracts.ts` | App-local copies of boundary types |
| Architecture rationale and runtime flow | `docs/architecture/` | Leaving architecture changes undocumented |

---

## Model file index

| File | What lives there |
|---|---|
| `models/demand.py` | `Venue`, `DemandContext`, `OccupancyResponse/QueryRequest/QueryResponse`, `PayoneIngestRequest/Response`, `PayoneDensityResponse/MerchantDensityResponse` |
| `models/vendor.py` | `HourlyTransactionBucket`, `DailyTransactionsResponse`, `HourlyAverageBucket`, `TransactionAveragesResponse`, `RevenueDay`, `RevenueLast7DaysResponse`, `HourRankingBucket`, `HourRankingsResponse`, `DashboardHourlyBucket`, `VendorDashboardTodayResponse` |
| `models/transactions.py` | `TransactionGenerationRequest`, `LiveUpdateRequest`, `TransactionGenerationResponse` |
| `models/context.py` | `CompositeContextState` and all its sub-contexts |
| `models/offers.py` | `OfferObject`, `ExplainabilityReason`, LLM output models |
| `models/redemption.py` | QR, wallet, outcome models |
| `models/wave.py` | Spark Wave request/response models |

---

## Repository file index

| File | What lives there |
|---|---|
| `repositories/redemption.py` | Wallet ops, QR/offer outcome, `ensure_graph_learning_schema` |
| `repositories/graph_event.py` | Graph event idempotency log, event counts, cleanup |
| `repositories/preference_event.py` | Preference attribution log, learning metrics |
| `repositories/identity.py` | Cross-session identity links (`identity_links` table) |
| `repositories/wave.py` | Wave records, milestone tracking, TTL expiry |
| `repositories/offer_decision.py` | Candidate merchant queries, session offer state |
| `repositories/density.py` | Payone transaction stats, historical rates |
| `repositories/venues.py` | Venue metadata queries |

---

## Feature templates (fast routing)

### OCR transit delay enrichment
- API intake: [`apps/api/src/spark/routers/ocr.py`](../../apps/api/src/spark/routers/ocr.py)
- delay window policy + gating: [`apps/api/src/spark/services/ocr_transit.py`](../../apps/api/src/spark/services/ocr_transit.py), [`apps/api/src/spark/services/offer_decision.py`](../../apps/api/src/spark/services/offer_decision.py)
- payload fields: [`apps/api/src/spark/models/ocr.py`](../../apps/api/src/spark/models/ocr.py), [`packages/shared/src/contracts.ts`](../../packages/shared/src/contracts.ts)
- tests: [`tests/unit`](../../tests/unit), [`tests/integration`](../../tests/integration)

### Wallet pass cold-start seeding
- ingestion endpoint: [`apps/api/src/spark/routers/graph.py`](../../apps/api/src/spark/routers/graph.py)
- seed policy/idempotency orchestration: [`apps/api/src/spark/services/wallet_seed.py`](../../apps/api/src/spark/services/wallet_seed.py)
- graph persistence and metadata: [`apps/api/src/spark/graph/repository.py`](../../apps/api/src/spark/graph/repository.py)
- contracts: [`apps/api/src/spark/models`](../../apps/api/src/spark/models), [`packages/shared/src/contracts.ts`](../../packages/shared/src/contracts.ts)

### Spark Wave social coordination
- endpoints and lifecycle orchestration: [`apps/api/src/spark/routers/wave.py`](../../apps/api/src/spark/routers/wave.py)
- rate-limit policy: [`apps/api/src/spark/services/wave_rate_limiter.py`](../../apps/api/src/spark/services/wave_rate_limiter.py)
- data access: [`apps/api/src/spark/repositories/wave.py`](../../apps/api/src/spark/repositories/wave.py)
- persistence schema: [`apps/api/src/spark/db/schema.sql`](../../apps/api/src/spark/db/schema.sql)
- integration coverage: [`tests/integration/test_wave_flow.py`](../../tests/integration/test_wave_flow.py)

### Fluent Bit → backend ingestion E2E
- ingestion config and Lua validation filter: [`infra/pipeline/`](../../infra/pipeline)
- backend sink/path alignment: [`apps/api/src/spark/routers/payone.py`](../../apps/api/src/spark/routers/payone.py), [`apps/api/src/spark/services/density.py`](../../apps/api/src/spark/services/density.py), [`apps/api/src/spark/repositories/transactions.py`](../../apps/api/src/spark/repositories/transactions.py)
- coverage: [`tests/integration/test_payone_ingest_e2e.py`](../../tests/integration/test_payone_ingest_e2e.py)

### Offer scoring rules
- pure scoring functions + category sets: [`apps/api/src/spark/services/scoring_rules.py`](../../apps/api/src/spark/services/scoring_rules.py)
- scoring orchestration: [`apps/api/src/spark/services/offer_decision.py`](../../apps/api/src/spark/services/offer_decision.py)
- tests: [`tests/unit/test_offer_decision.py`](../../tests/unit/test_offer_decision.py)

### Identity erasure (GDPR right to erasure)
- endpoint: `POST /api/v1/identity/profile/clear` in [`apps/api/src/spark/routers/identity.py`](../../apps/api/src/spark/routers/identity.py)
- Neo4j erasure: [`apps/api/src/spark/graph/store/ops.py`](../../apps/api/src/spark/graph/store/ops.py) (`purge_session_data` / `clear_session_data`)
- SQLite identity link removal: [`apps/api/src/spark/repositories/identity.py`](../../apps/api/src/spark/repositories/identity.py)

---

## PR checklist (placement)

- [ ] Code is in the correct layer per `ARCHITECTURE-GUARDRAILS.md`.
- [ ] New or changed cross-boundary fields are mirrored in `packages/shared`.
- [ ] New models go in the correct model file (`demand`, `vendor`, or `transactions`).
- [ ] Tests cover deterministic behavior and failure path.
- [ ] Docs under `docs/architecture/` are updated for flow changes.
