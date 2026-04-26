# Code Map

Quick placement guide for new work. If you are unsure where code belongs, start here.

> [!TIP]
> Pair this with [`ARCHITECTURE-GUARDRAILS.md`](./ARCHITECTURE-GUARDRAILS.md) during implementation and review.

---

## Where to place code

| You are adding | Place it in | Avoid |
|---|---|---|
| New API endpoint / request-response wiring | `apps/api/src/spark/routers/` | Embedding business policy in router |
| Deterministic business rule or ranking logic | `apps/api/src/spark/services/` | SQL or HTTP-specific code in service |
| SQL reads/writes and persistence helpers | `apps/api/src/spark/repositories/` | Response formatting in repository |
| New typed payload/model/contract | `apps/api/src/spark/models/` | Runtime side effects in models |
| DB bootstrap/schema connection code | `apps/api/src/spark/db/` | Decision logic in `db` |
| LLM/tool orchestration adapter logic | `apps/api/src/spark/agents/` | Canonical domain policy in agents |
| Ingress runtime config/Lua filter | `infra/fluentbit/` | Business policy in Lua that needs DB truth |
| Shared TS boundary types | `packages/shared/src/contracts.ts` | App-local copies of boundary types |
| Architecture rationale and runtime flow | `docs/architecture/` | Leaving architecture changes undocumented |

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
- endpoints and lifecycle orchestration: [`apps/api/src/spark/routers/wave.py`](../../apps/api/src/spark/routers/wave.py), [`apps/api/src/spark/repositories/wave.py`](../../apps/api/src/spark/repositories/wave.py)
- persistence schema: [`apps/api/src/spark/db/schema.sql`](../../apps/api/src/spark/db/schema.sql) (+ migrations as needed)
- integration coverage: [`tests/integration/test_wave_flow.py`](../../tests/integration/test_wave_flow.py)

### Fluent Bit -> backend ingestion E2E
- ingestion config and filter validation: [`infra/fluentbit`](../../infra/fluentbit)
- backend sink/path alignment: [`apps/api/src/spark/routers/payone.py`](../../apps/api/src/spark/routers/payone.py), [`apps/api/src/spark/services/density.py`](../../apps/api/src/spark/services/density.py), [`apps/api/src/spark/repositories/transactions.py`](../../apps/api/src/spark/repositories/transactions.py)
- coverage: integration test proving density impact

---

## PR checklist (placement)

- [ ] Code is in the correct layer per `ARCHITECTURE-GUARDRAILS.md`.
- [ ] New or changed cross-boundary fields are mirrored in `packages/shared`.
- [ ] Tests cover deterministic behavior and failure path.
- [ ] Docs under `docs/architecture/` are updated for flow changes.
