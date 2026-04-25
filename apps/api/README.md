# Spark API (`spark` Python package)

FastAPI service under `apps/api/src/spark/`. Run from **repository root** with `PYTHONPATH` so imports resolve:

```bash
uv sync
PYTHONPATH=apps/api/src uv run uvicorn spark.main:app --reload --port 8000
```

Or use the root script: `npm run dev:api` (after `npm install` at repo root).

**Seed DB manually:**

```bash
PYTHONPATH=apps/api/src uv run python -m spark.db.seed
```

**Smoke-test IntentVector → API:**

```bash
uv run python scripts/dev/smoke_intent_vector.py
SPARK_API_BASE=http://127.0.0.1:8000 uv run python scripts/dev/smoke_intent_vector.py --generate
```

---

Full endpoint list, env table, and Neo4j notes: see **[`../../docs/REPOSITORY-OVERVIEW.md`](../../docs/REPOSITORY-OVERVIEW.md)** and **[`../../docs/USER-KNOWLEDGE-GRAPH-NEO4J.md`](../../docs/USER-KNOWLEDGE-GRAPH-NEO4J.md)**.

Environment variables are defined in `apps/api/src/spark/config.py` (including `OFFER_LLM_PROVIDER`, `OLLAMA_*`, `NEO4J_*`, `GRAPH_*`).

## Demo merchants

| ID | Name | Type |
|----|------|------|
| MERCHANT_001 | Café Römer | cafe |
| MERCHANT_002 | Bäckerei Wolf | bakery |
| MERCHANT_003 | Bar Unter | bar |
| MERCHANT_004 | Markthalle Bistro | restaurant |
| MERCHANT_005 | Club Schräglage | club |
