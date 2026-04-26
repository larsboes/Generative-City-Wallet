"""Cypher queries for preference read/write and decay."""

from __future__ import annotations

REINFORCE_CATEGORY = """
MERGE (u:UserSession {session_id: $session_id})
ON CREATE SET u.created_at_unix = $now
MERGE (c:MerchantCategory {name: $category})
MERGE (u)-[p:PREFERS]->(c)
ON CREATE SET p.weight = $base_weight,
              p.created_at_unix = $now,
              p.source_type = $source_type,
              p.last_reinforced_unix = $now,
              p.decay_rate = $decay_rate,
              p.source_confidence = $source_confidence,
              p.artifact_count = $artifact_count
ON MATCH  SET p.weight = CASE
                   WHEN coalesce(p.weight, 0) + $delta > 1.0 THEN 1.0
                   WHEN coalesce(p.weight, 0) + $delta < 0.0 THEN 0.0
                   ELSE coalesce(p.weight, 0) + $delta
                 END,
              p.last_reinforced_unix = $now,
              p.decay_rate = coalesce(p.decay_rate, $decay_rate),
              p.source_type = coalesce(p.source_type, $source_type),
              p.source_confidence = coalesce($source_confidence, p.source_confidence),
              p.artifact_count = coalesce($artifact_count, p.artifact_count)
RETURN p.weight AS weight
"""

GET_PREFERENCE_SCORES = """
MATCH (u:UserSession {session_id: $session_id})-[p:PREFERS]->(c:MerchantCategory)
RETURN c.name AS category,
       p.weight AS weight,
       p.last_reinforced_unix AS last_reinforced_unix,
       p.source_type AS source_type,
       p.decay_rate AS decay_rate,
       p.source_confidence AS source_confidence,
       p.artifact_count AS artifact_count
ORDER BY p.weight DESC
LIMIT $limit
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
