# Safety & Liability Framework

## The Air Canada Precedent: AI Responsibility

The Air Canada case (where a chatbot's incorrect bereavement refund policy was legally binding) established a critical precedent: **a company is legally responsible for the outputs of its AI systems.**

Spark addresses this by enforcing a deterministic safety layer between the generative model and the user.

---

## Hard Rails: Deterministic Overrides

While the LLM generates marketing copy and visual themes (soft values), it is never allowed to determine business-critical or legally binding values (hard values). These are always sourced from the authoritative merchant database and injected post-generation.

### Value Separation

| Value Category | Source | Treatment |
|---|---|---|
| **Discount %** | Merchant DB | Hard-railed (capped to merchant max) |
| **Merchant Identity** | Merchant DB | Overwritten with canonical name |
| **Expiry Time** | Server Logic | Computed and injected server-side |
| **Distance/Time** | Context Engine | Real-time calculation override |
| **Health Claims** | Prohibited | Sanitized and stripped from LLM output |

### Enforcement Logic

```python
def enforce_hard_rails(llm_output, merchant_rules, composite_state):
    """Override any LLM-generated business-critical values with ground truth."""
    offer = llm_output.copy()
    
    # Hard cap: discount cannot exceed merchant's configured maximum
    offer["discount"]["value"] = min(
        llm_output["discount"]["value"],
        merchant_rules.max_discount_pct
    )
    
    # Override: merchant name from DB, never from LLM
    offer["merchant_name"] = merchant_db.get(merchant_rules.merchant_id).name
    
    # Override: expiry always computed server-side
    offer["expires_at"] = (
        composite_state.timestamp 
        + timedelta(minutes=merchant_rules.valid_window_min)
    ).isoformat()
    
    return offer
```

---

## Audit Trail: Evidentiary Logging

Every generated offer is logged with a complete state snapshot to ensure explainability and legal defensibility.

**Log Schema:**
- `offer_id`: Unique identifier.
- `generated_at`: ISO timestamp.
- `merchant_rules_snapshot`: The exact rule set active at the moment of generation.
- `composite_state_hash`: Verifiable hash of the context signals used.
- `llm_raw_output`: The unedited output from the model.
- `rails_enforced`: A diff showing exactly which fields were overridden.
- `final_offer`: The final object delivered to the user.

---

## Pre-Flight Validation

To prevent user frustration and merchant disputes, a silent validation check is performed before an offer is presented to the user. If the offer has been invalidated by a merchant state change (e.g., venue now at capacity), the card is gracefully suppressed before the user can interact with it.
