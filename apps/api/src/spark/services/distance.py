from __future__ import annotations

import hashlib


def estimate_distance_m(
    *,
    user_grid_cell: str,
    merchant_grid_cell: str | None,
    merchant_id: str,
) -> float:
    """
    Deterministic distance estimate using available location abstractions.

    We only have quantized grid cells on backend in MVP, so this function
    returns a stable estimate (not precise GPS distance) suitable for ranking
    and explainability metadata.
    """
    token = f"{user_grid_cell}|{merchant_grid_cell or 'unknown'}|{merchant_id}"
    bucket = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
    if merchant_grid_cell and merchant_grid_cell == user_grid_cell:
        return float(60 + (bucket % 70))  # 60..129m same-grid estimate
    return float(220 + (bucket % 180))  # 220..399m nearby-grid estimate


def distance_points(distance_m: float) -> float:
    """Map estimated distance to deterministic ranking points."""
    if distance_m <= 120:
        return 25.0
    if distance_m <= 250:
        return 18.0
    if distance_m <= 400:
        return 10.0
    return 5.0
