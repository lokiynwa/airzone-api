import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";

const fetchMock = vi.fn();

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TileLayer: () => null,
  Marker: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CircleMarker: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Polyline: () => null,
  Popup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useMap: () => ({
    getZoom: () => 8,
    setView: vi.fn(),
  }),
  useMapEvents: () => ({}),
}));

describe("authentication shell", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    cleanup();
    fetchMock.mockReset();
    window.history.pushState({}, "", "/");
  });

  it("logs a user in and navigates to the app shell", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Authentication required." }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ user: { id: 1, email: "pilot@example.com" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    window.history.pushState({}, "", "/login");
    const user = userEvent.setup();

    render(<App />);

    await user.type(await screen.findByLabelText(/email/i), "pilot@example.com");
    await user.type(screen.getByLabelText(/password/i), "supersecure");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    await screen.findByText(/airzone flight deck/i);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({
        credentials: "include",
        method: "POST",
      }),
    );
  });

  it("restores a logged-in session on refresh", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ user: { id: 1, email: "pilot@example.com" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    window.history.pushState({}, "", "/app");
    render(<App />);

    await waitFor(() => expect(screen.getByText(/search radius/i)).toBeInTheDocument());
    expect(screen.getByText(/signed in as/i)).toHaveTextContent("pilot@example.com");
  });

  it("searches for aircraft and renders route details with full airport names", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/auth/me")) {
        return Promise.resolve(
          new Response(JSON.stringify({ user: { id: 1, email: "pilot@example.com" } }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (url.includes("/locations/geocode")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              query: "London",
              results: [{ label: "London, United Kingdom", lat: 51.5074, lon: -0.1278 }],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/aircraft/search")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              search_center: { lat: 51.5074, lon: -0.1278, label: "London, United Kingdom" },
              radius_km: 25,
              provider_meta: {
                opensky_used: true,
                enrichment_used: true,
                partial_results: true,
              },
              results: [
                {
                  icao24: "400001",
                  callsign: "BAW123",
                  airline_name: null,
                  flight_number: "123",
                  flight_iata: null,
                  flight_icao: "BAW123",
                  origin_airport: {
                    name: "Heathrow Airport",
                    iata: "LHR",
                    icao: "EGLL",
                    latitude: 51.4706,
                    longitude: -0.461941,
                  },
                  destination_airport: {
                    name: "Manchester Airport",
                    iata: "MAN",
                    icao: "EGCC",
                    latitude: 53.3537,
                    longitude: -2.27495,
                  },
                  arrival_time_estimated: "2026-03-29T13:15:00Z",
                  position: {
                    latitude: 51.5,
                    longitude: -0.12,
                    altitude_m: 10000,
                    heading_deg: 120,
                    speed_kph: 700,
                    last_seen_at: "2026-03-29T12:00:00Z",
                  },
                  is_civil_best_effort: true,
                  missing_fields: [
                    "airline_name",
                    "flight_iata",
                  ],
                  enrichment_status: "partial",
                },
              ],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }

      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });

    window.history.pushState({}, "", "/app");
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText(/airzone flight deck/i);
    await user.type(screen.getByPlaceholderText(/search for a city or airport/i), "London");
    await user.click(await screen.findByRole("button", { name: /london, united kingdom/i }));
    await user.click(screen.getByRole("button", { name: /search aircraft/i }));

    const matches = await screen.findAllByText("BAW123");
    expect(matches.length).toBeGreaterThan(0);
    expect(screen.getAllByText(/partial data/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/some flights are still missing route or eta data/i)).toBeInTheDocument();
    expect(
      screen.getAllByText(/heathrow airport \(LHR \/ EGLL\) to manchester airport \(MAN \/ EGCC\)/i)
        .length,
    ).toBeGreaterThan(0);
    expect(screen.getByText(/origin: heathrow airport \(LHR \/ EGLL\)/i)).toBeInTheDocument();
    expect(screen.getByText(/destination: manchester airport \(MAN \/ EGCC\)/i)).toBeInTheDocument();
    expect(screen.getByText(/selected flight/i)).toBeInTheDocument();
    expect(screen.getByText(/last updated:/i)).toBeInTheDocument();
  });
});
