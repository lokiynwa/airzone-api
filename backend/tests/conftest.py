from collections.abc import Generator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import build_engine, get_db
from app.main import create_app
from app.services.aircraft_search import clear_provider_caches


@contextmanager
def _test_client_context(tmp_path) -> Generator[TestClient, None, None]:
    get_settings.cache_clear()
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = build_engine(database_url)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        clear_provider_caches()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        get_settings.cache_clear()


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    with _test_client_context(tmp_path) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client: TestClient) -> TestClient:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "pilot@example.com", "password": "supersecure"},
    )
    assert response.status_code == 201
    return client


@pytest.fixture
def aviationstack_authenticated_client(
    tmp_path,
    monkeypatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("AVIATIONSTACK_API_KEY", "test-aviationstack-key")
    with _test_client_context(tmp_path) as test_client:
        response = test_client.post(
            "/api/v1/auth/register",
            json={"email": "pilot@example.com", "password": "supersecure"},
        )
        assert response.status_code == 201
        yield test_client
