# Context Signals

Runtime signal model and composite context assembly.

> [!TIP]
> Start with this page for signal semantics, then continue in [`offer-decision-engine.md`](./offer-decision-engine.md) for ranking and threshold behavior.

---

## Signal categories

- environmental (weather condition and derived need)
- merchant demand (density/current-vs-baseline)
- movement/mobility (intent mode)
- temporal (hour/day bucketing)
- preference signals (graph-derived or fallback heuristics)

---

## Composite assembly role

`build_composite_state()` assembles signal inputs into `CompositeContextState`, then attaches:

- conflict resolution framing constraints
- deterministic decision trace

```mermaid
flowchart TD
  subgraph Data Sources
      weather((Weather API))
      demand((Payone Density))
      movement((Motion Mode))
      time((Time Bucket))
      prefs[(Neo4j Prefs)]
  end

  subgraph Composite Assembly
      composite{Composite State Builder}
      decision(Offer Decision Engine)
      conflict[Conflict Resolver & Framing]
  end

  weather --> composite
  demand --> composite
  movement --> composite
  time --> composite
  prefs -.-> composite

  composite ==> decision
  decision ==> conflict
  conflict ==> llm(((Gemini Flash)))
```

### Runtime code links

| Concern | File |
|---|---|
| Composite builder | [`apps/api/src/spark/services/composite.py`](../../apps/api/src/spark/services/composite.py) |
| Deterministic decision | [`apps/api/src/spark/services/offer_decision.py`](../../apps/api/src/spark/services/offer_decision.py) |
| Context models | [`apps/api/src/spark/models/context.py`](../../apps/api/src/spark/models/context.py) |
| API request models | [`apps/api/src/spark/models/api.py`](../../apps/api/src/spark/models/api.py) |
| Intent trust normalization | [`apps/api/src/spark/services/intent_trust.py`](../../apps/api/src/spark/services/intent_trust.py) |

---

## Runtime invariants

- composite context is always available for offer endpoint path
- preference scores are always present (graph values or defaults)
- conflict framing vocabulary is attached before LLM call

---

## Known simplifications

- Some optional signals are still advisory/fail-soft depending on provider availability.
- Cross-session identity continuity policy is intentionally bounded by retention and reset controls.

---

## Implementation

- models: [`apps/api/src/spark/models/context.py`](../../apps/api/src/spark/models/context.py), [`apps/api/src/spark/models/api.py`](../../apps/api/src/spark/models/api.py)
- builder: [`apps/api/src/spark/services/composite.py`](../../apps/api/src/spark/services/composite.py)
- decision: [`apps/api/src/spark/services/offer_decision.py`](../../apps/api/src/spark/services/offer_decision.py)

---

## Composite example (shape)

```json
{
  "session_id": "sess-123",
  "user": {
    "intent": {"movement_mode": "browsing", "weather_need": "warmth_seeking"},
    "preference_scores": {"cafe": 0.82, "bar": 0.4}
  },
  "merchant": {
    "id": "MERCHANT_001",
    "demand": {"signal": "PRIORITY", "drop_pct": 0.66}
  },
  "conflict_resolution": {"recommendation": "RECOMMEND_WITH_FRAMING"},
  "decision_trace": {"selected_merchant_id": "MERCHANT_001"}
}
```

---

## Debug cookbook

1. Unexpected merchant selection:
   - inspect `decision_trace` in composite state.
2. Missing preferences:
   - verify graph availability and fallback defaults.
3. Wrong weather-derived tone:
   - inspect `weather_need` and `vibe_signal` classification.
4. Offer blocked unexpectedly:
   - inspect movement mode and hard-block metadata.
