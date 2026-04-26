from spark.services.distance import distance_points, estimate_distance_m


def test_estimate_distance_same_grid_is_stable_and_close() -> None:
    d1 = estimate_distance_m(
        user_grid_cell="STR-MITTE-047",
        merchant_grid_cell="STR-MITTE-047",
        merchant_id="MERCHANT_001",
    )
    d2 = estimate_distance_m(
        user_grid_cell="STR-MITTE-047",
        merchant_grid_cell="STR-MITTE-047",
        merchant_id="MERCHANT_001",
    )
    assert d1 == d2
    assert 60 <= d1 <= 129


def test_estimate_distance_other_grid_is_farther() -> None:
    distance = estimate_distance_m(
        user_grid_cell="STR-MITTE-047",
        merchant_grid_cell="STR-WEST-002",
        merchant_id="MERCHANT_002",
    )
    assert 220 <= distance <= 399


def test_distance_points_decrease_with_distance() -> None:
    assert distance_points(100) > distance_points(220) > distance_points(380)
