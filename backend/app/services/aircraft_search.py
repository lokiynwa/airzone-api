from app.core.config import Settings
from app.schemas.aircraft import (
    AircraftPosition,
    AircraftResult,
    AircraftSearchResponse,
    ProviderMeta,
    SearchCenter,
)
from app.services.cache import TTLMemoryCache
from app.services.geo import bounding_box_for_radius, haversine_km
from app.services.providers.opensky import OpenSkyClient

_search_cache = TTLMemoryCache[AircraftSearchResponse](ttl_seconds=10)


def _cache_key(lat: float, lon: float, radius_km: float, label: str | None) -> str:
    rounded_label = (label or "").strip().lower()
    return f"{round(lat, 2)}:{round(lon, 2)}:{round(radius_km, 1)}:{rounded_label}"


def clear_aircraft_search_cache() -> None:
    _search_cache.clear()


def _missing_fields(result: AircraftResult) -> list[str]:
    missing: list[str] = []
    if result.airline_name is None:
        missing.append("airline_name")
    if result.flight_number is None:
        missing.append("flight_number")
    if result.flight_iata is None:
        missing.append("flight_iata")
    if result.flight_icao is None:
        missing.append("flight_icao")
    if result.origin_airport is None:
        missing.append("origin_airport")
    if result.destination_airport is None:
        missing.append("destination_airport")
    if result.arrival_time_estimated is None:
        missing.append("arrival_time_estimated")
    return missing


async def search_aircraft(
    *,
    settings: Settings,
    lat: float,
    lon: float,
    radius_km: float,
    label: str | None,
) -> AircraftSearchResponse:
    cache_key = _cache_key(lat, lon, radius_km, label)
    cached = _search_cache.get(cache_key)
    if cached:
        return cached

    bbox = bounding_box_for_radius(lat=lat, lon=lon, radius_km=radius_km)
    provider = OpenSkyClient(settings)
    states = await provider.fetch_states(bbox)

    results_with_distance: list[tuple[float, AircraftResult]] = []
    partial_results = False
    for state in states:
        distance = haversine_km(lat1=lat, lon1=lon, lat2=state.latitude, lon2=state.longitude)
        if distance > radius_km:
            continue

        result = AircraftResult(
            icao24=state.icao24,
            callsign=state.callsign,
            flight_number=state.flight_number,
            flight_icao=state.flight_icao,
            position=AircraftPosition(
                latitude=state.latitude,
                longitude=state.longitude,
                altitude_m=state.altitude_m,
                heading_deg=state.heading_deg,
                speed_kph=state.speed_kph,
                last_seen_at=state.last_seen_at,
            ),
            is_civil_best_effort=True,
            missing_fields=[],
            enrichment_status="not_requested",
        )
        result.missing_fields = _missing_fields(result)
        partial_results = partial_results or bool(result.missing_fields)
        results_with_distance.append((distance, result))

    results = [result for _, result in sorted(results_with_distance, key=lambda item: item[0])]
    response = AircraftSearchResponse(
        search_center=SearchCenter(lat=lat, lon=lon, label=label),
        radius_km=radius_km,
        results=results,
        provider_meta=ProviderMeta(
            opensky_used=True,
            enrichment_used=False,
            partial_results=partial_results,
        ),
    )
    _search_cache.set(cache_key, response)
    return response

