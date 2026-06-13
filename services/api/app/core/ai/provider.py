"""AI provider abstraction — deterministic, Anthropic, OpenAI-compatible, hybrid."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.core.models import ArchitectureProject, ProjectWarning


class AIProvider(ABC):
    """Common interface for all generation backends."""

    @abstractmethod
    def generate_project(self, prompt: str) -> tuple[ArchitectureProject, str]:
        """Return (project, human-readable summary)."""


class DeterministicProvider(AIProvider):
    """Phase 5 rule-based generator — no AI key required."""

    def generate_project(self, prompt: str) -> tuple[ArchitectureProject, str]:
        from app.core.architecture.floorplan_generator import generate_floorplan
        from app.core.architecture.requirement_parser import parse_prompt

        return generate_floorplan(parse_prompt(prompt))


class AnthropicProvider(AIProvider):
    """Claude via the Anthropic SDK (lazy-imported so the API starts without it)."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._api_key = api_key
        self._model = model

    def generate_project(self, prompt: str) -> tuple[ArchitectureProject, str]:
        try:
            import anthropic  # noqa: PLC0415
        except ImportError as exc:
            raise ValueError("anthropic package not installed. Run: pip install anthropic") from exc

        from app.core.ai.prompt_templates import build_messages
        from app.core.ai.schema_repair import repair_and_parse

        client = anthropic.Anthropic(api_key=self._api_key)
        msgs = build_messages(prompt)
        response = client.messages.create(
            model=self._model,
            max_tokens=8192,
            system=msgs["system"],
            messages=[{"role": "user", "content": msgs["user"]}],
        )
        raw = response.content[0].text
        project = repair_and_parse(raw)
        return project, f"AI-generated design ({self._model})."


class OpenAICompatibleProvider(AIProvider):
    """OpenAI-compatible endpoint — openai SDK, lazy-imported."""

    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def generate_project(self, prompt: str) -> tuple[ArchitectureProject, str]:
        try:
            import openai  # noqa: PLC0415
        except ImportError as exc:
            raise ValueError("openai package not installed. Run: pip install openai") from exc

        from app.core.ai.prompt_templates import build_messages
        from app.core.ai.schema_repair import repair_and_parse

        client = openai.OpenAI(api_key=self._api_key, base_url=self._base_url)
        msgs = build_messages(prompt)
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": msgs["system"]},
                {"role": "user", "content": msgs["user"]},
            ],
            max_tokens=8192,
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        project = repair_and_parse(raw)
        return project, f"AI-generated design ({self._model})."


class HybridProvider(AIProvider):
    """Try AI provider; on any failure fall back silently to deterministic."""

    def __init__(self, ai: AIProvider) -> None:
        self._ai = ai
        self._det = DeterministicProvider()

    def generate_project(self, prompt: str) -> tuple[ArchitectureProject, str]:
        try:
            return self._ai.generate_project(prompt)
        except Exception:  # noqa: BLE001
            project, summary = self._det.generate_project(prompt)
            project.warnings.append(
                ProjectWarning(
                    id=f"ai-fallback-{uuid.uuid4().hex[:8]}",
                    message="AI output was invalid — deterministic layout used as fallback.",
                    severity="info",
                )
            )
            return project, f"{summary} (AI fallback used.)"
