# Self-Learning API Reference

This page summarizes the server-side graph personalization loop and the API/ops surfaces used to inspect and maintain it.

## Purpose

The self-learning loop updates user-category preference edges from behavioral signals while enforcing deterministic safety controls:

- event-granular idempotency
- per `(session_id, category)` update guardrails
- event-level attribution
- retention and decay maintenance
- learning-health metrics logging

## Core signal ingests

### Offer outcome projection

- Runtime path: `apps/api/src/spark/services/redemption.py` (`project_offer_outcome_to_graph`)
- Inputs: `session_id`, `offer_id`, `status`, optional `merchant_category`
- Effects:
  - writes outcome edge in graph
  - applies negative reinforcement for `DECLINED` / `EXPIRED` when category exists
  - logs update outcome (`applied`, `duplicate`, `suppressed_by_guardrail`)

### Redemption projection

- Runtime path: `apps/api/src/spark/services/redemption.py` (`project_redemption_to_graph`)
- Inputs: redemption context from confirmed offer
- Effects:
  - writes redemption and wallet event graph entities
  - reinforces category preference for redeemed merchant category
  - logs attribution and metrics

### Wallet seed projection

- API endpoint: `POST /api/graph/sessions/{session_id}/wallet-seed`
- Runtime path: `apps/api/src/spark/services/wallet_seed.py`
- Effects:
  - applies cold-start category priors with source governance
  - tracks duplicates and guardrail suppressions
  - logs attribution and metrics

## Explainability endpoint

### Session preferences (with attribution)

- Endpoint: `GET /api/graph/sessions/{session_id}/preferences`
- Optional query params:
  - `include_attribution` (`bool`, default `false`)
  - `event_limit` (`int`, default `10`, max `100`)

Example:

```bash
curl -s 'http://localhost:8000/api/graph/sessions/sess-123/preferences?include_attribution=true&event_limit=10' | jq .
```

Response highlights:

- `scores[]`: category weight + provenance fields (`source_type`, `decay_rate`, `source_confidence`, `artifact_count`)
- `attribution[]` (optional): event-level updates (`before_weight`, `delta`, `after_weight`, `event_key`, `outcome`, timestamp)

## Data stores used by the loop

### `graph_event_log`

Primary idempotency and event observability ledger.

Key fields:

- `idempotency_key`
- `event_type`
- `session_id`
- `offer_id`
- `category`
- `source_event_id`
- `payload_hash`
- `created_at`

### `preference_update_log`

Preference attribution ledger for explainability and replay diagnostics.

Key fields:

- `session_id`
- `category`
- `source_type`
- `event_type`
- `event_key`
- `before_weight`
- `delta`
- `after_weight`
- `outcome`
- `created_at`

### `learning_metrics_log`

Metric stream for learning health and drift diagnostics.

Typical metrics:

- `learning_update_applied`
- `learning_duplicate_suppression`
- `learning_guardrail_suppressed`
- `preference_weight_volatility`
- maintenance metrics from ops scripts

## Maintenance and operations

### Graph maintenance script

- Script: `scripts/ops/run_graph_maintenance.py`
- Performs:
  - graph artifact cleanup
  - stale preference decay
  - source-aware retention pruning for learning attribution rows
  - decay gap health checks (`decay_gap_alarm`)

Example:

```bash
uv run python scripts/ops/run_graph_maintenance.py
```

## Relevant configuration

Config source: `apps/api/src/spark/config.py`

- `GRAPH_PREF_UPDATE_WINDOW_SECONDS`
- `GRAPH_PREF_MAX_UPDATES_PER_CATEGORY_WINDOW`
- `GRAPH_PREF_DECAY_DEFAULT_RATE`
- `GRAPH_PREF_DECAY_STALE_AFTER_DAYS`
- `GRAPH_PREF_DECAY_MAX_GAP_HOURS`
- `GRAPH_PREF_RETENTION_WALLET_SEED_DAYS`
- `GRAPH_PREF_RETENTION_INTERACTION_DAYS`

## Implementation map

- `apps/api/src/spark/services/redemption.py`
- `apps/api/src/spark/services/wallet_seed.py`
- `apps/api/src/spark/repositories/redemption.py`
- `apps/api/src/spark/routers/graph.py`
- `apps/api/src/spark/db/schema.sql`
- `scripts/ops/run_graph_maintenance.py`

## Debug playbook (copy/paste)

Use this sequence when a category weight looks wrong or does not change as expected.

### 1) Check graph service health

```bash
curl -s http://localhost:8000/api/graph/health | jq .
```

If `available` is `false`, learning writes are fail-soft and no preference changes will be applied.

### 2) Inspect current preferences with attribution

```bash
SESSION_ID="sess-123"
curl -s "http://localhost:8000/api/graph/sessions/${SESSION_ID}/preferences?include_attribution=true&event_limit=20" | jq .
```

Focus on:

- `scores[]` current weight for the category
- `attribution[]` latest `outcome` and `delta`

### 3) Trigger a test learning signal (wallet seed)

```bash
curl -s -X POST "http://localhost:8000/api/graph/sessions/${SESSION_ID}/wallet-seed" \
  -H "Content-Type: application/json" \
  -d '{
    "seeds": [
      {
        "category": "cafe",
        "weight": 0.45,
        "source_type": "wallet_pass",
        "source_confidence": 0.9,
        "artifact_count": 2
      }
    ]
  }' | jq .
```

Check `result.applied`, `result.duplicates`, and `result.suppressed_by_guardrail`.

### 4) Re-read preferences and attribution

```bash
curl -s "http://localhost:8000/api/graph/sessions/${SESSION_ID}/preferences?include_attribution=true&event_limit=20" | jq .
```

Expected:

- weight movement in `scores[]` for category `cafe`
- new attribution row with `outcome=applied` (or explicit suppression/duplicate)

### 5) Run maintenance and verify decay health

```bash
uv run python scripts/ops/run_graph_maintenance.py | jq .
```

Check:

- `health.last_decay_age_hours`
- `health.decay_gap_alarm`
- `retention.wallet_seed_pruned` and `retention.interaction_pruned`
