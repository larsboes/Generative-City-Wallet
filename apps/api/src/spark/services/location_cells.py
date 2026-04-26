from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt

import h3

from spark.config import SPARK_H3_RESOLUTION

DEFAULT_H3_RESOLUTION = SPARK_H3_RESOLUTION


def latlon_to_h3(lat: float, lon: float, resolution: int = DEFAULT_H3_RESOLUTION) -> str:
    return h3.latlng_to_cell(lat, lon, resolution)


def is_valid_h3(cell: str) -> bool:
    return h3.is_valid_cell(cell)


def neighbor_cells(cell: str, k: int) -> list[str]:
    if k < 1:
        return []
    if not is_valid_h3(cell):
        return []
    ring = h3.grid_disk(cell, k)
    return sorted(other for other in ring if other != cell)


def h3_centroid(cell: str) -> tuple[float, float] | None:
    if not is_valid_h3(cell):
        return None
    lat, lon = h3.cell_to_latlng(cell)
    return float(lat), float(lon)


def haversine_distance_m(
    lat_a: float, lon_a: float, lat_b: float, lon_b: float
) -> float:
    earth_radius_m = 6_371_000.0
    phi_1 = radians(lat_a)
    phi_2 = radians(lat_b)
    delta_phi = radians(lat_b - lat_a)
    delta_lambda = radians(lon_b - lon_a)
    hav = (
        sin(delta_phi / 2.0) ** 2
        + cos(phi_1) * cos(phi_2) * sin(delta_lambda / 2.0) ** 2
    )
    return 2.0 * earth_radius_m * atan2(sqrt(hav), sqrt(1.0 - hav))
