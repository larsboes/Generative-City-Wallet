# Development — Spark

This document covers package boundaries, how to run the codebase locally, CI/CD, and active technical debt.
For architecture and data flows, see **[`ARCHITECTURE.md`](ARCHITECTURE.md)**.

---

## Package ownership & Import rules

| Area | Owns | Consumes |
|------|------|-----------|
| **`apps/api`** | HTTP API, SQLite, Neo4j graph, offer pipeline | `@spark/shared` **not** imported — mirror contracts in `spark.models.contracts` |
| **`apps/mobile`** | Expo UI, on-device flows | `@spark/shared` for request/response shapes |
| **`apps/web-dashboard`** | Merchant UI | `@spark/shared` + `VITE_*` env when wired |
| **`packages/shared`** | TypeScript types only | Nothing from `apps/*` |

1. **Mobile and dashboard** must take boundary types from **`@spark/shared`**, not by copying shapes into each app.
2. **Python** must not import `packages/shared`; parity is enforced by **review** + **`scripts/dev/check_contract_symbols.py`** in CI (extend the symbol list when you add cross-boundary types).
3. Keep `packages/shared/src/contracts.ts` aligned with `apps/api/src/spark/models/contracts.py` for all cross-boundary types consumed by mobile/dashboard.
4. Inside Python, prefer narrow imports from `spark.models.api`, `spark.models.context`, `spark.models.offers`, `spark.models.transactions`, `spark.models.redemption`, and `spark.models.conflict`. Treat `spark.models.contracts` as a compatibility barrel for legacy imports.
5. Keep `spark.db` narrow: connections, schema bootstrap, and DB package scaffolding. Put SQL-backed persistence operations in `spark.repositories`.

## Repository layout conventions

- **Application code** lives under `apps/` (API, mobile, dashboard).
- **Shared TypeScript contracts/types** live under `packages/`.
- **Developer/ops scripts** live under `scripts/`.
- **Infrastructure assets** (container/runtime configs, pipeline assets) live under `infra/`.

Examples:
- Fluent Bit assets: `infra/fluentbit/`
- Graph ops scripts: `scripts/ops/`

---

## Commands (from repo root)

### Development

| Command | What |
|---------|------|
| `npm run dev:api` | FastAPI + uvicorn reload on `:8000` |
| `npm run dev:mobile` | Expo dev server |
| `npm run dev:dashboard` | Vite dev server on `:3000` |

### Taskfile quick reference

`Taskfile.yml` provides shortcut wrappers for common demo/test workflows.

| Command | What |
|---------|------|
| `task --list` | List all available tasks |
| `task dev:api` | FastAPI + uvicorn reload on `:8000` |
| `task demo:load-munich` | Reset DB and load Munich demo data into both pipelines |
| `task demo:seed-legacy` | Run legacy Stuttgart seed path |
| `task lint:api` | Ruff lint + format check |
| `task test:contracts` | Contract symbol parity check |
| `task test:api` | Python test suite |
| `task verify` | Run core local gates (`test:contracts`, `test:api`) |

### Quality gates

| Command | What |
|---------|------|
| `npm run lint` | Ruff (Python) + `turbo run lint` (JS workspaces) |
| `npm run lint:api` | `ruff check` + format check on API, tests, scripts |
| `npm run lint:js` | `turbo run lint` |
| `npm run typecheck` | `turbo run typecheck` (all workspaces that define it) |
| `npm run typecheck:web` | Dashboard only |
| `npm run typecheck:mobile` | Mobile only |
| `npm run typecheck:shared` | Shared contracts only |
| `npm run test` | pytest **+** contract symbol guard |
| `npm run test:api` | pytest only (set `SPARK_DB_PATH=:memory:` locally or in CI for isolation) |
| `npm run test:contracts` | `check_contract_symbols.py` |
| `uv run python scripts/dev/check_architecture_boundaries.py` | CI/local architecture import-boundary guard |
| `uv run python scripts/dev/check_service_sql_boundaries.py` | CI/local guard: prevent new direct SQL in services |
| `npm run build` | `turbo run build` |

### Python-only (when you prefer `uv` directly)

| Command | What |
|---------|------|
| `uv sync --dev` | Install Python + dev tools |
| `uv run pytest tests/ -v` | Tests (`SPARK_DB_PATH=:memory:` in CI) |
| `uv run ruff check apps/api/src/spark tests scripts` | Lint |
| `uv run pyright apps/api/src/spark/` | Types |

### Scripts

| Path | Purpose |
|------|---------|
| `scripts/ops/run_graph_maintenance.py` | Neo4j cleanup + preference decay (cron-friendly) |
| `scripts/ops/benchmark_offer_latency.py` | p95 offer latency Neo4j on vs off |
| `scripts/dev/smoke_intent_vector.py` | POST sample intent to running API |
| `scripts/dev/smoke_local_llm.py` | Validates local-LLM fixtures + parser rates |
| `scripts/dev/check_contract_symbols.py` | CI: TS/Python contract name alignment |
| `scripts/dev/check_architecture_boundaries.py` | CI: clean-architecture import boundary enforcement |
| `scripts/dev/check_service_sql_boundaries.py` | CI: blocks new direct SQL usage in services (incremental rollout) |

---

## Docker & CI Alignment

### Docker
- **`Dockerfile`:** Python 3.12 slim, `uv sync --frozen`, copies `apps/api/src/spark`, sets `PYTHONPATH`, runs uvicorn `spark.main:app` on `8000`.
- **`docker-compose.yml`:** `backend` + `redis` + `fluentbit` + `neo4j` services, `.env` for backend, mounts `./data` → `/app/data`.
- Backend graph env is pinned for container networking (`NEO4J_URI=bolt://neo4j:7687`) and waits for Neo4j health (`depends_on: condition: service_healthy`).

Run the Docker stack from repo root:

```bash
docker compose up -d --build
docker compose logs -f backend
docker compose down
```

Default Fluent Bit host bindings are `8889 -> 8888` and `2021 -> 2020`.
If those host ports are occupied, override them at startup:

```bash
FLUENTBIT_HTTP_PORT=8890 FLUENTBIT_METRICS_PORT=2022 docker compose up -d --build
```

Verify full system (including graph):

```bash
curl -s http://localhost:8000/api/health | jq .graph
curl -s http://localhost:8000/api/graph/health | jq .
```

Full reset (including volumes):

```bash
docker compose down -v
```

### CI Workflow (`.github/workflows/ci.yml`)
Runs, in order: Python ruff + format + pyright + architecture boundary guard + service SQL boundary guard → **Node** `npm ci` → **`npm run typecheck`** → **`npm run test:contracts`** → pytest (test job) → Docker.
Keep **root `package-lock.json`** committed so `npm ci` is reproducible.

### Turbo notes
- **`build`**: `outputs: []` so packages that only typecheck (e.g. `@spark/shared`) or echo a placeholder (`@spark/mobile`) do not produce Turbo “missing outputs” warnings. 
- **`typecheck`** / **`lint`**: defined per JS workspace; root runs them via `npm run typecheck` / `npm run lint:js`.

---

## Active Tech Debt

### Open items
- **Pyright baseline (API package)**
  - **Scope:** `apps/api/src/spark/`
  - **Current status:** `uv run pyright apps/api/src/spark/` reports **28 errors**.
  - **Hotspots:** `agents/agent.py`, `graph/repository.py`, `graph/{migrations,schema}.py`, `services/{composite,offer_generator}.py`, `routers/vendors.py`.
  - **Tracking note:** address in a dedicated typing pass.

- **Contract parity drift (Python vs TS)**
  - Enforce parity through `scripts/dev/check_contract_symbols.py` and review when adding new boundary contracts.

- **Planning-to-implementation deltas**
  - Advanced signals from planning (`OCR transit scan`, `wallet seed`, `Spark Wave`) are still mostly design-stage.
  - Track these as explicit implementation epics instead of implicit planning carry-over.

---

## Release Note: Post-workout deterministic rollout

The deterministic decision engine now includes movement-aware scoring and retry behavior for `post_workout`:

- recovery-category boost (e.g. `cafe`, `bakery`, `juice_bar`, `smoothie_bar`, `healthy_cafe`)
- nightlife suppression (`bar`, `club`, `nightclub`)
- shorter `recheck_in_minutes` for `DO_NOT_RECOMMEND` in post-workout context

### Manual verification (API)

Assumes API is running on `http://localhost:8000`.

1) **Positive path (post-workout should favor recovery categories)**

```bash
curl -s -X POST http://localhost:8000/api/offers/generate \
  -H "Content-Type: application/json" \
  -d '{
    "intent": {
      "grid_cell": "STR-MITTE-047",
      "movement_mode": "post_workout",
      "time_bucket": "sunday_morning_coffee",
      "weather_need": "neutral",
      "social_preference": "quiet",
      "price_tier": "mid",
      "recent_categories": ["healthy_cafe"],
      "dwell_signal": true,
      "battery_low": false,
      "session_id": "verify-post-workout-001"
    }
  }'
```

Expected:
- `recommendation` is `RECOMMEND` or `RECOMMEND_WITH_FRAMING`
- `decision_trace.trace` includes `movement_category_adjustment`

2) **Blocked path (`exercising` still hard-blocks)**

```bash
curl -s -X POST http://localhost:8000/api/offers/generate \
  -H "Content-Type: application/json" \
  -d '{
    "intent": {
      "grid_cell": "STR-MITTE-047",
      "movement_mode": "exercising",
      "time_bucket": "sunday_morning_coffee",
      "weather_need": "neutral",
      "social_preference": "quiet",
      "price_tier": "mid",
      "recent_categories": [],
      "dwell_signal": false,
      "battery_low": false,
      "session_id": "verify-exercising-block-001"
    }
  }'
```

Expected:
- `recommendation` is `DO_NOT_RECOMMEND`
- top trace code is `movement_hard_block`
- response includes `recheck_in_minutes`
