import asyncio

from app.core.config import Settings
from app.schemas.aircraft import (
    AircraftPosition,
    AircraftResult,
    AircraftSearchResponse,
    AirportReference,
    ProviderMeta,
    SearchCenter,
)
from app.services.cache import TTLMemoryCache
from app.services.geo import bounding_box_for_radius, haversine_km
from app.services.providers.aviationstack import (
    AviationstackClient,
    AviationstackClientError,
    clear_aviationstack_cache,
)
from app.services.providers.opensky import OpenSkyClient

_search_cache = TTLMemoryCache[AircraftSearchResponse](ttl_seconds=10)
_ENRICHMENT_FIELDS = {
    "airline_name",
    "flight_number",
    "flight_iata",
    "flight_icao",
    "origin_airport",
    "destination_airport",
    "arrival_time_estimated",
}


def _cache_key(lat: float, lon: float, radius_km: float, label: str | None) -> str:
    rounded_label = (label or "").strip().lower()
    return f"{round(lat, 2)}:{round(lon, 2)}:{round(radius_km, 1)}:{rounded_label}"


def clear_aircraft_search_cache() -> None:
    _search_cache.clear()


def clear_provider_caches() -> None:
    clear_aircraft_search_cache()
    clear_aviationstack_cache()


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


async def _lookup_enrichment(
    *,
    settings: Settings,
    results: list[AircraftResult],
) -> tuple[dict[str, object], bool]:
    if not settings.aviationstack_api_key:
        return {}, False

    flight_codes = sorted({result.flight_icao for result in results if result.flight_icao})
    if not flight_codes:
        return {}, False

    provider = AviationstackClient(settings)
    responses = await asyncio.gather(
        *(provider.lookup_flight(code) for code in flight_codes),
        return_exceptions=True,
    )

    mapped: dict[str, object] = {}
    for code, response in zip(flight_codes, responses, strict=True):
        mapped[code] = response
    return mapped, True


def _airport_reference(raw_airport) -> AirportReference | None:
    if raw_airport is None:
        return None
    return AirportReference(
        name=raw_airport.name,
        iata=raw_airport.iata,
        icao=raw_airport.icao,
    )


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
        results_with_distance.append((distance, result))

    results = [result for _, result in sorted(results_with_distance, key=lambda item: item[0])]
    lookup_results, enrichment_used = await _lookup_enrichment(settings=settings, results=results)
    partial_results = False
    for result in results:
        if not result.flight_icao:
            result.missing_fields = _missing_fields(result)
            partial_results = partial_results or bool(result.missing_fields)
            continue

        lookup = lookup_results.get(result.flight_icao)
        if lookup is None:
            result.enrichment_status = "not_requested"
            result.missing_fields = _missing_fields(result)
            partial_results = partial_results or bool(result.missing_fields)
            continue
        if isinstance(lookup, Exception):
            if isinstance(lookup, AviationstackClientError):
                result.enrichment_status = "not_available"
            else:
                result.enrichment_status = "not_available"
            result.missing_fields = _missing_fields(result)
            partial_results = partial_results or bool(result.missing_fields)
            continue
        if not lookup.found or lookup.enrichment is None:
            result.enrichment_status = "not_available"
            result.missing_fields = _missing_fields(result)
            partial_results = partial_results or bool(result.missing_fields)
            continue

        enrichment = lookup.enrichment
        result.airline_name = enrichment.airline_name or result.airline_name
        result.flight_number = enrichment.flight_number or result.flight_number
        result.flight_iata = enrichment.flight_iata or result.flight_iata
        result.flight_icao = enrichment.flight_icao or result.flight_icao
        result.origin_airport = _airport_reference(enrichment.origin_airport)
        result.destination_airport = _airport_reference(enrichment.destination_airport)
        result.arrival_time_estimated = enrichment.arrival_time_estimated
        result.missing_fields = _missing_fields(result)
        enrichment_missing = [
            field for field in result.missing_fields if field in _ENRICHMENT_FIELDS
        ]
        result.enrichment_status = "complete" if not enrichment_missing else "partial"
        partial_results = partial_results or bool(result.missing_fields)

    response = AircraftSearchResponse(
        search_center=SearchCenter(lat=lat, lon=lon, label=label),
        radius_km=radius_km,
        results=results,
        provider_meta=ProviderMeta(
            opensky_used=True,
            enrichment_used=enrichment_used,
            partial_results=partial_results,
        ),
    )
    _search_cache.set(cache_key, response)
    return response
