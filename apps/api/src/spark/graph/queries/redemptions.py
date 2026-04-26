"""Cypher queries for redemption and wallet concerns."""

from __future__ import annotations

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
