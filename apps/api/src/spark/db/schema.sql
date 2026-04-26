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
    grid_cell   TEXT NOT NULL DEFAULT '891f8d7a49bffff'
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

-- ── Graph Projection Idempotency / Retention ─────────────────────────────────

CREATE TABLE IF NOT EXISTS graph_event_log (
    idempotency_key      TEXT PRIMARY KEY,
    event_type           TEXT NOT NULL,
    session_id           TEXT,
    offer_id             TEXT,
    source               TEXT NOT NULL,
    category             TEXT,
    source_event_id      TEXT,
    payload_hash         TEXT,
    created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_graph_event_log_created_at
    ON graph_event_log(created_at);
CREATE INDEX IF NOT EXISTS idx_graph_event_log_session_event
    ON graph_event_log(session_id, event_type);
CREATE INDEX IF NOT EXISTS idx_graph_event_log_category
    ON graph_event_log(category);

-- ── Learning Attribution + Metrics ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS preference_update_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT NOT NULL,
    category            TEXT NOT NULL,
    source_type         TEXT NOT NULL,
    event_type          TEXT NOT NULL,
    event_key           TEXT NOT NULL,
    source_event_id     TEXT,
    before_weight       REAL,
    delta               REAL NOT NULL,
    after_weight        REAL,
    outcome             TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pref_update_log_session_category
    ON preference_update_log(session_id, category, created_at);

CREATE TABLE IF NOT EXISTS learning_metrics_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name         TEXT NOT NULL,
    metric_value        REAL NOT NULL,
    metric_group        TEXT,
    session_id          TEXT,
    category            TEXT,
    source_type         TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_learning_metrics_log_name
    ON learning_metrics_log(metric_name, created_at);

-- ── Spark Wave (social coordination, anonymous + TTL-bounded) ─────────────────

CREATE TABLE IF NOT EXISTS spark_waves (
    wave_id              TEXT PRIMARY KEY,
    offer_id             TEXT NOT NULL,
    merchant_id          TEXT NOT NULL,
    created_by_session   TEXT NOT NULL,
    participant_count    INTEGER NOT NULL DEFAULT 1,
    milestone_target     INTEGER NOT NULL DEFAULT 3,
    expires_at           TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE | COMPLETED | EXPIRED
    created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (offer_id) REFERENCES offer_audit_log(offer_id)
);

CREATE INDEX IF NOT EXISTS idx_spark_waves_offer
    ON spark_waves(offer_id);

-- ── Venue Occupancy (Finn's transaction-based demand system) ──────────────────

CREATE TABLE IF NOT EXISTS venues (
    merchant_id     TEXT PRIMARY KEY,
    osm_type        TEXT,
    osm_id          TEXT,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    lat             REAL NOT NULL,
    lon             REAL NOT NULL,
    city            TEXT,
    address         TEXT,
    website         TEXT,
    phone           TEXT,
    opening_hours   TEXT,
    source          TEXT NOT NULL DEFAULT 'openstreetmap',
    raw_tags_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_venues_category ON venues(category);
CREATE INDEX IF NOT EXISTS idx_venues_city ON venues(city);
CREATE INDEX IF NOT EXISTS idx_venues_lat_lon ON venues(lat, lon);

CREATE TABLE IF NOT EXISTS transaction_baselines (
    merchant_id             TEXT NOT NULL,
    hour_of_week            INTEGER NOT NULL CHECK(hour_of_week BETWEEN 0 AND 167),
    historical_avg_txn_rate REAL NOT NULL CHECK(historical_avg_txn_rate >= 0),
    sample_count            INTEGER NOT NULL DEFAULT 0,
    source                  TEXT NOT NULL DEFAULT 'synthetic',
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (merchant_id, hour_of_week),
    FOREIGN KEY (merchant_id) REFERENCES venues(merchant_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS current_signals (
    merchant_id         TEXT PRIMARY KEY,
    current_txn_rate    REAL NOT NULL CHECK(current_txn_rate >= 0),
    observed_at         TEXT NOT NULL,
    source              TEXT NOT NULL DEFAULT 'demo_override',
    FOREIGN KEY (merchant_id) REFERENCES venues(merchant_id) ON DELETE CASCADE
);

-- Individual-transaction table (used by Finn's demand signal system).
-- Kept separate from payone_transactions (aggregated hourly buckets for offer engine).
CREATE TABLE IF NOT EXISTS venue_transactions (
    transaction_id  TEXT PRIMARY KEY,
    merchant_id     TEXT NOT NULL,
    category        TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    hour_of_day     INTEGER NOT NULL CHECK(hour_of_day BETWEEN 0 AND 23),
    day_of_week     INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    hour_of_week    INTEGER NOT NULL CHECK(hour_of_week BETWEEN 0 AND 167),
    amount_eur      REAL NOT NULL CHECK(amount_eur >= 0),
    currency        TEXT NOT NULL DEFAULT 'EUR',
    source          TEXT NOT NULL DEFAULT 'synthetic',
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (merchant_id) REFERENCES venues(merchant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_venue_txn_merchant_timestamp
    ON venue_transactions(merchant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_venue_txn_merchant_category_timestamp
    ON venue_transactions(merchant_id, category, timestamp);
CREATE INDEX IF NOT EXISTS idx_venue_txn_merchant_hour_of_week
    ON venue_transactions(merchant_id, hour_of_week, timestamp);

-- ── Identity Links (cross-session continuity) ───────────────────────────────

CREATE TABLE IF NOT EXISTS identity_links (
    continuity_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    linked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (continuity_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_identity_links_continuity
    ON identity_links(continuity_id);
CREATE INDEX IF NOT EXISTS idx_identity_links_session
    ON identity_links(session_id);
