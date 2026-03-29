from fastapi.testclient import TestClient


def test_register_sets_cookie_and_returns_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "pilot@example.com", "password": "supersecure"},
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "pilot@example.com"
    assert "airzone_session" in response.cookies


def test_duplicate_registration_returns_conflict(client: TestClient) -> None:
    payload = {"email": "pilot@example.com", "password": "supersecure"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "A user with this email already exists."


def test_login_rejects_invalid_password(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "pilot@example.com", "password": "supersecure"},
    )
    client.cookies.clear()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "pilot@example.com", "password": "wrongpass"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_me_returns_authenticated_user(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "pilot@example.com", "password": "supersecure"},
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "pilot@example.com"


def test_logout_clears_session(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "pilot@example.com", "password": "supersecure"},
    )

    logout_response = client.post("/api/v1/auth/logout")
    me_response = client.get("/api/v1/auth/me")

    assert logout_response.status_code == 204
    assert "airzone_session" not in client.cookies
    assert me_response.status_code == 401
    assert me_response.json()["detail"] == "Authentication required."
