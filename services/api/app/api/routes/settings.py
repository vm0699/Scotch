"""GET /settings/generation — provider status (never echoes keys)."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class GenerationSettings(BaseModel):
    mode: str
    provider: str
    anthropic_configured: bool
    openai_configured: bool


@router.get("/generation", response_model=GenerationSettings)
def get_generation_settings() -> GenerationSettings:
    s = get_settings()
    return GenerationSettings(
        mode=s.generation_mode,
        provider=s.ai_provider,
        anthropic_configured=bool(s.anthropic_api_key),
        openai_configured=bool(s.openai_api_key),
    )
