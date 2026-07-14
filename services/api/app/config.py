from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Scotch API configuration, overridable via environment / .env."""

    app_name: str = "scotch"
    version: str = "0.1.0"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # Storage: "local" today; cloud backends register in storage/factory.py (Phase 18).
    storage_backend: str = "local"
    data_dir: Path = Path(__file__).resolve().parent / "data"
    # Phase 43: vendored interior-design furniture catalog (committed to git,
    # not user data) — models/, thumbnails/, catalog.json live here.
    catalog_dir: Path = Path(__file__).resolve().parent / "assets" / "catalog"

    # ── AI provider settings (Phase 9) ────────────────────────────────────────
    # Generation mode: "deterministic" (no key needed) | "ai" | "hybrid"
    generation_mode: str = "deterministic"
    # Which provider to prefer when both keys are present: "anthropic" | "openai"
    ai_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    model_config = SettingsConfigDict(env_prefix="SCOTCH_", env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept a plain comma-separated string in addition to JSON list syntax."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                import json

                return json.loads(stripped)
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
