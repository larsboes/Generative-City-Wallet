# Data Model

Canonical data model across contracts, SQLite persistence, and graph projection.

---

## Model layers

1. **Canonical API contracts (Python runtime)**  
   `apps/api/src/spark/models/contracts.py`
2. **Shared cross-client mirror (TypeScript)**  
   `packages/shared/src/contracts.ts` (`@spark/shared`)
3. **Operational store (SQLite)**  
   `apps/api/src/spark/db/schema.sql`
4. **Knowledge graph (Neo4j)**  
   projected best-effort from offer/outcome lifecycle

---

## Local vs cloud boundary (data classes)

### Local-only classes (conceptual/mobile side)

- raw sensor/event streams used to derive intent
- fine-grained location history before quantization
- private interaction logs used for local preference shaping

Only derived abstractions are eligible to cross the boundary.

### Boundary contract (cloud-ingested)

Primary ingress contract:

- `GenerateOfferRequest`
  - `intent: IntentVector`
  - optional `merchant_id`
  - optional `demo_overrides` (dev/demo only)

`IntentVector` is the core privacy boundary object and contains abstracted fields
such as `grid_cell`, `movement_mode`, and `weather_need` rather than raw telemetry.

### Cloud-resident classes/stores

- `CompositeContextState`, `OfferDecisionTrace`, `OfferObject`
- SQLite tables (`offer_audit_log`, `wallet_transactions`, `graph_event_log`, etc.)
- optional Neo4j projection entities for personalization and explainability

### Explicitly disallowed in cloud payloads

- raw latitude/longitude traces from device sensors
- raw transaction/event history used for local-only preference derivation
- unconstrained generative fields as source of truth for discount/expiry/merchant id

---

## Core class model (contracts)

```mermaid
classDiagram
  class IntentVector {
    +string grid_cell
    +MovementMode movement_mode
    +WeatherNeed weather_need
    +SocialPreference social_preference
    +PriceTier price_tier
    +list recent_categories
    +bool dwell_signal
    +bool battery_low
    +string session_id
  }

  class UserContext {
    +IntentVector intent
    +map preference_scores
    +SocialPreference social_preference
    +PriceTier price_tier
  }

  class MerchantDemand {
    +float density_score
    +float drop_pct
    +DensitySignalType signal
    +bool offer_eligible
    +float? current_occupancy_pct
    +float? predicted_occupancy_pct
  }

  class ActiveCoupon {
    +CouponType? type
    +float max_discount_pct
    +int valid_window_min
    +map? config
  }

  class MerchantContext {
    +string id
    +string name
    +string category
    +float distance_m
    +string address
    +MerchantDemand demand
    +ActiveCoupon active_coupon
  }

  class EnvironmentContext {
    +string weather_condition
    +float temp_celsius
    +float feels_like_celsius
    +string weather_need
    +string vibe_signal
  }

  class ConflictResolutionContext {
    +ConflictRecommendation recommendation
    +string? framing_band
    +list allowed_vocabulary
    +list banned_vocabulary
  }

  class DecisionTraceItem {
    +string code
    +string reason
    +float score
    +map metadata
  }

  class OfferDecisionTrace {
    +ConflictRecommendation recommendation
    +string? selected_merchant_id
    +float selected_merchant_score
    +int? recheck_in_minutes
    +list candidate_scores
    +list~DecisionTraceItem~ trace
  }

  class CompositeContextState {
    +string timestamp
    +string session_id
    +UserContext user
    +MerchantContext merchant
    +EnvironmentContext environment
    +ConflictResolutionContext conflict_resolution
    +OfferDecisionTrace? decision_trace
  }

  class LLMOfferOutput {
    +LLMContent content
    +LLMGenUI genui
    +string framing_band_used
  }

  class OfferObject {
    +string offer_id
    +string session_id
    +MerchantInfo merchant
    +DiscountInfo discount
    +LLMContent content
    +LLMGenUI genui
    +string expires_at
    +string? qr_payload
    +list explainability
  }

  UserContext --> IntentVector
  MerchantContext --> MerchantDemand
  MerchantContext --> ActiveCoupon
  CompositeContextState --> UserContext
  CompositeContextState --> MerchantContext
  CompositeContextState --> EnvironmentContext
  CompositeContextState --> ConflictResolutionContext
  CompositeContextState --> OfferDecisionTrace
  OfferDecisionTrace --> DecisionTraceItem
  OfferObject --> LLMOfferOutput : derived_from
```

---

## Persistence model (SQLite)

```mermaid
erDiagram
  merchants ||--o{ payone_transactions : has
  merchants ||--o{ merchant_coupons : configures
  merchants ||--o{ offer_audit_log : appears_in
  offer_audit_log ||--o{ wallet_transactions : credits
  offer_audit_log ||--o{ graph_event_log : projects

  merchants {
    text id PK
    text name
    text type
    real lat
    real lon
    text address
    text grid_cell
  }

  payone_transactions {
    text merchant_id FK
    text timestamp
    integer hour_of_week
    integer txn_count
    real total_volume_eur
  }

  merchant_coupons {
    text merchant_id FK
    text coupon_type
    text config
    integer active
    text created_at
    text expires_at
  }

  offer_audit_log {
    text offer_id PK
    text created_at
    text session_id
    text merchant_id
    text density_signal
    text conflict_resolution
    text llm_raw_output
    text final_offer
    text rails_audit
    text status
  }

  wallet_transactions {
    integer id PK
    text session_id
    text offer_id FK
    real amount_eur
    text merchant_name
    text credited_at
  }

  graph_event_log {
    text idempotency_key PK
    text event_type
    text session_id
    text offer_id
    text source
    text created_at
  }
```

---

## Graph projection model (conceptual)

```mermaid
flowchart TB
  UserSession -->|RECEIVED_OFFER| Offer
  Offer -->|AT_MERCHANT| Merchant
  Offer -->|GENERATED_IN| ContextSnapshot
  UserSession -->|PREFERS weight| MerchantCategory
  Redemption -->|FOR_OFFER| Offer
  WalletEvent -->|CREDIT_FOR| Redemption
```

Projection is best-effort and idempotency-protected by SQLite `graph_event_log`.

---

## Offer lifecycle sequence (request to projection)

```mermaid
sequenceDiagram
  autonumber
  participant Mobile as Mobile App
  participant API as FastAPI
  participant Decision as DeterministicDecisionEngine
  participant RuleGate as GraphRuleGate
  participant LLM as LLM Provider
  participant SQLite as SQLite
  participant Graph as Neo4j

  Mobile->>API: POST /api/offers/generate (GenerateOfferRequest)
  API->>Decision: build CompositeContextState + decide_offer()
  Decision-->>API: OfferDecisionTrace (recommendation + candidate scores)

  API->>RuleGate: validate(session, merchant, context)
  RuleGate-->>API: accept/reject + reason

  alt Rejected
    API->>SQLite: INSERT offer_audit_log (decision_trace + rejection)
    API-->>Mobile: no-offer response
  else Accepted
    API->>LLM: generate framing/genui with bounded prompt
    LLM-->>API: LLMOfferOutput
    API->>API: apply hard rails and build OfferObject
    API->>SQLite: INSERT offer_audit_log (final_offer + rails_audit)
    API->>Graph: best-effort projection (idempotency-keyed)
    API-->>Mobile: OfferObject
  end

  opt Redemption path
    Mobile->>API: POST /api/redeem
    API->>SQLite: UPDATE offer_audit_log status=REDEEMED
    API->>SQLite: INSERT wallet_transactions credit
    API->>Graph: project redemption/outcome (idempotent)
    API-->>Mobile: cashback confirmation
  end
```

---

## Data ownership and authority

- **Source of truth for offer lifecycle:** SQLite `offer_audit_log`
- **Source of truth for wallet balance:** SQLite `wallet_transactions`
- **Source of truth for contract shape:** Python contracts in `apps/api/src/spark/models/contracts.py`
- **Parity requirement for frontend/shared consumers:** TypeScript mirror in `packages/shared/src/contracts.ts` must stay field-for-field aligned with Python
- **Graph:** derived/augmenting personalization layer, fail-soft

---

## Debug cookbook

1. Wrong response shape:
   - verify `contracts.py` model and serializer path in router.
2. Offer status mismatch:
   - inspect `offer_audit_log.status` and timestamps.
3. Duplicate graph side-effects:
   - inspect `graph_event_log` idempotency keys.
4. Unexpected density class:
   - inspect `payone_transactions` for merchant/hour-of-week baseline.
