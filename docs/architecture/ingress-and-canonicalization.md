# Ingress and Canonicalization

Runtime ownership for mapping, normalization, and canonical contracts.

## Quick Navigation

- [Two mapping stages](#two-mapping-stages)
- [Decision rule](#decision-rule)
- [Current examples](#current-examples)

---

## Two mapping stages

### 1. Ingress normalization

Owned by Fluent Bit / Lua for event streams such as Payone ingestion.

Responsibilities:
- reject malformed records early
- coerce simple field types
- derive lightweight deterministic fields
- normalize stable aliases such as category names
- route dead-letter records without involving the app runtime

This stage should stay close to the transport payload and avoid app-domain rules.

### 2. Domain canonicalization

Owned by Python in `apps/api`.

Responsibilities:
- combine raw inputs with DB-authoritative state
- map semi-trusted inputs into typed runtime contracts
- apply product and liability rails
- persist audit metadata about rewritten/defaulted/dropped fields

This stage produces the objects the API returns or persists as canonical records.

### Runtime code links

| Stage | File |
|---|---|
| Fluent Bit ingress config | [`infra/fluentbit/fluent-bit.yaml`](../../infra/fluentbit/fluent-bit.yaml) |
| Payone ingest route | [`apps/api/src/spark/routers/payone.py`](../../apps/api/src/spark/routers/payone.py) |
| Offer rails canonicalization | [`apps/api/src/spark/services/hard_rails.py`](../../apps/api/src/spark/services/hard_rails.py) |
| Offer route orchestration | [`apps/api/src/spark/routers/offers.py`](../../apps/api/src/spark/routers/offers.py) |
| Transaction persistence | [`apps/api/src/spark/repositories/transactions.py`](../../apps/api/src/spark/repositories/transactions.py) |

---

## Decision rule

Use Lua when the rule:
- depends only on the event payload
- is deterministic and cheap
- improves ingress reliability or DLQ behavior

Use Python when the rule:
- depends on SQLite or Neo4j state
- shapes a public or persisted contract
- expresses offer/business policy
- needs explainability or audit metadata

---

## Current examples

- Fluent Bit Lua:
  - required Payone fields
  - canonical category aliases
  - derived hour/day buckets
- Python canonicalization:
  - `hard_rails.py` builds `OfferObject` from `LLMOfferOutput` plus DB truth
  - redemption reads stored `final_offer` through a typed canonical parser
  - venue transactions are normalized before SQLite insert

> [!TIP]
> If the rule needs database truth, public API contract semantics, or explainability metadata, keep it in Python services/routers, not Lua.
