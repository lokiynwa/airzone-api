from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Airzone API"
    app_env: str = "development"
    app_debug: bool = True
    database_url: str = "sqlite:///./airzone.db"
    session_cookie_name: str = "airzone_session"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 168
    http_timeout_seconds: float = 10.0
    cors_allow_origins_raw: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ALLOW_ORIGINS",
    )
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "airzone-api/0.1 (local development)"
    opensky_base_url: str = "https://opensky-network.org"
    opensky_auth_url: str = (
        "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    )
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cors_allow_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins_raw.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
