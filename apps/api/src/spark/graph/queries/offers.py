"""Cypher queries for offer write/read and outcomes."""

from __future__ import annotations

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

COUNT_RECENT_OFFERS_FOR_MERCHANT = """
MATCH (u:UserSession {session_id: $session_id})-[:RECEIVED_OFFER]->(o:Offer)-[:AT_MERCHANT]->(m:Merchant {id: $merchant_id})
WHERE o.created_at_unix >= $since_unix
RETURN count(o) AS count,
       max(o.created_at_unix) AS last_unix
"""

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
