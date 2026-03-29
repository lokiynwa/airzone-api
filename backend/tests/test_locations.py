import respx
from fastapi.testclient import TestClient
from httpx import Response


@respx.mock
def test_geocode_caches_external_results(client: TestClient) -> None:
    route = respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=Response(
            200,
            json=[
                {
                    "display_name": "London, Greater London, England, United Kingdom",
                    "lat": "51.5074456",
                    "lon": "-0.1277653",
                }
            ],
        )
    )

    first_response = client.get("/api/v1/locations/geocode", params={"q": "London"})
    second_response = client.get("/api/v1/locations/geocode", params={"q": "London"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert route.call_count == 1
    assert first_response.json()["results"][0]["label"].startswith("London")
    assert second_response.json() == first_response.json()


@respx.mock
def test_geocode_returns_empty_results_for_unknown_location(client: TestClient) -> None:
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=Response(200, json=[])
    )

    response = client.get("/api/v1/locations/geocode", params={"q": "asldkfjalskdfj"})

    assert response.status_code == 200
    assert response.json() == {"query": "asldkfjalskdfj", "results": []}


def test_geocode_rejects_blank_query(client: TestClient) -> None:
    response = client.get("/api/v1/locations/geocode", params={"q": " "})

    assert response.status_code == 422
