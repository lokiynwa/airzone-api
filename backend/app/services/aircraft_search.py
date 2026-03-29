import asyncio
from datetime import UTC, datetime, timedelta

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
from app.services.providers.adsbdb import (
    AdsbdbClient,
    RouteAirport,
    clear_adsbdb_cache,
)
from app.services.providers.aviationstack import (
    AviationstackClient,
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
    clear_adsbdb_cache()
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


async def _lookup_route_data(
    *,
    settings: Settings,
    results: list[AircraftResult],
) -> tuple[dict[str, object], bool]:
    callsigns = sorted({result.callsign for result in results if result.callsign})
    if not callsigns:
        return {}, False

    provider = AdsbdbClient(settings)
    semaphore = asyncio.Semaphore(12)

    async def fetch(callsign: str) -> object:
        async with semaphore:
            return await provider.lookup_callsign(callsign)

    responses = await asyncio.gather(
        *(fetch(callsign) for callsign in callsigns),
        return_exceptions=True,
    )
    mapped: dict[str, object] = {}
    for callsign, response in zip(callsigns, responses, strict=True):
        mapped[callsign] = response
    return mapped, True


def _airport_reference(raw_airport) -> AirportReference | None:
    if raw_airport is None:
        return None
    return AirportReference(
        name=raw_airport.name,
        iata=raw_airport.iata,
        icao=raw_airport.icao,
    )


def _estimated_arrival_time(
    *,
    result: AircraftResult,
    destination_airport: RouteAirport | None,
) -> datetime | None:
    if destination_airport is None:
        return None
    if destination_airport.latitude is None or destination_airport.longitude is None:
        return None
    if result.position.speed_kph is None or result.position.speed_kph < 80:
        return None

    distance_km = haversine_km(
        lat1=result.position.latitude,
        lon1=result.position.longitude,
        lat2=destination_airport.latitude,
        lon2=destination_airport.longitude,
    )
    if distance_km <= 3:
        return result.position.last_seen_at or datetime.now(UTC)

    effective_speed_kph = max(result.position.speed_kph, 200.0)
    base_time = result.position.last_seen_at or datetime.now(UTC)
    return base_time + timedelta(hours=distance_km / effective_speed_kph)


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
            is_civil_best_effort=state.is_civil_best_effort,
            missing_fields=[],
            enrichment_status="not_available",
        )
        result.missing_fields = _missing_fields(result)
        results_with_distance.append((distance, result))

    results = [result for _, result in sorted(results_with_distance, key=lambda item: item[0])]
    route_lookup_results, route_lookup_used = await _lookup_route_data(
        settings=settings,
        results=results,
    )
    route_enriched_callsigns: set[str] = set()
    for result in results:
        route_lookup = route_lookup_results.get(result.callsign)
        if (
            not isinstance(route_lookup, Exception)
            and route_lookup is not None
            and route_lookup.found
        ):
            route_enrichment = route_lookup.enrichment
            if route_enrichment is not None:
                result.airline_name = route_enrichment.airline_name or result.airline_name
                result.flight_number = route_enrichment.flight_number or result.flight_number
                result.flight_iata = route_enrichment.flight_iata or result.flight_iata
                result.flight_icao = route_enrichment.flight_icao or result.flight_icao
                result.origin_airport = _airport_reference(route_enrichment.origin_airport)
                result.destination_airport = _airport_reference(
                    route_enrichment.destination_airport
                )
                result.arrival_time_estimated = (
                    result.arrival_time_estimated
                    or _estimated_arrival_time(
                        result=result,
                        destination_airport=route_enrichment.destination_airport,
                    )
                )
                route_enriched_callsigns.add(result.callsign)
    aviationstack_results, aviationstack_used = await _lookup_enrichment(
        settings=settings,
        results=results,
    )
    enrichment_used = route_lookup_used or aviationstack_used
    partial_results = False
    for result in results:
        enrichment_applied = result.callsign in route_enriched_callsigns

        lookup = aviationstack_results.get(result.flight_icao) if result.flight_icao else None
        if (
            lookup is not None
            and not isinstance(lookup, Exception)
            and lookup.found
            and lookup.enrichment is not None
        ):
            enrichment = lookup.enrichment
            result.airline_name = enrichment.airline_name or result.airline_name
            result.flight_number = enrichment.flight_number or result.flight_number
            result.flight_iata = enrichment.flight_iata or result.flight_iata
            result.flight_icao = enrichment.flight_icao or result.flight_icao
            result.origin_airport = (
                _airport_reference(enrichment.origin_airport) or result.origin_airport
            )
            result.destination_airport = (
                _airport_reference(enrichment.destination_airport) or result.destination_airport
            )
            result.arrival_time_estimated = (
                enrichment.arrival_time_estimated or result.arrival_time_estimated
            )
            enrichment_applied = True

        result.missing_fields = _missing_fields(result)
        if enrichment_applied:
            enrichment_missing = [
                field for field in result.missing_fields if field in _ENRICHMENT_FIELDS
            ]
            result.enrichment_status = "complete" if not enrichment_missing else "partial"
        else:
            result.enrichment_status = "not_available"
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
