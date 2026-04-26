# Architecture Guardrails

This file defines the code-structure rules that keep Spark aligned with a clean, DDD-inspired architecture.

Use this as the default for new features and refactors.

---

## Layer model

1. `routers` (transport/API)
2. `services` (application/domain orchestration + policy)
3. `repositories` (persistence adapters)
4. `models` (typed contracts and domain value shapes)
5. `db` (connection/bootstrap/schema-only helpers)
6. `agents` (LLM/tool orchestration adapters)

Principle: depend inward on stable abstractions; avoid coupling lower-level modules to higher-level transport/adaptation layers.

---

## Boundary rules (enforced)

- `spark.models` must not import `spark.routers`, `spark.services`, or `spark.agents`.
- `spark.services` must not import `spark.routers`.
- `spark.db` must not import `spark.routers`, `spark.services`, or `spark.agents`.
- `spark.repositories` must not import `spark.routers` or `spark.agents`.

CI guard:
- `scripts/dev/check_architecture_boundaries.py`
- `scripts/dev/check_service_sql_boundaries.py`
- `scripts/dev/check_router_boundaries.py`
- run in `.github/workflows/ci.yml`

If a new dependency direction is required, update this file and the guard script in the same PR with rationale.

Router guard policy:
- Default is strict: routers must not import `spark.repositories.*` and must not call `get_connection()`.
- If a temporary exception is needed, prefer introducing a narrow service wrapper first.
- If an exception is truly unavoidable, document rationale in this file and update `check_router_boundaries.py` in the same PR.

Direct SQL in services:
- Target state: persistence SQL lives in `spark.repositories`, not in `spark.services`.
- Enforcement is incremental: `check_service_sql_boundaries.py` blocks new direct SQL usage in non-allowlisted service files.
- Legacy service exceptions are explicitly tracked in the checker until refactored.

---

## Ownership by package

- `apps/api/src/spark/routers/`
  - HTTP concerns only: request parsing, response shape, status codes.
  - No business decision logic beyond orchestration.
- `apps/api/src/spark/services/`
  - Deterministic policy and orchestration.
  - Composition of graph/service/repository calls.
- `apps/api/src/spark/repositories/`
  - SQL-backed persistence reads/writes.
  - No API concerns.
- `apps/api/src/spark/graph/store/`
  - Neo4j persistence modules scoped to the graph bounded context.
  - Used by `spark.graph.repository` facade, not by HTTP routers directly.
  - Naming distinction is intentional:
    - `spark.repositories` = app SQLite repositories
    - `spark.graph.store` = graph (Neo4j) persistence modules
- `apps/api/src/spark/models/`
  - Typed contracts and model boundaries.
  - Keep deterministic and side-effect free.
- `apps/api/src/spark/db/`
  - Connection, schema, bootstrap.
  - No domain decisions.
- `apps/api/src/spark/agents/`
  - Agent model/tool invocation and adaptation to canonical offer models.

---

## Definition of done for architecture-safe features

For each feature PR:

1. Place code in the correct layer per ownership rules.
2. Keep cross-boundary types aligned (`spark.models.contracts` and `packages/shared` where relevant).
3. Add or update deterministic tests (`tests/unit` and/or `tests/integration`).
4. Update runtime docs under `docs/architecture/` when boundaries or flow change.
5. Keep `decision_trace` / explainability metadata for behavior-changing logic.

---

## Bounded context map (lightweight)

- `OfferDecision` — deterministic ranking, hard blocks, thresholds.
- `ContextComposition` — merges user intent, merchant demand, weather, and trace.
- `GraphPersonalization` — preference scores, graph rule gate, reinforcement.
- `IngestionAndDensity` — event intake and occupancy/density signals.
- `RedemptionAndWallet` — lifecycle outcomes, idempotency, credits.
- `AgentFraming` — LLM-generated framing constrained by hard rails.

Keep each context cohesive and avoid leaking transport/storage details into domain policy code.
