# 22 — FluentBit Payone Ingestion Pipeline

FluentBit as the ingestion layer for Payone transaction webhooks. Receives, validates, writes to the database, and fans out notifications. Density computation stays in Python.

## Why

The backend seeds synthetic hourly buckets at startup. When Payone sends real webhooks, something needs to sit between the webhook and the database: validate payloads, normalize into the existing schema, write to storage, and optionally notify the backend that new data arrived. FluentBit does this as a lightweight sidecar with zero application code changes.

## Architecture

```
  Payone Webhooks ──► FluentBit (:8888)
                         │
                         ├─ FILTER: validate.lua (drop malformed, add time fields)
                         │
                         ├─ OUTPUT: stdout (dev) / PostgreSQL (prod)
                         ├─ OUTPUT: Redis PUBLISH spark:txn (notify backend)
                         └─ OUTPUT: file DLQ (failed writes)

  FastAPI Backend (unchanged)
    ├─ density.py queries payone_transactions as before
    ├─ optional: Redis SUB spark:txn → trigger proactive density recheck
    └─ everything else untouched
```

## Lua Filter

One filter. Validates required fields, computes the time-of-week columns the `payone_transactions` schema expects, drops bad records.

## Docker

FluentBit sidecar + Redis added to docker-compose. Backend unchanged.

## Event Generator

Python script that simulates Payone webhooks by posting individual transaction events to FluentBit's HTTP input for development and testing.
