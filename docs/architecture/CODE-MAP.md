# Code Map

Quick placement guide for new work. If you are unsure where code belongs, start here.

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
- API intake: `routers/`
- delay window policy + gating: `services/`
- payload fields: `models/contracts.py` + `packages/shared`
- tests: `tests/unit` + `tests/integration`

### Wallet pass cold-start seeding
- ingestion endpoint: `routers/`
- seed policy/idempotency orchestration: `services/`
- graph persistence and metadata: `graph/repository.py`
- contracts: `models` + `packages/shared`

### Spark Wave social coordination
- endpoints and lifecycle orchestration: `routers/` + `services/`
- persistence schema: `db/schema.sql` (+ migrations as needed)
- integration coverage: `tests/integration`

### Fluent Bit -> backend ingestion E2E
- ingestion config and filter validation: `infra/fluentbit/`
- backend sink/path alignment: `services/` + `repositories/`
- coverage: integration test proving density impact

---

## PR checklist (placement)

- [ ] Code is in the correct layer per `ARCHITECTURE-GUARDRAILS.md`.
- [ ] New or changed cross-boundary fields are mirrored in `packages/shared`.
- [ ] Tests cover deterministic behavior and failure path.
- [ ] Docs under `docs/architecture/` are updated for flow changes.
