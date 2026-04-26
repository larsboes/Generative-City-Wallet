from __future__ import annotations

import hashlib

from spark.services.location_cells import h3_centroid, haversine_distance_m


def estimate_distance_m(
    *,
    user_grid_cell: str,
    merchant_grid_cell: str | None,
    merchant_id: str,
    merchant_lat: float | None = None,
    merchant_lon: float | None = None,
) -> float:
    """
    Geo-aware distance estimate using H3 cell + merchant coordinates when available.
    """
    user_centroid = h3_centroid(user_grid_cell)
    if user_centroid is not None:
        user_lat, user_lon = user_centroid
        if merchant_lat is not None and merchant_lon is not None:
            return float(
                haversine_distance_m(
                    user_lat, user_lon, float(merchant_lat), float(merchant_lon)
                )
            )

        merchant_centroid = h3_centroid(merchant_grid_cell or "")
        if merchant_centroid is not None:
            return float(
                haversine_distance_m(
                    user_lat, user_lon, merchant_centroid[0], merchant_centroid[1]
                )
            )

    # Deterministic fallback to keep demos resilient if invalid/missing location data appears.
    token = f"{user_grid_cell}|{merchant_grid_cell or 'unknown'}|{merchant_id}"
    bucket = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
    if merchant_grid_cell and merchant_grid_cell == user_grid_cell:
        return float(80 + (bucket % 110))  # 80..189m same-cell fallback
    return float(350 + (bucket % 650))  # 350..999m cross-cell fallback


def distance_points(distance_m: float) -> float:
    """Map estimated distance in meters to deterministic ranking points."""
    if distance_m <= 150:
        return 25.0
    if distance_m <= 400:
        return 18.0
    if distance_m <= 800:
        return 10.0
    return 5.0
