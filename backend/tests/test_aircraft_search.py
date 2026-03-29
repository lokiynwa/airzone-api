import respx
from fastapi.testclient import TestClient
from httpx import ReadTimeout, Response


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


def _adsbdb_missing_response() -> Response:
    return Response(200, json={"response": "unknown callsign"})


def _adsbdb_route_response(
    *,
    callsign: str,
    callsign_iata: str,
    airline_name: str,
    airline_icao: str,
    airline_iata: str,
    origin_name: str,
    origin_iata: str,
    origin_icao: str,
    origin_lat: float,
    origin_lon: float,
    destination_name: str,
    destination_iata: str,
    destination_icao: str,
    destination_lat: float,
    destination_lon: float,
) -> Response:
    return Response(
        200,
        json={
            "response": {
                "flightroute": {
                    "callsign": callsign,
                    "callsign_icao": callsign,
                    "callsign_iata": callsign_iata,
                    "airline": {
                        "name": airline_name,
                        "icao": airline_icao,
                        "iata": airline_iata,
                    },
                    "origin": {
                        "name": origin_name,
                        "iata_code": origin_iata,
                        "icao_code": origin_icao,
                        "latitude": origin_lat,
                        "longitude": origin_lon,
                    },
                    "destination": {
                        "name": destination_name,
                        "iata_code": destination_iata,
                        "icao_code": destination_icao,
                        "latitude": destination_lat,
                        "longitude": destination_lon,
                    },
                }
            }
        },
    )


@respx.mock
def test_aircraft_search_filters_radius_but_keeps_unknown_categories(
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
                        category=0,
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
    respx.get("https://api.adsbdb.com/v0/callsign/BAW123").mock(
        return_value=_adsbdb_missing_response()
    )
    respx.get("https://api.adsbdb.com/v0/callsign/UAV001").mock(
        return_value=_adsbdb_missing_response()
    )

    response = authenticated_client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.5074, "lon": -0.1278, "radius_km": 10, "label": "London"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["search_center"]["label"] == "London"
    assert {result["icao24"] for result in payload["results"]} == {"400001", "400002"}
    assert payload["provider_meta"] == {
        "opensky_used": True,
        "enrichment_used": True,
        "partial_results": True,
    }
    uav_result = next(result for result in payload["results"] if result["icao24"] == "400002")
    assert uav_result["is_civil_best_effort"] is False


@respx.mock
def test_aircraft_search_parses_extended_callsign_suffixes_when_route_data_missing(
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
                        callsign="EZY89VK",
                        lon=-0.1278,
                        lat=51.5074,
                        on_ground=False,
                        category=0,
                    )
                ],
            },
        )
    )
    respx.get("https://api.adsbdb.com/v0/callsign/EZY89VK").mock(
        return_value=_adsbdb_missing_response()
    )

    response = authenticated_client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.5074, "lon": -0.1278, "radius_km": 10},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["callsign"] == "EZY89VK"
    assert result["flight_icao"] == "EZY89VK"
    assert result["flight_number"] == "89VK"
    assert result["airline_name"] is None
    assert result["position"]["speed_kph"] == 720.0
    assert result["enrichment_status"] == "not_available"
    assert "origin_airport" in result["missing_fields"]
    assert "arrival_time_estimated" in result["missing_fields"]


@respx.mock
def test_aircraft_search_applies_public_route_enrichment_without_aviationstack(
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
                        callsign="EZY89VK",
                        lon=-3.45,
                        lat=53.82,
                        on_ground=False,
                        category=0,
                    )
                ],
            },
        )
    )
    respx.get("https://api.adsbdb.com/v0/callsign/EZY89VK").mock(
        return_value=_adsbdb_route_response(
            callsign="EZY89VK",
            callsign_iata="U289VK",
            airline_name="easyJet",
            airline_icao="EZY",
            airline_iata="U2",
            origin_name="Belfast International Airport",
            origin_iata="BFS",
            origin_icao="EGAA",
            origin_lat=54.6575,
            origin_lon=-6.21583,
            destination_name="Liverpool John Lennon Airport",
            destination_iata="LPL",
            destination_icao="EGGP",
            destination_lat=53.333599,
            destination_lon=-2.84972,
        )
    )

    response = authenticated_client.get(
        "/api/v1/aircraft/search",
        params={"lat": 53.8, "lon": -3.4, "radius_km": 100},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["airline_name"] == "easyJet"
    assert result["flight_iata"] == "U289VK"
    assert result["origin_airport"]["iata"] == "BFS"
    assert result["origin_airport"]["latitude"] == 54.6575
    assert result["destination_airport"]["icao"] == "EGGP"
    assert result["destination_airport"]["longitude"] == -2.84972
    assert result["arrival_time_estimated"] is not None
    assert result["enrichment_status"] == "complete"
    assert response.json()["provider_meta"]["enrichment_used"] is True


@respx.mock
def test_aircraft_search_handles_missing_enrichment(
    aviationstack_authenticated_client: TestClient,
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
                    )
                ],
            },
        )
    )
    respx.get("https://api.adsbdb.com/v0/callsign/BAW123").mock(
        return_value=_adsbdb_missing_response()
    )
    respx.get("https://api.aviationstack.com/v1/flights").mock(
        return_value=Response(200, json={"data": []})
    )

    response = aviationstack_authenticated_client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.5074, "lon": -0.1278, "radius_km": 10},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["enrichment_status"] == "not_available"
    assert result["airline_name"] is None
    assert response.json()["provider_meta"]["enrichment_used"] is True


@respx.mock
def test_aircraft_search_survives_aviationstack_timeout_when_public_route_data_exists(
    aviationstack_authenticated_client: TestClient,
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
                        lon=-0.25,
                        lat=51.45,
                        on_ground=False,
                    )
                ],
            },
        )
    )
    respx.get("https://api.adsbdb.com/v0/callsign/BAW123").mock(
        return_value=_adsbdb_route_response(
            callsign="BAW123",
            callsign_iata="BA123",
            airline_name="British Airways",
            airline_icao="BAW",
            airline_iata="BA",
            origin_name="Heathrow Airport",
            origin_iata="LHR",
            origin_icao="EGLL",
            origin_lat=51.4706,
            origin_lon=-0.461941,
            destination_name="John F. Kennedy International Airport",
            destination_iata="JFK",
            destination_icao="KJFK",
            destination_lat=40.6398,
            destination_lon=-73.7789,
        )
    )
    respx.get("https://api.aviationstack.com/v1/flights").mock(
        side_effect=ReadTimeout("timed out")
    )

    response = aviationstack_authenticated_client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.45, "lon": -0.25, "radius_km": 20},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["airline_name"] == "British Airways"
    assert result["destination_airport"]["icao"] == "KJFK"
    assert result["arrival_time_estimated"] is not None
    assert result["enrichment_status"] == "complete"


@respx.mock
def test_aircraft_search_supports_mixed_enrichment_results(
    aviationstack_authenticated_client: TestClient,
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
                        callsign="DLH400",
                        lon=-0.1280,
                        lat=51.5075,
                        on_ground=False,
                    ),
                ],
            },
        )
    )
    respx.get("https://api.adsbdb.com/v0/callsign/BAW123").mock(
        return_value=_adsbdb_route_response(
            callsign="BAW123",
            callsign_iata="BA123",
            airline_name="British Airways",
            airline_icao="BAW",
            airline_iata="BA",
            origin_name="Heathrow Airport",
            origin_iata="LHR",
            origin_icao="EGLL",
            origin_lat=51.4706,
            origin_lon=-0.461941,
            destination_name="John F. Kennedy International Airport",
            destination_iata="JFK",
            destination_icao="KJFK",
            destination_lat=40.6398,
            destination_lon=-73.7789,
        )
    )
    respx.get("https://api.adsbdb.com/v0/callsign/DLH400").mock(
        return_value=_adsbdb_missing_response()
    )
    route = respx.get("https://api.aviationstack.com/v1/flights")
    route.side_effect = [
        Response(200, json={"data": []}),
        Response(200, json={"data": []}),
    ]

    response = aviationstack_authenticated_client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.5074, "lon": -0.1278, "radius_km": 10},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["enrichment_status"] == "complete"
    assert results[1]["enrichment_status"] == "not_available"
    assert response.json()["provider_meta"]["partial_results"] is True


def test_aircraft_search_requires_authentication(client: TestClient) -> None:
    response = client.get(
        "/api/v1/aircraft/search",
        params={"lat": 51.5074, "lon": -0.1278, "radius_km": 10},
    )

    assert response.status_code == 401
