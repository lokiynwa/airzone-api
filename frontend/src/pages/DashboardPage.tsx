import { useQuery } from "@tanstack/react-query";
import { divIcon } from "leaflet";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/AuthProvider";
import {
  AircraftResult,
  GeocodeLocation,
  geocodeLocations,
  searchAircraft,
} from "../features/search/api";
import { useDebouncedValue } from "../features/search/useDebouncedValue";

const DEFAULT_CENTER: [number, number] = [51.5074, -0.1278];

type ActiveSearch = {
  lat: number;
  lon: number;
  radiusKm: number;
  label: string;
};

function formatAirport(airport: AircraftResult["origin_airport"]) {
  if (!airport) {
    return "Unknown airport";
  }

  const codes = [airport.iata, airport.icao].filter(Boolean).join(" / ");
  if (airport.name && codes) {
    return `${airport.name} (${codes})`;
  }
  return airport.name || codes || "Unknown airport";
}

function formatRoute(result: AircraftResult) {
  return `${formatAirport(result.origin_airport)} to ${formatAirport(result.destination_airport)}`;
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

function formatShortTimestamp(timestamp: number) {
  if (timestamp === 0) {
    return "Waiting for first scan";
  }

  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}

function formatLastSeen(timestamp: string | null) {
  if (!timestamp) {
    return "Unavailable";
  }

  return new Intl.DateTimeFormat("en-GB", {
    timeStyle: "short",
  }).format(new Date(timestamp));
}

function buildRoutePath(result: AircraftResult) {
  const routePoints: [number, number][] = [];

  const originPoint = getAirportCoordinates(result.origin_airport);
  const destinationPoint = getAirportCoordinates(result.destination_airport);

  if (originPoint) {
    routePoints.push(originPoint);
  }

  routePoints.push([result.position.latitude, result.position.longitude]);

  if (destinationPoint) {
    routePoints.push(destinationPoint);
  }

  return routePoints.length >= 2 ? routePoints : null;
}

function getAirportCoordinates(airport: AircraftResult["origin_airport"]) {
  if (
    airport?.latitude === null ||
    airport?.latitude === undefined ||
    airport.longitude === null ||
    airport.longitude === undefined
  ) {
    return null;
  }

  return [airport.latitude, airport.longitude] as [number, number];
}

function createAircraftIcon(result: AircraftResult, isSelected: boolean) {
  const heading = result.position.heading_deg ?? 0;
  const fillColor = isSelected ? "#0b4f78" : "#0c8bb0";

  return divIcon({
    className: "aircraft-marker-wrapper",
    iconSize: [48, 48],
    iconAnchor: [24, 24],
    popupAnchor: [0, -22],
    html: `
      <div class="aircraft-marker${isSelected ? " is-selected" : ""}" style="--heading:${heading}deg;">
        <svg viewBox="0 0 64 64" aria-hidden="true">
          <path
            fill="${fillColor}"
            d="M31.5 4.5c1.9 0 3.3 1.4 3.7 3.6l3.1 18.1 18.5 6.6c1.5.5 2.5 1.9 2.5 3.5s-1 3-2.5 3.5l-18.5 6.6-3.1 10.7c-.4 1.4-1.6 2.4-3 2.4s-2.7-1-3-2.4l-3.1-10.7-18.5-6.6c-1.5-.5-2.5-1.9-2.5-3.5s1-3 2.5-3.5l18.5-6.6 3.1-18.1c.4-2.2 1.8-3.6 3.8-3.6Z"
          />
        </svg>
      </div>
    `,
  });
}

function MapRecenter({ latitude, longitude }: { latitude: number; longitude: number }) {
  const map = useMap();

  useEffect(() => {
    map.setView([latitude, longitude], map.getZoom(), { animate: true });
  }, [latitude, longitude, map]);

  return null;
}

function MapSelectionHandler({ onClearSelection }: { onClearSelection: () => void }) {
  useMapEvents({
    click: () => onClearSelection(),
  });

  return null;
}

function ResultMap({
  center,
  results,
  selectedAircraft,
  onSelect,
  onClearSelection,
}: {
  center: [number, number];
  results: AircraftResult[];
  selectedAircraft: AircraftResult | null;
  onSelect: (result: AircraftResult) => void;
  onClearSelection: () => void;
}) {
  const routePath = selectedAircraft ? buildRoutePath(selectedAircraft) : null;
  const originPoint = getAirportCoordinates(selectedAircraft?.origin_airport ?? null);
  const destinationPoint = getAirportCoordinates(selectedAircraft?.destination_airport ?? null);

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
      <MapSelectionHandler onClearSelection={onClearSelection} />
      {routePath ? (
        <Polyline
          positions={routePath}
          pathOptions={{
            color: "#0b4f78",
            weight: 4,
            opacity: 0.8,
            dashArray: "10 10",
          }}
        />
      ) : null}
      {originPoint ? (
        <CircleMarker
          center={originPoint}
          radius={7}
          pathOptions={{
            color: "#175736",
            fillColor: "#2d9b66",
            fillOpacity: 0.95,
            weight: 2,
          }}
        >
          <Popup>
            <strong>Origin</strong>
            <br />
            {formatAirport(selectedAircraft?.origin_airport ?? null)}
          </Popup>
        </CircleMarker>
      ) : null}
      {destinationPoint ? (
        <CircleMarker
          center={destinationPoint}
          radius={7}
          pathOptions={{
            color: "#915122",
            fillColor: "#e59a42",
            fillOpacity: 0.95,
            weight: 2,
          }}
        >
          <Popup>
            <strong>Destination</strong>
            <br />
            {formatAirport(selectedAircraft?.destination_airport ?? null)}
          </Popup>
        </CircleMarker>
      ) : null}
      {results.map((result) => {
        const isSelected = selectedAircraft?.icao24 === result.icao24;

        return (
          <Marker
            key={result.icao24}
            position={[result.position.latitude, result.position.longitude]}
            icon={createAircraftIcon(result, isSelected)}
            eventHandlers={{
              click: () => onSelect(result),
            }}
          >
            <Popup>
              <strong>{result.callsign}</strong>
              <br />
              {result.airline_name ?? "Airline unavailable"}
              <br />
              {formatRoute(result)}
              <br />
              ETA: {formatArrival(result.arrival_time_estimated)}
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { logout, user, isSubmitting } = useAuth();
  const [query, setQuery] = useState("");
  const [radiusKm, setRadiusKm] = useState(25);
  const [selectedLocation, setSelectedLocation] = useState<GeocodeLocation | null>(null);
  const [activeSearch, setActiveSearch] = useState<ActiveSearch | null>(null);
  const [selectedAircraftId, setSelectedAircraftId] = useState<string | null>(null);
  const [pendingAutoSelect, setPendingAutoSelect] = useState(false);
  const debouncedQuery = useDebouncedValue(query.trim(), 300);

  const locationQuery = useQuery({
    queryKey: ["locations", debouncedQuery],
    queryFn: () => geocodeLocations(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });

  const aircraftQuery = useQuery({
    queryKey: [
      "aircraft",
      activeSearch?.lat ?? null,
      activeSearch?.lon ?? null,
      activeSearch?.radiusKm ?? null,
      activeSearch?.label ?? null,
    ],
    queryFn: () => {
      if (!activeSearch) {
        throw new Error("No active aircraft search is available.");
      }

      return searchAircraft({
        lat: activeSearch.lat,
        lon: activeSearch.lon,
        radiusKm: activeSearch.radiusKm,
        label: activeSearch.label,
      });
    },
    enabled: activeSearch !== null,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
  });

  const results = aircraftQuery.data?.results ?? [];
  const isSearching = aircraftQuery.fetchStatus === "fetching";
  const selectedAircraft = useMemo(
    () => results.find((result) => result.icao24 === selectedAircraftId) ?? null,
    [results, selectedAircraftId],
  );

  useEffect(() => {
    if (!aircraftQuery.data) {
      return;
    }

    const selectedStillVisible =
      selectedAircraftId !== null &&
      aircraftQuery.data.results.some((result) => result.icao24 === selectedAircraftId);

    if (selectedStillVisible) {
      if (pendingAutoSelect) {
        setPendingAutoSelect(false);
      }
      return;
    }

    if (pendingAutoSelect && aircraftQuery.data.results[0]) {
      setSelectedAircraftId(aircraftQuery.data.results[0].icao24);
    } else if (selectedAircraftId !== null) {
      setSelectedAircraftId(null);
    }

    if (pendingAutoSelect) {
      setPendingAutoSelect(false);
    }
  }, [aircraftQuery.data, pendingAutoSelect, selectedAircraftId]);

  const searchCenter = useMemo<[number, number]>(() => {
    if (selectedAircraft) {
      return [selectedAircraft.position.latitude, selectedAircraft.position.longitude];
    }
    if (aircraftQuery.data) {
      return [aircraftQuery.data.search_center.lat, aircraftQuery.data.search_center.lon];
    }
    if (selectedLocation) {
      return [selectedLocation.lat, selectedLocation.lon];
    }
    return DEFAULT_CENTER;
  }, [aircraftQuery.data, selectedAircraft, selectedLocation]);

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  async function handleSearch() {
    if (!selectedLocation) {
      return;
    }

    const nextSearch = {
      lat: selectedLocation.lat,
      lon: selectedLocation.lon,
      radiusKm,
      label: selectedLocation.label,
    };
    const sameSearch =
      activeSearch?.lat === nextSearch.lat &&
      activeSearch?.lon === nextSearch.lon &&
      activeSearch?.radiusKm === nextSearch.radiusKm &&
      activeSearch?.label === nextSearch.label;

    setPendingAutoSelect(true);
    if (sameSearch) {
      await aircraftQuery.refetch();
      return;
    }

    setSelectedAircraftId(null);
    setActiveSearch(nextSearch);
  }

  function handleLocationPick(location: GeocodeLocation) {
    setSelectedLocation(location);
    setQuery(location.label);
  }

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
                disabled={!selectedLocation || isSearching}
                onClick={handleSearch}
              >
                {isSearching ? "Scanning aircraft..." : "Search aircraft"}
              </button>
            </section>

            <section className="feature-card results-panel">
              <div className="results-header">
                <div>
                  <h2>Aircraft in range</h2>
                  <p>
                    {aircraftQuery.data?.provider_meta.partial_results
                      ? "Some flights are still missing route or ETA data."
                      : "Showing the best current live matches."}
                  </p>
                </div>
                <span className="results-count">{results.length}</span>
              </div>

              {selectedAircraft ? (
                <article className="selected-flight-card">
                  <div className="selected-flight-header">
                    <div>
                      <p className="eyebrow">Selected flight</p>
                      <h3>{selectedAircraft.callsign}</h3>
                    </div>
                    <span
                      className={`result-badge ${
                        selectedAircraft.missing_fields.length === 0
                          ? "badge-complete"
                          : "badge-partial"
                      }`}
                    >
                      {selectedAircraft.missing_fields.length === 0 ? "Complete" : "Partial data"}
                    </span>
                  </div>
                  <p>{selectedAircraft.airline_name ?? "Airline unavailable"}</p>
                  <p>{formatRoute(selectedAircraft)}</p>
                  <p>Origin: {formatAirport(selectedAircraft.origin_airport)}</p>
                  <p>Destination: {formatAirport(selectedAircraft.destination_airport)}</p>
                  <p>ETA: {formatArrival(selectedAircraft.arrival_time_estimated)}</p>
                  <p>Last seen: {formatLastSeen(selectedAircraft.position.last_seen_at)}</p>
                </article>
              ) : results.length > 0 ? (
                <p className="empty-state">Click an aircraft to highlight its route on the map.</p>
              ) : null}

              {!activeSearch ? (
                <p className="empty-state">Pick a location to load live aircraft.</p>
              ) : null}
              {aircraftQuery.isError ? (
                <p className="error-banner">{(aircraftQuery.error as Error).message}</p>
              ) : null}
              {activeSearch && !isSearching && !aircraftQuery.isError && results.length === 0 ? (
                <p className="empty-state">No aircraft were visible in that radius during the last scan.</p>
              ) : null}
              {results.map((result) => (
                <button
                  type="button"
                  key={result.icao24}
                  className={`result-card${selectedAircraft?.icao24 === result.icao24 ? " is-active" : ""}`}
                  onClick={() => setSelectedAircraftId(result.icao24)}
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
                  <p>{formatRoute(result)}</p>
                  <p>ETA: {formatArrival(result.arrival_time_estimated)}</p>
                </button>
              ))}
            </section>
          </aside>

          <section className="map-panel">
            <div className="map-panel-header">
              <div>
                <p className="eyebrow">Live map</p>
                <h2>Aircraft positions</h2>
                <p className="map-copy">
                  Click a plane to follow its route. Click empty map space to clear the selection.
                </p>
              </div>
              <div className="map-status">
                <strong>Last updated: {formatShortTimestamp(aircraftQuery.dataUpdatedAt)}</strong>
                <span>
                  {activeSearch
                    ? aircraftQuery.isFetching
                      ? "Refreshing live positions..."
                      : "Auto-refreshes every minute."
                    : "Run a search to start live refresh."}
                </span>
              </div>
            </div>
            <ResultMap
              center={searchCenter}
              results={results}
              selectedAircraft={selectedAircraft}
              onSelect={(result) => setSelectedAircraftId(result.icao24)}
              onClearSelection={() => setSelectedAircraftId(null)}
            />
          </section>
        </div>
      </section>
    </div>
  );
}
