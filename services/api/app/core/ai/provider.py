"""AI provider abstraction — deterministic, Anthropic, OpenAI-compatible, hybrid.

Also contains RenderProvider ABC for Phase 23 in-app rendering.
"""

from __future__ import annotations

import base64
import uuid
from abc import ABC, abstractmethod

from app.core.models import ArchitectureProject, ProjectWarning

# ── Render providers (Phase 23) ───────────────────────────────────────────────

# Minimal 8×8 gray PNG (deterministic placeholder when no conditioning image).
_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAD"
    "ElEQVQI12NgGAQAAAgABFlCdOQAAAAASUVORK5CYII="
)


class RenderProvider(ABC):
    """Interface for all image-render backends."""

    @abstractmethod
    def render_image(
        self,
        project: ArchitectureProject,
        camera_id: str,
        style: str,
        conditioning_b64: str | None,
        *,
        prompt_override: str | None = None,
    ) -> bytes:
        """Return PNG bytes for the rendered image."""


class DeterministicRenderProvider(RenderProvider):
    """No-key fallback: returns the massing capture as-is (always succeeds)."""

    def render_image(
        self,
        project: ArchitectureProject,
        camera_id: str,
        style: str,
        conditioning_b64: str | None,
        *,
        prompt_override: str | None = None,
    ) -> bytes:
        if conditioning_b64:
            data = (
                conditioning_b64.split(",", 1)[1]
                if "," in conditioning_b64
                else conditioning_b64
            )
            return base64.b64decode(data)
        return _PLACEHOLDER_PNG


class StableDiffusionRenderProvider(RenderProvider):
    """img2img via a Stable Diffusion web-UI compatible API endpoint."""

    def __init__(self, api_url: str, api_key: str = "") -> None:
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key

    def render_image(
        self,
        project: ArchitectureProject,
        camera_id: str,
        style: str,
        conditioning_b64: str | None,
        *,
        prompt_override: str | None = None,
    ) -> bytes:
        import json as _json
        import urllib.request

        from app.core.render.styles import get_style

        style_def = get_style(style)
        base_prompt = prompt_override or f"architectural render, {style_def.prompt_suffix}"
        payload = {
            "init_images": [conditioning_b64 or ""],
            "prompt": base_prompt,
            "negative_prompt": style_def.negative_prompt,
            "denoising_strength": 0.65 if prompt_override else 0.65,
            "steps": 20,
            "cfg_scale": 7,
            "width": 512,
            "height": 512,
        }
        req = urllib.request.Request(
            f"{self._api_url}/sdapi/v1/img2img",
            data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if self._api_key:
            req.add_header("Authorization", f"Bearer {self._api_key}")
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            result = _json.loads(resp.read())
        return base64.b64decode(result["images"][0])


def get_render_provider() -> RenderProvider:
    """Return the configured render provider, defaulting to deterministic."""
    import os

    sd_url = os.environ.get("SCOTCH_SD_URL", "").strip()
    sd_key = os.environ.get("SCOTCH_SD_KEY", "").strip()
    if sd_url:
        return StableDiffusionRenderProvider(api_url=sd_url, api_key=sd_key)
    return DeterministicRenderProvider()


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
