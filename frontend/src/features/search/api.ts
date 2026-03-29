import { apiFetch } from "../../lib/api";

export type GeocodeLocation = {
  label: string;
  lat: number;
  lon: number;
};

export type GeocodeResponse = {
  query: string;
  results: GeocodeLocation[];
};

export type AirportReference = {
  name: string | null;
  iata: string | null;
  icao: string | null;
  latitude: number | null;
  longitude: number | null;
};

export type AircraftPosition = {
  latitude: number;
  longitude: number;
  altitude_m: number | null;
  heading_deg: number | null;
  speed_kph: number | null;
  last_seen_at: string | null;
};

export type AircraftResult = {
  icao24: string;
  callsign: string;
  airline_name: string | null;
  flight_number: string | null;
  flight_iata: string | null;
  flight_icao: string | null;
  origin_airport: AirportReference | null;
  destination_airport: AirportReference | null;
  arrival_time_estimated: string | null;
  position: AircraftPosition;
  is_civil_best_effort: boolean;
  missing_fields: string[];
  enrichment_status: "not_requested" | "not_available" | "partial" | "complete";
};

export type AircraftSearchResponse = {
  search_center: {
    lat: number;
    lon: number;
    label: string | null;
  };
  radius_km: number;
  results: AircraftResult[];
  provider_meta: {
    opensky_used: boolean;
    enrichment_used: boolean;
    partial_results: boolean;
  };
};

export async function geocodeLocations(query: string) {
  const params = new URLSearchParams({ q: query });
  return apiFetch<GeocodeResponse>(`/locations/geocode?${params.toString()}`);
}

export async function searchAircraft(params: {
  lat: number;
  lon: number;
  radiusKm: number;
  label?: string;
}) {
  const searchParams = new URLSearchParams({
    lat: params.lat.toString(),
    lon: params.lon.toString(),
    radius_km: params.radiusKm.toString(),
  });
  if (params.label) {
    searchParams.set("label", params.label);
  }

  return apiFetch<AircraftSearchResponse>(`/aircraft/search?${searchParams.toString()}`);
}
