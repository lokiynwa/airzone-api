import { useMutation, useQuery } from "@tanstack/react-query";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/AuthProvider";
import {
  AircraftResult,
  AircraftSearchResponse,
  GeocodeLocation,
  geocodeLocations,
  searchAircraft,
} from "../features/search/api";
import { useDebouncedValue } from "../features/search/useDebouncedValue";

function formatAirport(airport: AircraftResult["origin_airport"]) {
  if (!airport) {
    return "Unknown";
  }
  return airport.iata || airport.icao || airport.name || "Unknown";
}

function formatArrival(arrivalTime: string | null) {
  if (!arrivalTime) {
    return "Unavailable";
  }

  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(arrivalTime));
}

function ResultMap({
  center,
  results,
  selectedAircraft,
  onSelect,
}: {
  center: [number, number];
  results: AircraftResult[];
  selectedAircraft: AircraftResult | null;
  onSelect: (result: AircraftResult) => void;
}) {
  return (
    <MapContainer center={center} zoom={8} className="results-map" scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapRecenter
        latitude={selectedAircraft?.position.latitude ?? center[0]}
        longitude={selectedAircraft?.position.longitude ?? center[1]}
      />
      {results.map((result) => (
        <CircleMarker
          key={result.icao24}
          center={[result.position.latitude, result.position.longitude]}
          radius={selectedAircraft?.icao24 === result.icao24 ? 9 : 7}
          pathOptions={{
            color: selectedAircraft?.icao24 === result.icao24 ? "#0b4f78" : "#0c8bb0",
            fillColor: selectedAircraft?.icao24 === result.icao24 ? "#0b4f78" : "#0c8bb0",
            fillOpacity: 0.85,
          }}
          eventHandlers={{
            click: () => onSelect(result),
          }}
        >
          <Popup>
            <strong>{result.callsign}</strong>
            <br />
            {result.airline_name ?? "Airline unavailable"}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

function MapRecenter({ latitude, longitude }: { latitude: number; longitude: number }) {
  const map = useMap();

  useEffect(() => {
    map.setView([latitude, longitude], map.getZoom(), { animate: true });
  }, [latitude, longitude, map]);

  return null;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { logout, user, isSubmitting } = useAuth();
  const [query, setQuery] = useState("");
  const [radiusKm, setRadiusKm] = useState(25);
  const [selectedLocation, setSelectedLocation] = useState<GeocodeLocation | null>(null);
  const [selectedAircraft, setSelectedAircraft] = useState<AircraftResult | null>(null);
  const debouncedQuery = useDebouncedValue(query.trim(), 300);

  const locationQuery = useQuery({
    queryKey: ["locations", debouncedQuery],
    queryFn: () => geocodeLocations(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });

  const searchMutation = useMutation({
    mutationFn: searchAircraft,
    onSuccess: (data) => {
      setSelectedAircraft(data.results[0] ?? null);
    },
  });

  const searchCenter = useMemo<[number, number]>(() => {
    if (selectedAircraft) {
      return [selectedAircraft.position.latitude, selectedAircraft.position.longitude];
    }
    if (selectedLocation) {
      return [selectedLocation.lat, selectedLocation.lon];
    }
    return [51.5074, -0.1278];
  }, [selectedAircraft, selectedLocation]);

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  async function handleSearch() {
    if (!selectedLocation) {
      return;
    }

    await searchMutation.mutateAsync({
      lat: selectedLocation.lat,
      lon: selectedLocation.lon,
      radiusKm,
      label: selectedLocation.label,
    });
  }

  function handleLocationPick(location: GeocodeLocation) {
    setSelectedLocation(location);
    setQuery(location.label);
  }

  const results = searchMutation.data?.results ?? [];
  const showSuggestions = debouncedQuery.length >= 2 && !selectedLocation;

  return (
    <div className="screen-shell">
      <section className="dashboard-shell">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Authenticated</p>
            <h1>Airzone flight deck</h1>
            <p className="summary">
              Signed in as <strong>{user?.email}</strong>. Search for a place, choose a radius, and
              inspect the live aircraft the backend can currently resolve around that point.
            </p>
          </div>
          <button className="ghost-button" onClick={handleLogout} disabled={isSubmitting}>
            Sign out
          </button>
        </header>
        <div className="workspace-layout">
          <aside className="workspace-panel">
            <section className="feature-card search-card">
              <h2>Search radius</h2>
              <label className="field-group">
                <span>Location</span>
                <input
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setSelectedLocation(null);
                  }}
                  placeholder="Search for a city or airport"
                />
              </label>
              {showSuggestions ? (
                <div className="suggestions-list">
                  {locationQuery.isLoading ? <p>Looking up locations...</p> : null}
                  {locationQuery.data?.results.map((location) => (
                    <button
                      key={`${location.lat}-${location.lon}`}
                      type="button"
                      className="suggestion-button"
                      onClick={() => handleLocationPick(location)}
                    >
                      {location.label}
                    </button>
                  ))}
                  {locationQuery.data && locationQuery.data.results.length === 0 ? (
                    <p>No matching places found.</p>
                  ) : null}
                </div>
              ) : null}
              <label className="field-group">
                <span>Radius: {radiusKm} km</span>
                <input
                  type="range"
                  min={5}
                  max={250}
                  step={5}
                  value={radiusKm}
                  onChange={(event) => setRadiusKm(Number(event.target.value))}
                />
              </label>
              <button
                type="button"
                className="primary-button"
                disabled={!selectedLocation || searchMutation.isPending}
                onClick={handleSearch}
              >
                {searchMutation.isPending ? "Scanning aircraft..." : "Search aircraft"}
              </button>
            </section>

            <section className="feature-card results-panel">
              <div className="results-header">
                <div>
                  <h2>Aircraft in range</h2>
                  <p>
                    {searchMutation.data?.provider_meta.partial_results
                      ? "Some flights are missing route or ETA data."
                      : "Showing the best current live matches."}
                  </p>
                </div>
                <span className="results-count">{results.length}</span>
              </div>

              {searchMutation.isIdle ? (
                <p className="empty-state">Pick a location to load live aircraft.</p>
              ) : null}
              {searchMutation.isError ? (
                <p className="error-banner">{(searchMutation.error as Error).message}</p>
              ) : null}
              {results.map((result) => (
                <button
                  type="button"
                  key={result.icao24}
                  className={`result-card${selectedAircraft?.icao24 === result.icao24 ? " is-active" : ""}`}
                  onClick={() => setSelectedAircraft(result)}
                >
                  <div className="result-topline">
                    <strong>{result.callsign}</strong>
                    <span
                      className={`result-badge ${
                        result.missing_fields.length === 0 ? "badge-complete" : "badge-partial"
                      }`}
                    >
                      {result.missing_fields.length === 0 ? "Complete" : "Partial data"}
                    </span>
                  </div>
                  <p>{result.airline_name ?? "Airline unavailable"}</p>
                  <p>
                    {formatAirport(result.origin_airport)} to {formatAirport(result.destination_airport)}
                  </p>
                  <p>ETA: {formatArrival(result.arrival_time_estimated)}</p>
                </button>
              ))}
            </section>
          </aside>

          <section className="map-panel">
            <ResultMap
              center={searchCenter}
              results={results}
              selectedAircraft={selectedAircraft}
              onSelect={setSelectedAircraft}
            />
          </section>
        </div>
      </section>
    </div>
  );
}
