from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Scotch API configuration, overridable via environment / .env."""

    app_name: str = "scotch"
    version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(env_prefix="SCOTCH_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
