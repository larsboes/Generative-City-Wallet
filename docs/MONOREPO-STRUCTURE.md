# Monorepo structure — Spark

Single reference for **where code lives**, **how to run it**, and **rules** that keep the TypeScript + Python split maintainable.

For backend depth (routers, Neo4j, hybrid pipeline), see **[`REPOSITORY-OVERVIEW.md`](REPOSITORY-OVERVIEW.md)**.

---

## Layout

```
Generative-City-Wallet/
├── apps/
│   ├── api/src/spark/       # FastAPI — import package `spark` (PYTHONPATH=apps/api/src)
│   ├── mobile/              # Expo consumer (@spark/mobile)
│   └── web-dashboard/       # Vite merchant UI (@spark/web-dashboard)
├── packages/
│   └── shared/              # @spark/shared — TS contracts (source of truth for JS)
├── tests/
│   ├── unit/                # Fast, isolated pytest modules
│   ├── integration/         # API / graph / composite flows
│   └── conftest.py          # Shared fixtures (applies to all subdirs)
├── scripts/
│   ├── ops/                 # Cron / benchmarks / production-adjacent tooling
│   └── dev/                 # Local smoke + CI guardrails
├── docs/                    # Implementation docs (this file, overview, Neo4j)
├── data/                    # SQLite + optional local Neo4j data paths
├── pyproject.toml           # Python deps + pytest (pythonpath includes apps/api/src)
├── package.json             # npm workspaces + root scripts
└── turbo.json               # turbo task graph (build, typecheck, lint)
```

---

## Package ownership

| Area | Owns | Consumes |
|------|------|-----------|
| **`apps/api`** | HTTP API, SQLite, Neo4j graph, offer pipeline | `@spark/shared` **not** imported — mirror contracts in `spark.models.contracts` |
| **`apps/mobile`** | Expo UI, on-device flows | `@spark/shared` for request/response shapes |
| **`apps/web-dashboard`** | Merchant UI | `@spark/shared` + `VITE_*` env when wired |
| **`packages/shared`** | TypeScript types only | Nothing from `apps/*` |

---

## Import rules

1. **Mobile and dashboard** must take boundary types from **`@spark/shared`**, not by copying shapes into each app.
2. **Python** must not import `packages/shared`; parity is enforced by **review** + **`scripts/dev/check_contract_symbols.py`** in CI (extend the symbol list when you add cross-boundary types).
3. **Known gap:** `CompositeContextState` exists in **`spark.models.contracts`** but is not yet exported from **`packages/shared/src/contracts.ts`**. Add it to shared when the mobile/dashboard surfaces need it, then add the name to the guard script list.

---

## Commands (from repo root)

### Development

| Command | What |
|---------|------|
| `npm run dev:api` | FastAPI + uvicorn reload on `:8000` |
| `npm run dev:mobile` | Expo dev server |
| `npm run dev:dashboard` | Vite dev server on `:3000` |

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
| `scripts/dev/check_contract_symbols.py` | CI: TS/Python contract name alignment |

See **`scripts/README.md`** for one-line descriptions.

---

## Turbo notes

- **`build`**: `outputs: []` so packages that only typecheck (e.g. `@spark/shared`) or echo a placeholder (`@spark/mobile`) do not produce Turbo “missing outputs” warnings. Tradeoff: Vite `dist/` is not listed as a cache artifact at the Turbo layer; the dashboard build still writes `apps/web-dashboard/dist/` on disk.
- **`typecheck`** / **`lint`**: defined per JS workspace; root runs them via `npm run typecheck` / `npm run lint:js`.

---

## CI alignment

`.github/workflows/ci.yml` runs, in order: Python ruff + format + pyright → **Node** `npm ci` → **`npm run typecheck`** → **`npm run test:contracts`** → pytest (test job) → Docker.

Keep **root `package-lock.json`** committed so `npm ci` is reproducible.

---

## See also

| Doc | When |
|-----|------|
| [`REPOSITORY-OVERVIEW.md`](REPOSITORY-OVERVIEW.md) | Backend modules, scripts table, tests detail |
| [`README.md`](../README.md) | Product + Graph Ops cron example |
| [`apps/api/README.md`](../apps/api/README.md) | API quick start |
