from spark.services.distance import distance_points, estimate_distance_m
from spark.services.location_cells import latlon_to_h3


MUNICH_CENTER = latlon_to_h3(48.137154, 11.576124)
MUNICH_NORTH = latlon_to_h3(48.153000, 11.576124)


def test_estimate_distance_same_grid_is_stable_and_close() -> None:
    d1 = estimate_distance_m(
        user_grid_cell=MUNICH_CENTER,
        merchant_grid_cell=MUNICH_CENTER,
        merchant_id="MERCHANT_001",
        merchant_lat=48.137154,
        merchant_lon=11.576124,
    )
    d2 = estimate_distance_m(
        user_grid_cell=MUNICH_CENTER,
        merchant_grid_cell=MUNICH_CENTER,
        merchant_id="MERCHANT_001",
        merchant_lat=48.137154,
        merchant_lon=11.576124,
    )
    assert d1 == d2
    assert d1 < 250


def test_estimate_distance_other_grid_is_farther() -> None:
    distance = estimate_distance_m(
        user_grid_cell=MUNICH_CENTER,
        merchant_grid_cell=MUNICH_NORTH,
        merchant_id="MERCHANT_002",
        merchant_lat=48.153000,
        merchant_lon=11.576124,
    )
    assert distance > 800


def test_distance_points_decrease_with_distance() -> None:
    assert distance_points(100) > distance_points(350) > distance_points(900)
