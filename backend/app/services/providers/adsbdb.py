from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.services.cache import TTLMemoryCache


@dataclass(frozen=True)
class RouteAirport:
    name: str | None
    iata: str | None
    icao: str | None
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True)
class AdsbdbCallsignEnrichment:
    airline_name: str | None
    flight_number: str | None
    flight_iata: str | None
    flight_icao: str | None
    origin_airport: RouteAirport | None
    destination_airport: RouteAirport | None


@dataclass(frozen=True)
class AdsbdbLookupResult:
    found: bool
    enrichment: AdsbdbCallsignEnrichment | None


class AdsbdbClientError(Exception):
    pass


class AdsbdbClient:
    _cache = TTLMemoryCache[AdsbdbLookupResult](ttl_seconds=300)

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def lookup_callsign(self, callsign: str) -> AdsbdbLookupResult:
        cache_key = callsign.upper()
        cached = type(self)._cache.get(cache_key)
        if cached:
            return cached

        try:
            async with httpx.AsyncClient(
                base_url=self.settings.adsbdb_base_url,
                timeout=self.settings.http_timeout_seconds,
            ) as client:
                response = await client.get(f"/callsign/{cache_key}")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AdsbdbClientError("ADSBDB callsign lookup failed.") from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise AdsbdbClientError("ADSBDB returned an unexpected payload.")

        response_payload = payload.get("response")
        if not isinstance(response_payload, dict):
            result = AdsbdbLookupResult(found=False, enrichment=None)
            type(self)._cache.set(cache_key, result)
            return result

        route = response_payload.get("flightroute")
        if not isinstance(route, dict):
            result = AdsbdbLookupResult(found=False, enrichment=None)
            type(self)._cache.set(cache_key, result)
            return result

        enrichment = AdsbdbCallsignEnrichment(
            airline_name=((route.get("airline") or {}).get("name")),
            flight_number=_extract_flight_number(
                (route.get("callsign_iata") or route.get("callsign_icao") or cache_key)
            ),
            flight_iata=route.get("callsign_iata"),
            flight_icao=route.get("callsign_icao") or cache_key,
            origin_airport=_parse_airport(route.get("origin")),
            destination_airport=_parse_airport(route.get("destination")),
        )
        result = AdsbdbLookupResult(found=True, enrichment=enrichment)
        type(self)._cache.set(cache_key, result)
        return result


def _extract_flight_number(callsign: str) -> str | None:
    normalized = callsign.strip().upper()
    if len(normalized) < 4:
        return None

    if len(normalized) >= 3 and normalized[:3].isalpha():
        suffix = normalized[3:]
        if suffix:
            return suffix

    if len(normalized) >= 2 and normalized[:2].isalpha():
        suffix = normalized[2:]
        if suffix:
            return suffix

    return None


def _parse_airport(raw_airport: dict | None) -> RouteAirport | None:
    if not raw_airport:
        return None

    airport = RouteAirport(
        name=raw_airport.get("name"),
        iata=raw_airport.get("iata_code"),
        icao=raw_airport.get("icao_code"),
        latitude=(
            float(raw_airport["latitude"]) if raw_airport.get("latitude") is not None else None
        ),
        longitude=(
            float(raw_airport["longitude"]) if raw_airport.get("longitude") is not None else None
        ),
    )
    if airport.name or airport.iata or airport.icao:
        return airport
    return None


def clear_adsbdb_cache() -> None:
    AdsbdbClient._cache.clear()
