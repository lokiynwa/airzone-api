import respx
from fastapi.testclient import TestClient
from httpx import Response


def _state(
    *,
    icao24: str,
    callsign: str,
    lon: float,
    lat: float,
    on_ground: bool,
    velocity: float = 200.0,
    heading: float = 90.0,
    geo_altitude: float | None = 10000.0,
    category: int | None = 5,
    last_contact: int = 1_743_200_000,
) -> list[object]:
    return [
        icao24,
        callsign,
        "United Kingdom",
        last_contact,
        last_contact,
        lon,
        lat,
        9800.0,
        on_ground,
        velocity,
        heading,
        None,
        None,
        geo_altitude,
        None,
        False,
        0,
        category,
    ]


@respx.mock
def test_aircraft_search_filters_radius_and_non_civil_records(
    authenticated_client: TestClient,
) -> None:
    respx.get("https://opensky-network.org/api/states/all").mock(
        return_value=Response(
            200,
            json={
                "time": 1_743_200_000,
                "states": [
                    _state(
                        icao24="400001",
                        callsign="BAW123",
                        lon=-0.1278,
                        lat=51.5074,
                        on_ground=False,
                    ),
                    _state(
                        icao24="400002",
                        callsign="UAV001",
                        lon=-0.1278,
                        lat=51.5075,
                        on_ground=False,
                        category=14,
                    ),
                    _state(
                        icao24="400003",
                        callsign="GROUNDED",
                        lon=-0.1278,
                        lat=51.5076,
                        on_ground=True,
                    ),
                    _state(
                        icao24="400004",
                        callsign="BAW999",
                        lon=-0.1278,
                        lat=51.60,
                        on_ground=False,
                    ),
                ],
            },
        )
    )

    response = authenticated_client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.5074, "lon": -0.1278, "radius_km": 10, "label": "London"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["search_center"]["label"] == "London"
    assert len(payload["results"]) == 1
    assert payload["results"][0]["icao24"] == "400001"
    assert payload["provider_meta"] == {
        "opensky_used": True,
        "enrichment_used": False,
        "partial_results": True,
    }


@respx.mock
def test_aircraft_search_normalizes_partial_live_state(authenticated_client: TestClient) -> None:
    respx.get("https://opensky-network.org/api/states/all").mock(
        return_value=Response(
            200,
            json={
                "time": 1_743_200_000,
                "states": [
                    _state(
                        icao24="400001",
                        callsign="BAW123",
                        lon=-0.1278,
                        lat=51.5074,
                        on_ground=False,
                    )
                ],
            },
        )
    )

    response = authenticated_client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.5074, "lon": -0.1278, "radius_km": 10},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["callsign"] == "BAW123"
    assert result["flight_icao"] == "BAW123"
    assert result["flight_number"] == "123"
    assert result["airline_name"] is None
    assert result["position"]["speed_kph"] == 720.0
    assert result["enrichment_status"] == "not_requested"
    assert "origin_airport" in result["missing_fields"]
    assert "arrival_time_estimated" in result["missing_fields"]


def test_aircraft_search_requires_authentication(client: TestClient) -> None:
    response = client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.5074, "lon": -0.1278, "radius_km": 10},
    )

    assert response.status_code == 401
