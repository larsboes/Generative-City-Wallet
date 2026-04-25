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
SET u.last_seen_unix = $now
WITH u
MERGE (m:Merchant {id: $merchant_id})
ON CREATE SET m.name = $merchant_name, m.category = $merchant_category
WITH u, m
MERGE (cat:MerchantCategory {name: $merchant_category})
MERGE (m)-[:IN_CATEGORY]->(cat)
MERGE (o:Offer {offer_id: $offer_id})
ON CREATE SET o.created_at_unix = $now
SET o.framing_band = $framing_band,
    o.density_signal = $density_signal,
    o.drop_pct = $drop_pct,
    o.distance_m = $distance_m,
    o.coupon_type = $coupon_type,
    o.discount_pct = $discount_pct,
    o.status = 'SENT'
WITH u, m, o
MERGE (ctx:ContextSnapshot {offer_id: $offer_id})
SET ctx.timestamp = $timestamp,
    ctx.grid_cell = $grid_cell,
    ctx.movement_mode = $movement_mode,
    ctx.time_bucket = $time_bucket,
    ctx.weather_need = $weather_need,
    ctx.vibe_signal = $vibe_signal,
    ctx.temp_c = $temp_c,
    ctx.social_preference = $social_preference,
    ctx.occupancy_pct = $occupancy_pct,
    ctx.predicted_occupancy_pct = $predicted_occupancy_pct
MERGE (u)-[ro:RECEIVED_OFFER {offer_id: $offer_id}]->(o)
SET ro.ts_unix = coalesce(ro.ts_unix, $now)
MERGE (o)-[:AT_MERCHANT]->(m)
MERGE (o)-[:GENERATED_IN]->(ctx)
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
              p.last_reinforced_unix = $now,
              p.decay_rate = $decay_rate
ON MATCH  SET p.weight = CASE
                   WHEN coalesce(p.weight, 0) + $delta > 1.0 THEN 1.0
                   WHEN coalesce(p.weight, 0) + $delta < 0.0 THEN 0.0
                   ELSE coalesce(p.weight, 0) + $delta
                 END,
              p.last_reinforced_unix = $now,
              p.decay_rate = coalesce(p.decay_rate, $decay_rate),
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

CLEANUP_OLD_OFFERS = """
MATCH (o:Offer)
WHERE coalesce(o.created_at_unix, 0) < $cutoff_unix
OPTIONAL MATCH (o)-[:GENERATED_IN]->(ctx:ContextSnapshot)
OPTIONAL MATCH (r:Redemption)-[:FOR_OFFER]->(o)
OPTIONAL MATCH (w:WalletEvent)-[:CREDIT_FOR]->(r)
WITH collect(DISTINCT w) AS ws,
     collect(DISTINCT r) AS rs,
     collect(DISTINCT ctx) AS cs,
     collect(DISTINCT o) AS os
FOREACH (w IN ws | DETACH DELETE w)
FOREACH (r IN rs | DETACH DELETE r)
FOREACH (c IN cs | DETACH DELETE c)
FOREACH (o IN os | DETACH DELETE o)
RETURN
  size(os) AS offers_deleted,
  size(cs) AS contexts_deleted,
  size(rs) AS redemptions_deleted,
  size(ws) AS wallet_events_deleted
"""

CLEANUP_STALE_SESSIONS = """
MATCH (u:UserSession)
WHERE coalesce(u.last_seen_unix, u.created_at_unix, 0) < $cutoff_unix
  AND NOT (u)-[:RECEIVED_OFFER]->(:Offer)
WITH collect(u) AS users
FOREACH (u IN users | DETACH DELETE u)
RETURN size(users) AS sessions_deleted
"""

CLEANUP_OLD_PREFERENCE_EDGES = """
MATCH (:UserSession)-[p:PREFERS|AVOIDS]->(:MerchantCategory|:Attribute)
WHERE coalesce(p.last_reinforced_unix, p.created_at_unix, 0) < $cutoff_unix
WITH collect(p) AS edges
FOREACH (e IN edges | DELETE e)
RETURN size(edges) AS preference_edges_deleted
"""

DECAY_STALE_PREFERENCES = """
MATCH (:UserSession)-[p:PREFERS]->(:MerchantCategory)
WHERE coalesce(p.last_reinforced_unix, p.created_at_unix, 0) < $stale_cutoff_unix
WITH p,
     coalesce(p.weight, 0.5) AS current_weight,
     (($now_unix - coalesce(p.last_reinforced_unix, p.created_at_unix, $now_unix)) / 86400.0) AS age_days,
     coalesce(p.decay_rate, $default_decay_rate) AS decay_rate
WITH p, current_weight, age_days, decay_rate,
     (current_weight - (age_days * decay_rate)) AS raw_weight
SET p.weight = CASE
        WHEN raw_weight < 0.0 THEN 0.0
        WHEN raw_weight > 1.0 THEN 1.0
        ELSE raw_weight
    END,
    p.last_decay_unix = $now_unix,
    p.decay_rate = decay_rate
RETURN count(p) AS edges_touched
"""

GET_MIGRATION_STATUS = """
MATCH (m:GraphMigration)
RETURN m.id AS id, m.description AS description, m.applied_at_unix AS applied_at_unix
ORDER BY m.applied_at_unix ASC
"""
