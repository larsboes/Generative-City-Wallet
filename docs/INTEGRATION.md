# Frontend ↔ Backend Integration

This repo contains two independent applications that are not yet wired together.

| App | Location | Stack | Data source |
|---|---|---|---|
| **Consumer + Merchant UI** | `Frontend Spark/` | React / Vite / Supabase | Supabase DB + Edge Functions |
| **AI Inference Backend** | `apps/api/` | FastAPI / Neo4j / SQLite | Payone density signals |

---

## Current state

The `Frontend Spark/` app is fully functional as a standalone Supabase-native app. It handles auth, offer display, QR redemption, and the merchant dashboard entirely through Supabase.

The FastAPI backend (`apps/api/`) is the deterministic offer engine — context assembly, graph rule gates, Gemini generation, hard rails, preference learning.

They are not yet connected. The frontend's `suggest-offers` Supabase edge function calls an AI gateway directly; the FastAPI pipeline is not invoked.

---

## Handshake point

When connecting them, the entry point is:

**`POST /api/v1/offers/generate`** — accepts a `GenerateOfferRequest` (defined in `packages/shared/src/contracts.ts`).

The frontend would:
1. Build an `IntentVector` from geolocation (`useGeolocation` hook) + user prefs from Supabase
2. Call `POST /api/v1/offers/generate` instead of querying Supabase offers directly
3. Display the returned `OfferObject` (same shape already in `contracts.ts`)

The Supabase edge function `suggest-offers` would be replaced or bypassed by this call.

---

## Environment variables needed

Add to `Frontend Spark/.env.local`:
```
VITE_SPARK_API_BASE=http://localhost:8000
```

The client entry point in `apps/mobile/src/api/spark.ts` already shows the pattern.
