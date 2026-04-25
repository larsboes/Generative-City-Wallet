"""
Cypher query strings for the user knowledge graph.

Centralized so the repository stays focused on Python orchestration and
all Cypher is reviewable in one place.
"""

from __future__ import annotations

# ── User session ──────────────────────────────────────────────────────────────

ENSURE_USER_SESSION = """
MERGE (u:UserSession {session_id: $session_id})
ON CREATE SET u.created_at_unix = $now,
              u.last_seen_unix = $now,
              u.offers_today = 0
ON MATCH  SET u.last_seen_unix = $now
RETURN u.session_id AS session_id
"""

# ── Merchant catalogue (mirrored from SQLite) ────────────────────────────────

UPSERT_MERCHANT = """
MERGE (m:Merchant {id: $merchant_id})
SET m.name = $name,
    m.category = $category,
    m.grid_cell = $grid_cell,
    m.address = coalesce($address, m.address)
WITH m
MERGE (c:MerchantCategory {name: $category})
MERGE (m)-[:IN_CATEGORY]->(c)
RETURN m.id AS id
"""

# ── Offer write path ──────────────────────────────────────────────────────────

# Records:
#   (UserSession)-[:RECEIVED_OFFER {ts}]->(Offer)
#   (Offer)-[:AT_MERCHANT]->(Merchant)
#   (Offer)-[:GENERATED_IN]->(ContextSnapshot)
WRITE_OFFER = """
MERGE (u:UserSession {session_id: $session_id})
ON CREATE SET u.created_at_unix = $now, u.offers_today = 0
SET u.last_seen_unix = $now,
    u.offers_today = coalesce(u.offers_today, 0) + 1
WITH u
MERGE (m:Merchant {id: $merchant_id})
ON CREATE SET m.name = $merchant_name, m.category = $merchant_category
WITH u, m
MERGE (cat:MerchantCategory {name: $merchant_category})
MERGE (m)-[:IN_CATEGORY]->(cat)
CREATE (o:Offer {
    offer_id: $offer_id,
    created_at_unix: $now,
    framing_band: $framing_band,
    density_signal: $density_signal,
    drop_pct: $drop_pct,
    distance_m: $distance_m,
    coupon_type: $coupon_type,
    discount_pct: $discount_pct,
    status: 'SENT'
})
CREATE (ctx:ContextSnapshot {
    timestamp: $timestamp,
    grid_cell: $grid_cell,
    movement_mode: $movement_mode,
    time_bucket: $time_bucket,
    weather_need: $weather_need,
    vibe_signal: $vibe_signal,
    temp_c: $temp_c,
    social_preference: $social_preference,
    occupancy_pct: $occupancy_pct,
    predicted_occupancy_pct: $predicted_occupancy_pct
})
CREATE (u)-[:RECEIVED_OFFER {ts_unix: $now}]->(o)
CREATE (o)-[:AT_MERCHANT]->(m)
CREATE (o)-[:GENERATED_IN]->(ctx)
RETURN o.offer_id AS offer_id
"""

# ── Outcome edges (accept / decline / expire / redeem) ───────────────────────

RECORD_OFFER_OUTCOME = """
MATCH (u:UserSession {session_id: $session_id})
MATCH (o:Offer {offer_id: $offer_id})
SET o.status = $status,
    o.outcome_at_unix = $now
MERGE (u)-[r:HAD_OUTCOME {offer_id: $offer_id}]->(o)
SET r.status = $status,
    r.ts_unix = $now,
    r.latency_sec = $now - coalesce(o.created_at_unix, $now)
RETURN o.offer_id AS offer_id
"""

# ── Redemption + wallet ──────────────────────────────────────────────────────

WRITE_REDEMPTION = """
MATCH (u:UserSession {session_id: $session_id})
MATCH (o:Offer {offer_id: $offer_id})
SET o.status = 'REDEEMED', o.outcome_at_unix = $now
MERGE (r:Redemption {offer_id: $offer_id})
SET r.validated_at_unix = $now,
    r.discount_value = $discount_value,
    r.discount_type = $discount_type
MERGE (r)-[:FOR_OFFER]->(o)
MERGE (u)-[hr:HAD_OUTCOME {offer_id: $offer_id}]->(o)
SET hr.status = 'REDEEMED', hr.ts_unix = $now
RETURN r.offer_id AS offer_id
"""

WRITE_WALLET_EVENT = """
MATCH (r:Redemption {offer_id: $offer_id})
MERGE (w:WalletEvent {offer_id: $offer_id})
SET w.amount_eur = $amount_eur,
    w.credited_at_unix = $now
MERGE (w)-[:CREDIT_FOR]->(r)
RETURN w.offer_id AS offer_id
"""

# ── Preference reinforcement ─────────────────────────────────────────────────

# delta is positive for reinforcement, negative for decay.
REINFORCE_CATEGORY = """
MERGE (u:UserSession {session_id: $session_id})
ON CREATE SET u.created_at_unix = $now
MERGE (c:MerchantCategory {name: $category})
MERGE (u)-[p:PREFERS]->(c)
ON CREATE SET p.weight = $base_weight,
              p.created_at_unix = $now,
              p.source_type = $source_type,
              p.last_reinforced_unix = $now
ON MATCH  SET p.weight = CASE
                   WHEN coalesce(p.weight, 0) + $delta > 1.0 THEN 1.0
                   WHEN coalesce(p.weight, 0) + $delta < 0.0 THEN 0.0
                   ELSE coalesce(p.weight, 0) + $delta
                 END,
              p.last_reinforced_unix = $now,
              p.source_type = coalesce(p.source_type, $source_type)
RETURN p.weight AS weight
"""

# ── Read path: preference scores ─────────────────────────────────────────────

GET_PREFERENCE_SCORES = """
MATCH (u:UserSession {session_id: $session_id})-[p:PREFERS]->(c:MerchantCategory)
RETURN c.name AS category,
       p.weight AS weight,
       p.last_reinforced_unix AS last_reinforced_unix,
       p.source_type AS source_type
ORDER BY p.weight DESC
LIMIT $limit
"""

# ── Read path: rule inputs ───────────────────────────────────────────────────

# Number of offers sent to this user for a given merchant since `since_unix`.
COUNT_RECENT_OFFERS_FOR_MERCHANT = """
MATCH (u:UserSession {session_id: $session_id})-[:RECEIVED_OFFER]->(o:Offer)-[:AT_MERCHANT]->(m:Merchant {id: $merchant_id})
WHERE o.created_at_unix >= $since_unix
RETURN count(o) AS count,
       max(o.created_at_unix) AS last_unix
"""

# Most recent offers (offer_id, merchant_id, category, status, ts) for this user.
GET_RECENT_OFFERS = """
MATCH (u:UserSession {session_id: $session_id})-[:RECEIVED_OFFER]->(o:Offer)-[:AT_MERCHANT]->(m:Merchant)
RETURN o.offer_id AS offer_id,
       o.created_at_unix AS created_at_unix,
       o.status AS status,
       m.id AS merchant_id,
       m.category AS category
ORDER BY o.created_at_unix DESC
LIMIT $limit
"""

# Number of offers in the lookback window for the entire session (anti-spam).
COUNT_SESSION_OFFERS = """
MATCH (u:UserSession {session_id: $session_id})-[:RECEIVED_OFFER]->(o:Offer)
WHERE o.created_at_unix >= $since_unix
RETURN count(o) AS count
"""

# ── Admin / debug ────────────────────────────────────────────────────────────

GRAPH_STATS = """
RETURN
  count { (:UserSession) }             AS user_sessions,
  count { (:Merchant) }                AS merchants,
  count { (:MerchantCategory) }        AS categories,
  count { (:Offer) }                   AS offers,
  count { (:Redemption) }              AS redemptions,
  count { (:WalletEvent) }             AS wallet_events,
  count { ()-[r:PREFERS]->() }         AS prefers_edges
"""
