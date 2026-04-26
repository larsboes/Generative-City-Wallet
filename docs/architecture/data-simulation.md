# Data Simulation

Synthetic transaction layer used for development, demos, and deterministic tests.

---

## Model

- historical hourly baselines per merchant/hour-of-week
- current-vs-baseline density classification
- optional occupancy proxy calibration for selected merchants

Signal outputs drive both decision engine ranking and conflict-resolution context.

---

## Density classes

- `NORMAL`
- `QUIET`
- `PRIORITY`
- `FLASH`
- `NORMALLY_CLOSED`

---

## Runtime components

- schema: `apps/api/src/spark/db/schema.sql`
- seed/helpers: `apps/api/src/spark/db/seed.py`, `apps/api/src/spark/db/connection.py`
- signal computation: `apps/api/src/spark/services/density.py`

---

## Known limitations

- not production forecasting
- calibration values are environment/demo tuned
- external feed emulation remains a roadmap item

---

## Example density output

```json
{
  "merchant_id": "MERCHANT_001",
  "density_score": 0.34,
  "drop_pct": 0.66,
  "signal": "PRIORITY",
  "offer_eligible": true,
  "historical_avg": 8.2,
  "current_rate": 2.8
}
```

---

## Debug cookbook

1. Signal seems too noisy:
   - inspect seeded historical buckets for that hour-of-week.
2. Always `NORMAL`:
   - verify current transaction rates are populated and read correctly.
3. Occupancy missing:
   - verify merchant exists in occupancy calibration map.
