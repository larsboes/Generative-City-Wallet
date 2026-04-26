"""Cypher queries for graph maintenance and diagnostics."""

from __future__ import annotations

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
MATCH (:UserSession)-[p]->(target)
WHERE type(p) IN ['PREFERS', 'AVOIDS']
  AND any(lbl IN labels(target) WHERE lbl IN ['MerchantCategory', 'Attribute'])
  AND coalesce(p.last_reinforced_unix, p.created_at_unix, 0) < $cutoff_unix
WITH collect(p) AS edges
FOREACH (e IN edges | DELETE e)
RETURN size(edges) AS preference_edges_deleted
"""

GET_MIGRATION_STATUS = """
MATCH (m:GraphMigration)
RETURN m.id AS id, m.description AS description, m.applied_at_unix AS applied_at_unix
ORDER BY m.applied_at_unix ASC
"""
