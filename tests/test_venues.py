from backend.app import db
from backend.app.services.venues import haversine_m, list_venues


def test_haversine_distance_for_nearby_points() -> None:
    distance = haversine_m(48.137154, 11.576124, 48.1375, 11.5765)
    assert 40 <= distance <= 60


def test_list_venues_filters_category_city_and_radius(tmp_path) -> None:
    db_path = tmp_path / "occupancy.db"
    db.upsert_venues(
        db_path,
        [
            {
                "merchant_id": "osm_node_1",
                "osm_type": "node",
                "osm_id": "1",
                "name": "Nearby Cafe",
                "category": "cafe",
                "lat": 48.137154,
                "lon": 11.576124,
                "city": "München",
            },
            {
                "merchant_id": "osm_node_2",
                "osm_type": "node",
                "osm_id": "2",
                "name": "Far Cafe",
                "category": "cafe",
                "lat": 48.150000,
                "lon": 11.590000,
                "city": "München",
            },
        ],
    )

    with db.connect(db_path) as conn:
        venues = list_venues(
            conn,
            category="cafe",
            city="München",
            lat=48.1372,
            lon=11.5762,
            radius_m=100,
        )

    assert [venue.merchant_id for venue in venues] == ["osm_node_1"]
