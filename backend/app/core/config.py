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
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

