from app.services.geo import bounding_box_for_radius, haversine_km


def test_haversine_distance_for_close_points() -> None:
    distance = haversine_km(
        lat1=51.5074,
        lon1=-0.1278,
        lat2=51.509865,
        lon2=-0.118092,
    )

    assert round(distance, 2) == 0.73


def test_bounding_box_expands_around_center() -> None:
    bbox = bounding_box_for_radius(lat=51.5074, lon=-0.1278, radius_km=25)

    assert bbox.lamin < 51.5074 < bbox.lamax
    assert bbox.lomin < -0.1278 < bbox.lomax
    assert round(bbox.lamax - bbox.lamin, 2) == 0.45

