"""Cypher queries for merchant catalogue concerns."""

from __future__ import annotations

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
