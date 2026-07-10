"""Phase 23.3 — Render style presets.

Five architectural render styles, each carrying prompt guidance and a UI swatch colour.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderStyle:
    id: str
    name: str
    description: str
    prompt_suffix: str
    negative_prompt: str
    swatch_color: str  # hex — used for the style-picker card in the UI


RENDER_STYLES: list[RenderStyle] = [
    RenderStyle(
        id="photorealistic_exterior",
        name="Photorealistic",
        description="Sunny-day photo-real exterior",
        prompt_suffix=(
            "photorealistic exterior view, natural daylight, "
            "professional architectural photography, high resolution, 8k"
        ),
        negative_prompt="cartoon, sketch, blur, low quality, dark, interior",
        swatch_color="#e8d5b0",
    ),
    RenderStyle(
        id="architectural_sketch",
        name="Sketch",
        description="Hand-drawn architectural sketch",
        prompt_suffix=(
            "architectural pencil sketch, fine lines, professional illustration, "
            "white paper background, ink hatching"
        ),
        negative_prompt="photorealistic, color photo, dark, blurry",
        swatch_color="#f5f0e8",
    ),
    RenderStyle(
        id="warm_interior",
        name="Warm Interior",
        description="Golden-hour interior scene",
        prompt_suffix=(
            "warm interior architectural render, golden hour light, "
            "cozy ambiance, high-end interior design, soft shadows"
        ),
        negative_prompt="exterior, dark nighttime, cartoon, low quality",
        swatch_color="#f0c87a",
    ),
    RenderStyle(
        id="night_render",
        name="Night",
        description="Dramatic night exterior with lit windows",
        prompt_suffix=(
            "night architectural render, dramatic lighting, illuminated windows, "
            "cinematic mood, professional visualization"
        ),
        negative_prompt="daytime, bright sun, sketch, low quality, blurry",
        swatch_color="#1a2540",
    ),
    RenderStyle(
        id="pencil_line",
        name="Line Drawing",
        description="Clean technical line art",
        prompt_suffix=(
            "architectural line drawing, technical illustration, clean precise lines, "
            "minimal color, blueprint style, white background"
        ),
        negative_prompt="photorealistic, noisy, dark, blurry, color photo",
        swatch_color="#dce8f0",
    ),
]

_BY_ID: dict[str, RenderStyle] = {s.id: s for s in RENDER_STYLES}


def get_style(style_id: str) -> RenderStyle:
    """Return named style, or the first preset as fallback."""
    return _BY_ID.get(style_id, RENDER_STYLES[0])


def list_styles() -> list[RenderStyle]:
    return RENDER_STYLES
