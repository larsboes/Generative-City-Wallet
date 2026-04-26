# `scripts/`

Repo-local tooling (not shipped in the Docker API image unless copied explicitly).

| Directory | Use |
|-----------|-----|
| **`ops/`** | Benchmarks, graph maintenance — safe targets for cron or manual ops runs |
| **`dev/`** | Smoke tests against a running API, CI guardrails |

Run Python scripts with repo root as cwd, e.g.:

```bash
uv run python infra/pipeline/graph-maintenance.py
uv run python scripts/dev/smoke_intent_vector.py
uv run python scripts/dev/smoke_local_llm.py
uv run python scripts/dev/check_architecture_boundaries.py
uv run python scripts/dev/check_service_sql_boundaries.py
```

See **`docs/DEVELOPMENT.md`** for the full command matrix.
