from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SearchCenter(BaseModel):
    lat: float
    lon: float
    label: str | None = None


class AirportReference(BaseModel):
    name: str | None = None
    iata: str | None = None
    icao: str | None = None


class AircraftPosition(BaseModel):
    latitude: float
    longitude: float
    altitude_m: float | None = None
    heading_deg: float | None = None
    speed_kph: float | None = None
    last_seen_at: datetime | None = None


class AircraftResult(BaseModel):
    icao24: str
    callsign: str
    airline_name: str | None = None
    flight_number: str | None = None
    flight_iata: str | None = None
    flight_icao: str | None = None
    origin_airport: AirportReference | None = None
    destination_airport: AirportReference | None = None
    arrival_time_estimated: datetime | None = None
    position: AircraftPosition
    is_civil_best_effort: bool
    missing_fields: list[str]
    enrichment_status: Literal["not_requested", "not_available", "partial", "complete"]


class ProviderMeta(BaseModel):
    opensky_used: bool
    enrichment_used: bool
    partial_results: bool


class AircraftSearchResponse(BaseModel):
    search_center: SearchCenter
    radius_km: float
    results: list[AircraftResult]
    provider_meta: ProviderMeta

