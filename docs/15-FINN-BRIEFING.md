# 15 — Finn's Briefing: Transaction Data, Core Financial Logic & the Rule Engine

> **TL;DR for Finn:** You own the data layer that makes the whole system smart. Everything downstream — offer generation, stakeholder conflict resolution, coupon mechanics — runs on signals your code produces. This doc gives you everything you need to start without waiting on anyone else.

---

## What You're Building (and Why It Matters)

The challenge brief lists Payone transaction data as DSV Gruppe's key asset. Every judge from DSV will be watching to see if we actually used it — or just made a weather app. Your code is the thing that makes Payone central to the pitch, not peripheral to it.

Three deliverables from you:

1. **Synthetic Payone feed** — 28 days of realistic per-merchant transaction history, served via an endpoint the backend polls
2. **Density signal computation** — converts raw txn rate into a normalized signal the offer engine consumes
3. **Occupancy inference + fill rate prediction** — estimates how full a venue is and where it's headed (critical for bars/clubs)

The conflict resolution logic (doc 14) and offer ranking logic (doc 10) consume these signals directly. If the signals are good, everything downstream is good.

---

## Part 1: Synthetic Payone Data Generator

### Why Synthetic?

We don't have a Payone API key. We don't need one for the hackathon — we need *plausible* data that produces interesting demo moments. The data generator should produce the exact format a real Payone webhook would emit, so the integration is a configuration change post-hackathon.

### Transaction Rate Units

Think in **transactions per hour** (txn/hr). A busy Stuttgart café does ~12 txn/hr at peak lunch. Same café at 15:00 on a Tuesday does ~2 txn/hr. The drop is your signal.

For bars and clubs: transactions proxy attendance. Drinks ordered ≈ people present (with some lag). One txn ≈ 1.5 people on average for a bar (groups share a round).

### Base Rate Profiles

```python
# Transactions per hour, indexed by hour of day (0-23)
# These are the "typical Friday" shapes. Calibrated to Stuttgart venue sizes.

BASE_HOURLY_RATES = {
    "cafe": [0,0,0,0,0,0,0.5, 3, 9, 7, 5, 4, 11, 13, 9, 6, 5, 4, 3, 2, 1, 0, 0, 0],
    "bakery": [0,0,0,0,0,0,0.5, 8, 12, 9, 6, 4, 8, 7, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0],
    "restaurant": [0,0,0,0,0,0,0, 0, 1, 2, 3, 5, 13, 15, 8, 3, 4, 8, 16, 14, 6, 2, 1, 0],
    "bar": [0,0,0,0,0,0,0, 0, 0, 0, 1, 2, 3, 2, 1, 1, 2, 3, 6, 10, 15, 18, 16, 10],
    "club": [0,0,0,0,0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 3, 8, 14, 20, 24],
    "retail": [0,0,0,0,0,0,0, 0, 1, 3, 6, 8, 10, 9, 7, 6, 5, 4, 2, 1, 0, 0, 0, 0],
}

# Day-of-week multipliers (Monday=0, Sunday=6)
DAY_MULTIPLIERS = {
    "cafe": [0.85, 0.90, 0.90, 0.88, 1.0, 1.25, 1.15],
    "bakery": [0.90, 0.88, 0.88, 0.88, 1.0, 1.30, 1.20],
    "restaurant": [0.80, 0.82, 0.85, 0.88, 1.10, 1.35, 1.25],
    "bar": [0.70, 0.72, 0.75, 0.85, 1.20, 1.60, 1.40],
    "club": [0.30, 0.30, 0.40, 0.60, 1.50, 2.00, 1.70],
    "retail": [0.90, 0.92, 0.92, 0.92, 1.05, 1.40, 0.80],  # Sundays closed in Stuttgart
}
```

### Full Generator Implementation

```python
import numpy as np
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

def generate_payone_history(
    merchant_id: str,
    merchant_type: str,
    days: int = 28,
    seed: Optional[int] = None
) -> list[dict]:
    """
    Generate 28 days of synthetic Payone transaction history.
    
    Returns list of transaction records, one per hour.
    Real Payone would return individual transactions — we aggregate to hourly
    buckets for demo purposes (and privacy/realism: we'd only get aggregate
    reporting from Payone anyway, not individual card numbers).
    """
    if seed:
        np.random.seed(seed)
    
    base_rates = BASE_HOURLY_RATES[merchant_type]
    day_mults = DAY_MULTIPLIERS[merchant_type]
    
    records = []
    start = datetime.now() - timedelta(days=days)
    
    for day_offset in range(days):
        dt = start + timedelta(days=day_offset)
        dow = dt.weekday()
        day_mult = day_mults[dow]
        
        for hour in range(24):
            base = base_rates[hour] * day_mult
            
            if base < 0.01:
                # Closed / truly silent period
                txn_count = 0
            else:
                # Poisson-distributed transactions with Gaussian noise on the rate
                # Poisson for count randomness + Gaussian for "unusual day" effect
                rate_with_noise = max(0, base * (1 + np.random.normal(0, 0.15)))
                txn_count = int(np.random.poisson(rate_with_noise))
            
            if txn_count > 0:
                # Average transaction value by type
                avg_values = {
                    "cafe": 4.80, "bakery": 3.20, "restaurant": 18.50,
                    "bar": 7.40, "club": 9.00, "retail": 28.00
                }
                avg = avg_values.get(merchant_type, 10.0)
                total_volume = sum(
                    max(0.5, np.random.normal(avg, avg * 0.3))
                    for _ in range(txn_count)
                )
            else:
                total_volume = 0.0
            
            records.append({
                "merchant_id": merchant_id,
                "merchant_type": merchant_type,
                "timestamp": dt.replace(hour=hour, minute=0, second=0).isoformat(),
                "hour_of_day": hour,
                "day_of_week": dow,
                "hour_of_week": dow * 24 + hour,  # 0-167, the rolling average key
                "txn_count": txn_count,
                "total_volume_eur": round(total_volume, 2),
            })
    
    return records


def seed_all_merchants(db_path: str = "payone_sim.db"):
    """
    Seed the local SQLite database with transaction history for all demo merchants.
    Call this once at backend startup.
    """
    DEMO_MERCHANTS = [
        {"id": "MERCHANT_001", "name": "Café Römer", "type": "cafe", "lat": 48.7758, "lon": 9.1829},
        {"id": "MERCHANT_002", "name": "Bäckerei Wolf", "type": "bakery", "lat": 48.7771, "lon": 9.1793},
        {"id": "MERCHANT_003", "name": "Bar Unter", "type": "bar", "lat": 48.7748, "lon": 9.1795},
        {"id": "MERCHANT_004", "name": "Markthalle Bistro", "type": "restaurant", "lat": 48.7780, "lon": 9.1812},
        {"id": "MERCHANT_005", "name": "Club Schräglage", "type": "club", "lat": 48.7731, "lon": 9.1820},
    ]
    
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payone_transactions (
            merchant_id TEXT,
            merchant_type TEXT,
            timestamp TEXT,
            hour_of_day INTEGER,
            day_of_week INTEGER,
            hour_of_week INTEGER,
            txn_count INTEGER,
            total_volume_eur REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_merchant_hour ON payone_transactions(merchant_id, hour_of_week)")
    
    for m in DEMO_MERCHANTS:
        # Seed with fixed random seed per merchant for reproducibility
        records = generate_payone_history(
            m["id"], m["type"], days=28,
            seed=hash(m["id"]) % (2**31)
        )
        conn.executemany(
            "INSERT INTO payone_transactions VALUES (?,?,?,?,?,?,?,?)",
            [(r["merchant_id"], r["merchant_type"], r["timestamp"],
              r["hour_of_day"], r["day_of_week"], r["hour_of_week"],
              r["txn_count"], r["total_volume_eur"]) for r in records]
        )
    
    conn.commit()
    conn.close()
    print(f"Seeded {len(DEMO_MERCHANTS)} merchants × 28 days × 24 hours = {len(DEMO_MERCHANTS)*28*24} records")
```

---

## Part 2: Density Signal Computation

The density signal is not raw txn count — it's **current rate vs. historical baseline for this exact hour-of-week**. A bar at 3 txn/hr is quiet on a Friday night but active on a Tuesday morning.

```python
def compute_density_signal(
    merchant_id: str,
    current_txn_rate: float,   # txn/hr in last 60 minutes (call Payone live / poll sim)
    current_dt: datetime,
    db_path: str = "payone_sim.db"
) -> dict:
    """
    Returns a normalized density signal for the offer engine.
    
    The 'density_score' is the ratio of current rate to historical average.
    < 0.70 = offer-eligible quiet period
    < 0.50 = priority offer window
    < 0.30 = flash offer / emergency fill trigger
    """
    hour_of_week = current_dt.weekday() * 24 + current_dt.hour
    
    conn = sqlite3.connect(db_path)
    
    # Rolling 4-week average for this exact hour-of-week
    row = conn.execute("""
        SELECT AVG(txn_count), STDEV(txn_count), COUNT(*)
        FROM payone_transactions
        WHERE merchant_id = ? AND hour_of_week = ?
    """, (merchant_id, hour_of_week)).fetchone()
    
    conn.close()
    
    avg_txn, std_txn, sample_count = row
    
    if not avg_txn or avg_txn < 0.5:
        # Merchant is normally closed at this hour — don't trigger offers
        return {
            "density_score": 1.0,
            "drop_pct": 0.0,
            "signal": "NORMALLY_CLOSED",
            "offer_eligible": False,
            "historical_avg": 0,
            "current_rate": current_txn_rate,
        }
    
    density_score = current_txn_rate / avg_txn
    drop_pct = max(0, 1 - density_score)
    
    # Classify
    if drop_pct >= 0.70:
        signal = "FLASH"
        eligible = True
    elif drop_pct >= 0.50:
        signal = "PRIORITY"
        eligible = True
    elif drop_pct >= 0.30:
        signal = "QUIET"
        eligible = True
    else:
        signal = "NORMAL"
        eligible = False
    
    return {
        "density_score": round(density_score, 3),
        "drop_pct": round(drop_pct, 3),
        "signal": signal,
        "offer_eligible": eligible,
        "historical_avg": round(avg_txn, 1),
        "current_rate": round(current_txn_rate, 1),
        "confidence": min(1.0, sample_count / 4),  # Full confidence after 4 weeks
    }
```

**Note on `STDEV`**: SQLite doesn't have a built-in STDEV. Either use a Python aggregation or install the `sqlite-stats` extension. For the hackathon, skip the std and just use avg — it's fine.

---

## Part 3: Occupancy Inference for Bars and Clubs

Txn rate → % occupancy is a calibration problem. There's no universal formula, so we anchor on two known points per venue: "dead" and "full house."

```python
OCCUPANCY_CALIBRATION = {
    # (txn_rate_at_empty, txn_rate_at_capacity, capacity_guests)
    "MERCHANT_003": (0.5, 22, 120),    # Bar Unter: 0.5 txn/hr = empty, 22 = full (120 guests)
    "MERCHANT_005": (0, 35, 300),      # Club Schräglage: 0 = closed, 35 = full house (300 ppl)
}

def infer_occupancy_pct(merchant_id: str, current_txn_rate: float) -> float:
    """
    Linearly interpolate between known empty/full txn rates.
    Clamp to [0, 1]. Not precise — but good enough for the conflict decision.
    """
    if merchant_id not in OCCUPANCY_CALIBRATION:
        return None  # Can't infer without calibration
    
    empty_rate, full_rate, capacity = OCCUPANCY_CALIBRATION[merchant_id]
    
    if full_rate <= empty_rate:
        return 0.0
    
    occ = (current_txn_rate - empty_rate) / (full_rate - empty_rate)
    return round(max(0.0, min(1.0, occ)), 3)
```

### Fill Rate Prediction

For social users approaching a venue that's currently at low occupancy, we need to predict occupancy at the time they'll actually arrive. This is the key insight from doc 14.

```python
def predict_occupancy_at(
    merchant_id: str,
    current_occ_pct: float,
    current_dt: datetime,
    arrival_dt: datetime,
    db_path: str = "payone_sim.db"
) -> float:
    """
    Predict occupancy percentage at arrival time using historical trajectory.
    
    Method: Look at historical data for similar time windows (same weekday).
    Find the average occupancy at arrival_hour given current occupancy at current_hour.
    
    Simplified for hackathon: use historical average at arrival_hour as baseline,
    then blend with current actual occupancy to account for "tonight is unusual."
    """
    arrival_hour_of_week = arrival_dt.weekday() * 24 + arrival_dt.hour
    
    conn = sqlite3.connect(db_path)
    
    # Historical txn rate at arrival time on this weekday
    hist_at_arrival = conn.execute("""
        SELECT AVG(txn_count)
        FROM payone_transactions
        WHERE merchant_id = ? AND hour_of_week = ?
    """, (merchant_id, arrival_hour_of_week)).fetchone()[0]
    
    conn.close()
    
    if not hist_at_arrival:
        return current_occ_pct  # No data, assume static
    
    # Historical occupancy at arrival time
    hist_occ_at_arrival = infer_occupancy_pct(merchant_id, hist_at_arrival or 0)
    
    if hist_occ_at_arrival is None:
        return current_occ_pct
    
    # Blend: weight historical trajectory more if current matches historical pattern
    # Simple version for hackathon: 60% historical, 40% current extrapolated
    # (A more sophisticated version would adjust based on how far current deviates from baseline)
    predicted = 0.6 * hist_occ_at_arrival + 0.4 * current_occ_pct
    
    return round(max(0.0, min(1.0, predicted)), 3)
```

---

## Part 4: The Conflict Resolution Rule Engine

This is the decision logic from doc 14. You implement this as a backend endpoint. The offer engine calls it before scoring any bar or club.

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class Recommendation(Enum):
    RECOMMEND = "RECOMMEND"
    RECOMMEND_WITH_FRAMING = "RECOMMEND_WITH_FRAMING"
    DO_NOT_RECOMMEND = "DO_NOT_RECOMMEND"

@dataclass
class ConflictResolution:
    recommendation: Recommendation
    framing_band: str | None           # Key into FRAMING_VOCABULARY
    coupon_mechanism: str | None       # "MILESTONE" | "FLASH" | "TIME_BOUND" | "DRINK" | None
    reason: str                        # For audit log — human-readable why
    recheck_in_minutes: int | None     # For DO_NOT_RECOMMEND: when to retry


def resolve_conflict(
    merchant_id: str,
    user_social_pref: str,   # "social" | "quiet" | "neutral"
    current_txn_rate: float,
    current_dt: datetime,
    active_coupon: dict | None,  # {"type": "MILESTONE", "threshold": 50, "current": 16, ...}
    db_path: str = "payone_sim.db"
) -> ConflictResolution:
    """
    Pure rule engine. No LLM. Deterministic. Auditable.
    
    The LLM runs AFTER this returns RECOMMEND — it only generates framing copy.
    The LLM never decides whether to recommend.
    """
    # Walk time estimate: assume 140m average distance at 80m/min = 1.75 min
    # In production, pass actual distance from user context
    walk_time_min = 2
    arrival_dt = current_dt + timedelta(minutes=walk_time_min + 1)
    
    current_occ = infer_occupancy_pct(merchant_id, current_txn_rate)
    predicted_occ = predict_occupancy_at(merchant_id, current_occ or 0, current_dt, arrival_dt, db_path)
    
    current_occ_pct = (current_occ or 0) * 100
    predicted_occ_pct = predicted_occ * 100
    
    if user_social_pref == "social":
        if predicted_occ_pct >= 60:
            coupon = None if predicted_occ_pct >= 70 else _select_coupon(active_coupon, "soft")
            return ConflictResolution(
                recommendation=Recommendation.RECOMMEND,
                framing_band="busy" if predicted_occ_pct >= 70 else "building_momentum",
                coupon_mechanism=coupon,
                reason=f"Social user, predicted occ at arrival {predicted_occ_pct:.0f}% — natural match",
                recheck_in_minutes=None,
            )
        
        elif predicted_occ_pct >= 40:
            if active_coupon and active_coupon.get("type") == "MILESTONE":
                return ConflictResolution(
                    recommendation=Recommendation.RECOMMEND_WITH_FRAMING,
                    framing_band="building_momentum",
                    coupon_mechanism="MILESTONE",
                    reason=f"Social + {predicted_occ_pct:.0f}% predicted + milestone active — honest social proof",
                    recheck_in_minutes=None,
                )
            elif active_coupon and active_coupon.get("type") in ("TIME_BOUND", "DRINK"):
                return ConflictResolution(
                    recommendation=Recommendation.RECOMMEND_WITH_FRAMING,
                    framing_band="empty_but_filling",
                    coupon_mechanism=active_coupon["type"],
                    reason=f"Social + {predicted_occ_pct:.0f}% predicted + value coupon — worth the early arrival",
                    recheck_in_minutes=None,
                )
            else:
                # No coupon to bridge the gap
                return ConflictResolution(
                    recommendation=Recommendation.DO_NOT_RECOMMEND,
                    framing_band=None,
                    coupon_mechanism=None,
                    reason=f"Social + {predicted_occ_pct:.0f}% predicted + no coupon — insufficient to recommend",
                    recheck_in_minutes=30,
                )
        
        else:
            return ConflictResolution(
                recommendation=Recommendation.DO_NOT_RECOMMEND,
                framing_band=None,
                coupon_mechanism=None,
                reason=f"Social user, predicted occ {predicted_occ_pct:.0f}% at arrival — won't be lively",
                recheck_in_minutes=30,
            )
    
    elif user_social_pref == "quiet":
        if current_occ_pct <= 50:
            return ConflictResolution(
                recommendation=Recommendation.RECOMMEND,
                framing_band="quiet_intentional",
                coupon_mechanism=None,  # No coupon needed — preference match IS the value
                reason=f"Quiet user, current occ {current_occ_pct:.0f}% — natural match",
                recheck_in_minutes=None,
            )
        elif current_occ_pct <= 70:
            return ConflictResolution(
                recommendation=Recommendation.RECOMMEND_WITH_FRAMING,
                framing_band="quiet_intentional",
                coupon_mechanism=_select_coupon(active_coupon, "soft"),
                reason=f"Quiet user, current occ {current_occ_pct:.0f}% — some quiet spots remain",
                recheck_in_minutes=None,
            )
        else:
            return ConflictResolution(
                recommendation=Recommendation.DO_NOT_RECOMMEND,
                framing_band=None,
                coupon_mechanism=None,
                reason=f"Quiet user, current occ {current_occ_pct:.0f}% — wrong vibe entirely",
                recheck_in_minutes=60,
            )
    
    else:  # neutral
        return ConflictResolution(
            recommendation=Recommendation.RECOMMEND,
            framing_band=None,
            coupon_mechanism=_select_coupon(active_coupon, "any"),
            reason="Neutral user — standard offer flow, no occupancy constraint",
            recheck_in_minutes=None,
        )


def _select_coupon(active_coupon: dict | None, preference: str) -> str | None:
    """Pick the appropriate coupon type given what's active and what the situation calls for."""
    if not active_coupon:
        return None
    coupon_type = active_coupon.get("type")
    if preference == "any":
        return coupon_type
    if preference == "soft":
        return coupon_type if coupon_type in ("DRINK", "FLASH") else None
    return coupon_type
```

---

## Part 5: Coupon Mechanism Types

Merchants configure these in their dashboard. You store them in the rule engine DB and look them up during conflict resolution.

```python
COUPON_SCHEMA = {
    "FLASH": {
        "fields": ["discount_pct", "duration_minutes"],
        "example": {"discount_pct": 15, "duration_minutes": 20},
        "trigger": "offer_eligible == True AND density_signal in ('QUIET', 'PRIORITY', 'FLASH')",
        "best_for": ["cafe", "bakery", "restaurant"],
        "merchant_pays_when": "QR scanned (unconditional)",
    },
    "MILESTONE": {
        "fields": ["target_guests", "reward_type", "reward_value", "reward_count"],
        "example": {"target_guests": 50, "reward_type": "cover_refund", "reward_value": 8.0, "reward_count": 20},
        "trigger": "current_occupancy < target_guests AND social_user",
        "best_for": ["bar", "club"],
        "merchant_pays_when": "milestone reached (pays only on success)",
    },
    "TIME_BOUND": {
        "fields": ["discount_pct", "valid_until_time"],
        "example": {"discount_pct": 20, "valid_until_time": "22:00"},
        "trigger": "current_time < valid_until_time AND social_user wants early arrival",
        "best_for": ["bar", "club", "restaurant"],
        "merchant_pays_when": "QR scanned before time cutoff",
    },
    "DRINK": {
        "fields": ["offer_description", "valid_hours"],
        "example": {"offer_description": "First drink on us", "valid_hours": 2},
        "trigger": "any occupancy — value play",
        "best_for": ["bar", "restaurant"],
        "merchant_pays_when": "QR scanned (capped by drink limit)",
    },
    "VISIBILITY_ONLY": {
        "fields": [],
        "example": {},
        "trigger": "quiet_user + quiet venue — no discount, just discovery",
        "best_for": ["cafe", "retail", "premium venues"],
        "merchant_pays_when": "impression or click (not redemption)",
    },
}
```

For the MVP rule engine, store active coupons in a table:

```sql
CREATE TABLE merchant_coupons (
    merchant_id TEXT,
    coupon_type TEXT,           -- matches keys in COUPON_SCHEMA
    config JSON,                -- type-specific fields from COUPON_SCHEMA
    active INTEGER DEFAULT 1,
    created_at TEXT,
    expires_at TEXT,
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

-- Milestone progress tracking
CREATE TABLE milestone_progress (
    merchant_id TEXT,
    session_date TEXT,          -- "2025-06-14" (resets daily)
    current_guests INTEGER DEFAULT 0,
    target_guests INTEGER,
    milestone_fired INTEGER DEFAULT 0,
    PRIMARY KEY (merchant_id, session_date)
);
```

---

## Part 6: Hard Rails Enforcement

This is non-negotiable from doc 13 and the Air Canada liability analysis. The LLM generates soft values (copy, tone, imagery). You cap and override hard values from the DB. Every offer that ships must pass this.

```python
def enforce_hard_rails(
    llm_output: dict,
    merchant_id: str,
    coupon_config: dict | None,
    composite_state: dict,
    conn: sqlite3.Connection
) -> dict:
    """
    Post-LLM guard. Run this ALWAYS before returning an offer to the device.
    
    Rule: If in doubt, the DB wins. The LLM never determines what the user owes,
    what the discount is, or what the merchant's name is.
    """
    offer = llm_output.copy()
    
    # 1. Merchant name — always from DB
    merchant_name = conn.execute(
        "SELECT name FROM merchants WHERE id = ?", (merchant_id,)
    ).fetchone()[0]
    offer["merchant_name"] = merchant_name
    
    # 2. Discount value — cap to what merchant configured; default 0 if no coupon
    if coupon_config:
        llm_discount = offer.get("discount", {}).get("value", 0)
        max_discount = coupon_config.get("discount_pct", 0)
        offer["discount"] = {
            "value": min(llm_discount, max_discount),
            "type": coupon_config.get("reward_type", "percentage"),
            "source": "merchant_rules_db",  # Audit marker
        }
    else:
        offer["discount"] = {"value": 0, "type": "none", "source": "no_active_coupon"}
    
    # 3. Expiry — always computed server-side from timestamp
    offer["expires_at"] = (
        datetime.fromisoformat(composite_state["timestamp"]) + timedelta(minutes=15)
    ).isoformat()
    
    # 4. Strip any health claims from copy (GDPR / regulatory)
    BANNED_COPY_PATTERNS = [
        "helps you", "good for your health", "improves", "boosts your",
        "doctors recommend", "clinically", "heals"
    ]
    content = offer.get("content", {})
    for field in ["headline", "subtext"]:
        text = content.get(field, "")
        for pattern in BANNED_COPY_PATTERNS:
            if pattern.lower() in text.lower():
                content[field] = "[content review required]"  # Flag it rather than silently pass
    offer["content"] = content
    
    # 5. Mandatory audit fields
    offer["_audit"] = {
        "rails_applied": True,
        "merchant_name_source": "merchant_db",
        "discount_capped_from": llm_output.get("discount", {}).get("value"),
        "discount_capped_to": offer["discount"]["value"],
        "expiry_computed_at": datetime.now().isoformat(),
    }
    
    return offer
```

---

## Part 7: Offer Audit Log

Every offer that fires must be stored. This is the explainability trace from doc 14 — judges and future regulators can audit why any specific offer was sent.

```sql
CREATE TABLE offer_audit_log (
    offer_id TEXT PRIMARY KEY,
    created_at TEXT,
    
    -- User context (anonymized — no PII)
    session_id TEXT,
    grid_cell TEXT,
    movement_mode TEXT,
    social_preference TEXT,
    
    -- Merchant + venue state
    merchant_id TEXT,
    density_signal TEXT,
    density_score REAL,
    current_occupancy_pct REAL,
    predicted_occupancy_pct REAL,
    
    -- Conflict resolution
    conflict_check TEXT,        -- "SOFT_CONFLICT" | "HARD_CONFLICT" | "NO_CONFLICT" | ...
    conflict_resolution TEXT,   -- "RECOMMEND" | "RECOMMEND_WITH_FRAMING" | "DO_NOT_RECOMMEND"
    framing_band TEXT,
    
    -- Coupon
    coupon_type TEXT,
    coupon_config JSON,
    
    -- LLM output (pre-rails)
    llm_raw_output JSON,
    
    -- Final offer (post-rails)
    final_offer JSON,
    rails_audit JSON,
    
    -- Lifecycle
    status TEXT DEFAULT 'SENT',  -- SENT | ACCEPTED | DECLINED | EXPIRED | REDEEMED
    accepted_at TEXT,
    redeemed_at TEXT,
    declined_at TEXT,
    expired_at TEXT
);
```

Log every offer on creation:
```python
def log_offer(offer_id, session_id, merchant_id, density_signal, conflict_result, llm_raw, final_offer, conn):
    conn.execute("""
        INSERT INTO offer_audit_log 
        (offer_id, created_at, session_id, merchant_id, density_signal, 
         conflict_resolution, framing_band, coupon_type, llm_raw_output, final_offer, rails_audit, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        offer_id, datetime.now().isoformat(), session_id, merchant_id,
        density_signal["signal"],
        conflict_result.recommendation.value,
        conflict_result.framing_band,
        conflict_result.coupon_mechanism,
        json.dumps(llm_raw),
        json.dumps(final_offer),
        json.dumps(final_offer.get("_audit")),
        "SENT"
    ))
    conn.commit()
```

---

## Part 8: Integration Endpoints

What the rest of the backend expects from you. These are the contracts.

### `GET /payone/density/{merchant_id}`
```json
{
  "merchant_id": "MERCHANT_003",
  "density_score": 0.34,
  "drop_pct": 0.66,
  "signal": "PRIORITY",
  "offer_eligible": true,
  "historical_avg": 8.2,
  "current_rate": 2.8,
  "current_occupancy_pct": 0.22,
  "timestamp": "2025-06-14T21:14:00"
}
```

### `POST /conflict/resolve`
Request:
```json
{
  "merchant_id": "MERCHANT_003",
  "user_social_pref": "social",
  "current_txn_rate": 2.8,
  "current_dt": "2025-06-14T21:14:00",
  "active_coupon": {
    "type": "MILESTONE",
    "threshold": 50,
    "current_guests": 16,
    "reward_value": 8.0
  }
}
```
Response:
```json
{
  "recommendation": "RECOMMEND_WITH_FRAMING",
  "framing_band": "building_momentum",
  "coupon_mechanism": "MILESTONE",
  "reason": "Social + 58% predicted + milestone active — honest social proof",
  "recheck_in_minutes": null
}
```

### `POST /offer/validate-qr`
Request: `{ "qr_payload": "spark://redeem/offer_123/abc789/1718404000" }`
Response:
```json
{
  "valid": true,
  "offer_id": "offer_123",
  "merchant_id": "MERCHANT_003",
  "discount_value": 8.00,
  "discount_type": "cover_refund",
  "user_session": "anon-uuid",
  "expires_at": "2025-06-14T21:29:00"
}
```
On validation, update `offer_audit_log.status = 'REDEEMED'` and credit user wallet.

### `POST /offer/redemption-confirm`
Called after merchant confirms payment. Triggers cashback credit.
```json
{ "offer_id": "offer_123", "merchant_confirmed": true }
```

---

## Part 9: Open Questions You'll Hit

These are real decisions that aren't fully locked. Make a call and document it in doc 08 (OPEN-QUESTIONS.md) with your reasoning.

**Q1: Polling vs. webhook for simulated Payone feed?**
Decision needed: Does the backend poll the SQLite feed every 60 seconds (simpler, fine for demo) or do we simulate real-time push (more realistic for pitch)? Recommendation: poll every 60s for MVP. FastAPI background task with `asyncio.sleep(60)`.

**Q2: What's the "current_txn_rate" in the demo?**
The sim generates hourly buckets. When the backend polls at 21:14, does it use the 21:00 bucket's txn_count as the rate? Or interpolate between buckets? Recommendation: use the most recent full hour bucket, no interpolation. Document the simplification.

**Q3: Club occupancy calibration numbers — are they realistic?**
The OCCUPANCY_CALIBRATION values above are guesses. For the demo, they just need to produce non-trivial predictions — e.g., Bar Unter at 21:00 should show ~22% and predict ~58% at 22:30. Tune these numbers to produce a compelling demo trace.

**Q4: Milestone coupon "current_guests" — how tracked?**
In the real world: Payone txn rate. In our sim: cumulative txn_count since 18:00 divided by avg_drinks_per_person (1.5). Implement `milestone_progress` table updates on every Payone poll cycle.

**Q5: When does a DO_NOT_RECOMMEND turn into a re-check?**
The conflict resolver returns `recheck_in_minutes`. The backend needs a queue or scheduler to re-evaluate qualifying merchants after that delay. For the demo: implement a simple in-memory heap with `heapq`. Don't bother with Redis.

---

## Quick Start Checklist for Finn

```
□ 1. Create payone_sim.db by running seed_all_merchants()
□ 2. Implement GET /payone/density/{merchant_id} — polling from SQLite
□ 3. Implement POST /conflict/resolve — rule engine, pure Python
□ 4. Implement POST /offer/validate-qr — token validation + log update
□ 5. Implement POST /offer/redemption-confirm — cashback trigger
□ 6. Wire enforce_hard_rails() into the offer generation pipeline (after Claude API call)
□ 7. Verify the demo trace: social user 140m from Bar Unter at 21:00
     → density: PRIORITY, occupancy 22%, predicted 58%, milestone active
     → resolve_conflict → RECOMMEND_WITH_FRAMING, band: building_momentum
     → offer sent, QR generated, Spark animation fires
```

The trace above is the money moment of the demo. Everything should be designed so that specific scenario works perfectly.

---

*Ask Lars if anything here conflicts with what he's building on the offer generation side. The integration contracts in Part 8 are the handshake points.*
