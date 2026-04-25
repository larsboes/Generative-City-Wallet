-- Spark SQLite Schema
-- All tables for the hackathon MVP.

-- ── Merchants ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS merchants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,        -- cafe | bakery | bar | restaurant | club | retail
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    address     TEXT NOT NULL DEFAULT '',
    grid_cell   TEXT NOT NULL DEFAULT 'STR-MITTE-047'
);

-- ── Payone Transactions (hourly buckets) ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS payone_transactions (
    merchant_id     TEXT NOT NULL,
    merchant_type   TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    hour_of_day     INTEGER NOT NULL,
    day_of_week     INTEGER NOT NULL,  -- 0=Monday, 6=Sunday
    hour_of_week    INTEGER NOT NULL,  -- 0-167
    txn_count       INTEGER NOT NULL,
    total_volume_eur REAL NOT NULL,
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

CREATE INDEX IF NOT EXISTS idx_merchant_hour
    ON payone_transactions(merchant_id, hour_of_week);

CREATE INDEX IF NOT EXISTS idx_merchant_ts
    ON payone_transactions(merchant_id, timestamp);

-- ── Merchant Coupons ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS merchant_coupons (
    merchant_id     TEXT NOT NULL,
    coupon_type     TEXT NOT NULL,       -- FLASH | MILESTONE | TIME_BOUND | DRINK | VISIBILITY_ONLY
    config          TEXT NOT NULL DEFAULT '{}',  -- JSON
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    expires_at      TEXT,
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

-- ── Milestone Progress (daily) ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS milestone_progress (
    merchant_id     TEXT NOT NULL,
    session_date    TEXT NOT NULL,       -- YYYY-MM-DD
    current_guests  INTEGER NOT NULL DEFAULT 0,
    target_guests   INTEGER NOT NULL,
    milestone_fired INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (merchant_id, session_date)
);

-- ── Offer Audit Log ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS offer_audit_log (
    offer_id            TEXT PRIMARY KEY,
    created_at          TEXT NOT NULL,

    -- User context (anonymized)
    session_id          TEXT,
    grid_cell           TEXT,
    movement_mode       TEXT,
    social_preference   TEXT,

    -- Merchant + venue state
    merchant_id         TEXT,
    density_signal      TEXT,
    density_score       REAL,
    current_occupancy_pct   REAL,
    predicted_occupancy_pct REAL,

    -- Conflict resolution
    conflict_check      TEXT,
    conflict_resolution TEXT,
    framing_band        TEXT,

    -- Coupon
    coupon_type         TEXT,
    coupon_config       TEXT,   -- JSON

    -- LLM output (pre-rails)
    llm_raw_output      TEXT,   -- JSON

    -- Final offer (post-rails)
    final_offer         TEXT,   -- JSON
    rails_audit         TEXT,   -- JSON

    -- Lifecycle
    status              TEXT NOT NULL DEFAULT 'SENT',  -- SENT | ACCEPTED | DECLINED | EXPIRED | REDEEMED
    accepted_at         TEXT,
    redeemed_at         TEXT,
    declined_at         TEXT,
    expired_at          TEXT
);

-- ── Wallet Transactions ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS wallet_transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    offer_id        TEXT NOT NULL,
    amount_eur      REAL NOT NULL,
    merchant_name   TEXT NOT NULL,
    credited_at     TEXT NOT NULL,
    FOREIGN KEY (offer_id) REFERENCES offer_audit_log(offer_id)
);
