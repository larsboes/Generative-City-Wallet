# LLM and Hard Rails

Safety and boundary model for generated offer content.

## Quick Navigation

- [Core boundary](#core-boundary)
- [Hard rail checks](#hard-rail-checks)
- [What LLM cannot decide](#what-llm-cannot-decide)
- [Failure and fallback](#failure-and-fallback)
- [Audit and explainability hooks](#audit-and-explainability-hooks)
- [Code map](#code-map)

---

## Core boundary

- Deterministic engine decides eligibility and merchant selection.
- LLM generates wording/style only after deterministic approval.
- Hard rails enforce final business and safety constraints.
- Raw model output is never treated as the final offer contract.
- Python canonicalization owns DB-truth overrides, typed offer assembly, and rails audit.

```mermaid
sequenceDiagram
    participant Pipeline as Deterministic Engine
    participant Gemini as Gemini Flash (Cloud)
    participant Rails as Server Hard Rails
    participant DB as SQLite Audit
    
    Pipeline->>Gemini: 1. Send Target Context (Passed Gates)
    Gemini-->>Pipeline: 2. Return Generated GenUI JSON
    Pipeline->>Rails: 3. Pass JSON to Rules Validator
    
    rect rgb(200, 10, 10, 0.1)
        Note over Rails: Discount Capped<br/>Expiry Enforced<br/>Safety Claims Verified
        Rails->>Rails: Bounding Checks Override Bad Output
    end
    
    Rails->>DB: 4. Persist Original vs Adjusted JSON
    Rails-->>Pipeline: 5. Return Canonical OfferObject
```

---

## Hard rail checks

Implemented in `apps/api/src/spark/services/hard_rails.py`:

1. merchant name/address resolved from DB context
2. discount capped by active coupon config
3. expiry computed server-side
4. banned health/safety claims scrubbed
5. placeholders normalized
6. canonical mapping actions recorded for audit persistence

### Linked implementation

| Capability | File |
|---|---|
| LLM output generation | [`apps/api/src/spark/services/offer_generator.py`](../../apps/api/src/spark/services/offer_generator.py) |
| Hard rail enforcement | [`apps/api/src/spark/services/hard_rails.py`](../../apps/api/src/spark/services/hard_rails.py) |
| Offer route orchestration | [`apps/api/src/spark/routers/offers.py`](../../apps/api/src/spark/routers/offers.py) |
| Contract models | [`apps/api/src/spark/models/offers.py`](../../apps/api/src/spark/models/offers.py) |

## Why hard rails stay in Python

- They depend on DB truth, not just event payload fields.
- They build the canonical `OfferObject`, not an ingress-side intermediate record.
- They need typed runtime models and stable audit metadata for later inspection.
- They sit on the boundary between generative output (`LLMOfferOutput`) and the final server contract (`OfferObject`).

---

## What LLM cannot decide

- offer eligibility
- merchant entitlement values
- hard financial terms outside configured limits
- lifecycle timestamps

> [!IMPORTANT]
> The LLM is a renderer, not a policy engine. Treat every generated field as untrusted until rails canonicalization completes.

---

## Failure and fallback

- If provider call fails, runtime falls back to deterministic smart fallback generation.
- Hard rails still run on fallback output.
- API should continue returning structurally valid offer objects when eligible.

---

## Audit and explainability hooks

- rails metadata persisted in offer audit log (`rails_audit` payload)
- canonical mapping actions record what was rewritten, defaulted, derived, or redacted
- decision trace and graph decision metadata also attached by router layer

---

## Code map

- [`apps/api/src/spark/services/offer_generator.py`](../../apps/api/src/spark/services/offer_generator.py)
- [`apps/api/src/spark/services/hard_rails.py`](../../apps/api/src/spark/services/hard_rails.py)
- [`apps/api/src/spark/routers/offers.py`](../../apps/api/src/spark/routers/offers.py)

---

## Example before and after rails

Input (LLM-side intent):

```json
{
  "content": {
    "headline": "Warm up at [MERCHANT_NAME]",
    "subtext": "Only [DISCOUNT]% right now"
  }
}
```

Output (post rails):

```json
{
  "merchant": {"name": "Cafe One"},
  "discount": {"value": 15, "source": "merchant_rules_db"},
  "content": {
    "headline": "Warm up at Cafe One",
    "subtext": "Only 15 % right now"
  },
  "expires_at": "2026-04-26T10:15:00"
}
```

---

## Debug cookbook

1. Wrong discount value:
   - inspect active coupon config in DB and post-rails output.
2. Placeholder leakage:
   - confirm `_replace_placeholders` path applied in `hard_rails.py`.
3. Unsafe wording:
   - verify banned pattern filter replaced phrase.
4. LLM outage:
   - confirm fallback generation path and still-valid `OfferObject`.
