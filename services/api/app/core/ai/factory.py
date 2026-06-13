"""Instantiate the right AIProvider for a given generation mode and settings."""

from __future__ import annotations

from app.core.ai.provider import (
    AIProvider,
    AnthropicProvider,
    DeterministicProvider,
    HybridProvider,
    OpenAICompatibleProvider,
)


def get_provider(mode: str, settings: object) -> AIProvider:
    """Return an AIProvider for the given mode.

    mode: "deterministic" | "ai" | "hybrid" (unknown values → deterministic)
    settings: Settings instance from app.config with AI key fields.
    """
    if mode == "deterministic":
        return DeterministicProvider()

    try:
        ai = _ai_provider_from_settings(settings)
    except ValueError:
        if mode == "ai":
            raise
        # hybrid with no key → plain deterministic (graceful degradation)
        return DeterministicProvider()

    if mode == "ai":
        return ai
    if mode == "hybrid":
        return HybridProvider(ai)

    return DeterministicProvider()


def _ai_provider_from_settings(settings: object) -> AIProvider:
    if getattr(settings, "anthropic_api_key", ""):
        return AnthropicProvider(
            settings.anthropic_api_key,  # type: ignore[attr-defined]
            settings.anthropic_model,  # type: ignore[attr-defined]
        )
    if getattr(settings, "openai_api_key", ""):
        return OpenAICompatibleProvider(
            settings.openai_api_key,  # type: ignore[attr-defined]
            settings.openai_base_url,  # type: ignore[attr-defined]
            settings.openai_model,  # type: ignore[attr-defined]
        )
    raise ValueError(
        "AI mode requires an API key. Set SCOTCH_ANTHROPIC_API_KEY or "
        "SCOTCH_OPENAI_API_KEY in .env then restart the backend."
    )
