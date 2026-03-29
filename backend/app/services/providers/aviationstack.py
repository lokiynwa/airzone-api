from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import Settings
from app.services.cache import TTLMemoryCache


@dataclass(frozen=True)
class AirportData:
    name: str | None
    iata: str | None
    icao: str | None


@dataclass(frozen=True)
class AviationstackEnrichment:
    airline_name: str | None
    flight_number: str | None
    flight_iata: str | None
    flight_icao: str | None
    origin_airport: AirportData | None
    destination_airport: AirportData | None
    arrival_time_estimated: datetime | None


@dataclass(frozen=True)
class AviationstackLookupResult:
    found: bool
    enrichment: AviationstackEnrichment | None


class AviationstackClientError(Exception):
    pass


class AviationstackClient:
    _cache = TTLMemoryCache[AviationstackLookupResult](ttl_seconds=60)

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def lookup_flight(self, flight_icao: str) -> AviationstackLookupResult:
        cache_key = flight_icao.upper()
        cached = type(self)._cache.get(cache_key)
        if cached:
            return cached

        if not self.settings.aviationstack_api_key:
            return AviationstackLookupResult(found=False, enrichment=None)

        try:
            async with httpx.AsyncClient(
                base_url=self.settings.aviationstack_base_url,
                timeout=self.settings.http_timeout_seconds,
            ) as client:
                response = await client.get(
                    "/flights",
                    params={
                        "access_key": self.settings.aviationstack_api_key,
                        "flight_icao": cache_key,
                        "limit": 1,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AviationstackClientError("aviationstack lookup failed.") from exc

        payload = response.json()
        if "error" in payload:
            raise AviationstackClientError("aviationstack returned an API error.")

        records = payload.get("data") or []
        matched_record = next(
            (
                record
                for record in records
                if ((record.get("flight") or {}).get("icao") or "").upper() == cache_key
            ),
            None,
        )

        if matched_record is None:
            result = AviationstackLookupResult(found=False, enrichment=None)
            type(self)._cache.set(cache_key, result)
            return result

        enrichment = AviationstackEnrichment(
            airline_name=(matched_record.get("airline") or {}).get("name"),
            flight_number=(matched_record.get("flight") or {}).get("number"),
            flight_iata=(matched_record.get("flight") or {}).get("iata"),
            flight_icao=(matched_record.get("flight") or {}).get("icao"),
            origin_airport=_airport_from_record(matched_record.get("departure")),
            destination_airport=_airport_from_record(matched_record.get("arrival")),
            arrival_time_estimated=_parse_datetime(
                (matched_record.get("arrival") or {}).get("estimated")
                or (matched_record.get("arrival") or {}).get("scheduled")
            ),
        )
        result = AviationstackLookupResult(found=True, enrichment=enrichment)
        type(self)._cache.set(cache_key, result)
        return result


def _airport_from_record(raw_airport: dict | None) -> AirportData | None:
    if not raw_airport:
        return None
    airport = AirportData(
        name=raw_airport.get("airport"),
        iata=raw_airport.get("iata"),
        icao=raw_airport.get("icao"),
    )
    if airport.name or airport.iata or airport.icao:
        return airport
    return None


def _parse_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    cleaned = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def clear_aviationstack_cache() -> None:
    AviationstackClient._cache.clear()

