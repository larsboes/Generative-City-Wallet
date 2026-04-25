# Spark Backend

Real-time, context-aware local commerce offers powered by Payone density signals + Gemini Flash.

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
| `GEMINI_MODEL` | No | `gemini-2.5-flash-preview-05-20` | Gemini model string |
| `SPARK_DB_PATH` | No | `./spark.db` | SQLite database path |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/payone/density/{merchant_id}` | Density signal for a merchant |
| `GET` | `/api/payone/merchants` | All merchants with density |
| `POST` | `/api/context/composite` | Build composite context state |
| `POST` | `/api/offers/generate` | **Core pipeline** — generate offer |
| `POST` | `/api/conflict/resolve` | Standalone conflict resolution |
| `POST` | `/api/redemption/validate` | Validate QR code |
| `POST` | `/api/redemption/confirm` | Confirm redemption + cashback |
| `GET` | `/api/wallet/{session_id}` | Wallet balance + history |

## Demo Merchants

| ID | Name | Type |
|----|------|------|
| MERCHANT_001 | Café Römer | cafe |
| MERCHANT_002 | Bäckerei Wolf | bakery |
| MERCHANT_003 | Bar Unter | bar |
| MERCHANT_004 | Markthalle Bistro | restaurant |
| MERCHANT_005 | Club Schräglage | club |
