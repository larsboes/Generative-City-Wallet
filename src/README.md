# Spark Backend

Real-time, context-aware local commerce offers powered by Payone density signals + Gemini Flash.

**Full repo map (routers, stores, CI, hybrid agent path):** [`../docs/REPOSITORY-OVERVIEW.md`](../docs/REPOSITORY-OVERVIEW.md) · **Neo4j user graph:** [`../docs/USER-KNOWLEDGE-GRAPH-NEO4J.md`](../docs/USER-KNOWLEDGE-GRAPH-NEO4J.md)

## Quick Start

```bash
# Install deps
uv sync

# Run (auto-seeds DB on first launch)
uv run uvicorn src.backend.main:app --reload --port 8000

# Or seed manually
uv run python -m src.backend.db.seed
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_AI_API_KEY` | No | _(fallback mode)_ | Gemini Flash API key |
| `OPENWEATHER_API_KEY` | No | _(Stuttgart defaults)_ | OpenWeatherMap API key |
| `GEMINI_MODEL` | No | see `config.py` | Gemini model string |
| `SPARK_DB_PATH` | No | `data/spark.db` (from project root) | SQLite database path |
| `AGENT_ENABLED` | No | `auto` | Strands OfferAgent: `auto` / `true` / `false` |
| `NEO4J_*`, `GRAPH_*` | No | defaults in `config.py` | Optional user graph + rule thresholds — see docs |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check (+ Neo4j metrics when enabled) |
| `GET` | `/api/payone/density/{merchant_id}` | Density signal for a merchant |
| `GET` | `/api/payone/merchants` | All merchants with density |
| `POST` | `/api/context/composite` | Build composite context state |
| `POST` | `/api/offers/generate` | **Core pipeline** — hybrid agent + graph rules + offer |
| `POST` | `/api/conflict/resolve` | Standalone conflict resolution |
| `POST` | `/api/redemption/validate` | Validate QR code |
| `POST` | `/api/redemption/confirm` | Confirm redemption + cashback + graph |
| `POST` | `/api/offers/{offer_id}/outcome` | Decline / expire / accept outcome → graph |
| `GET` | `/api/wallet/{session_id}` | Wallet balance + history |
| `GET` | `/api/graph/health` | Neo4j availability + query metrics |
| `GET` | `/api/graph/stats` | Graph node/edge counts |
| `GET` | `/api/graph/migrations` | Applied graph migrations |
| `GET` | `/api/graph/sessions/{id}/preferences` | Top preference scores |
| `GET` | `/api/graph/sessions/{id}/recent-offers` | Recent offers (debug) |
| `POST` | `/api/graph/cleanup` | Retention cleanup |
| `POST` | `/api/graph/decay-preferences` | Stale preference decay |

## Demo Merchants

| ID | Name | Type |
|----|------|------|
| MERCHANT_001 | Café Römer | cafe |
| MERCHANT_002 | Bäckerei Wolf | bakery |
| MERCHANT_003 | Bar Unter | bar |
| MERCHANT_004 | Markthalle Bistro | restaurant |
| MERCHANT_005 | Club Schräglage | club |
