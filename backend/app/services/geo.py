from dataclasses import dataclass
from math import asin, cos, degrees, pi, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class BoundingBox:
    lamin: float
    lomin: float
    lamax: float
    lomax: float


def haversine_km(*, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_KM * c


def bounding_box_for_radius(*, lat: float, lon: float, radius_km: float) -> BoundingBox:
    angular_distance = radius_km / EARTH_RADIUS_KM
    lat_delta = degrees(angular_distance)
    cos_lat = cos(radians(lat))
    if abs(cos_lat) < 1e-12:
        lon_delta = 180.0
    else:
        lon_delta = degrees(min(pi, angular_distance / abs(cos_lat)))

    return BoundingBox(
        lamin=max(-90.0, lat - lat_delta),
        lomin=max(-180.0, lon - lon_delta),
        lamax=min(90.0, lat + lat_delta),
        lomax=min(180.0, lon + lon_delta),
    )

