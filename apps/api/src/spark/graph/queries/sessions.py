"""Cypher queries for session lifecycle concerns."""

from __future__ import annotations

ENSURE_USER_SESSION = """
MERGE (u:UserSession {session_id: $session_id})
ON CREATE SET u.created_at_unix = $now,
              u.last_seen_unix = $now,
              u.offers_today = 0
ON MATCH  SET u.last_seen_unix = $now
RETURN u.session_id AS session_id
"""

COUNT_SESSION_OFFERS = """
MATCH (u:UserSession {session_id: $session_id})-[:RECEIVED_OFFER]->(o:Offer)
WHERE o.created_at_unix >= $since_unix
RETURN count(o) AS count
"""
