"""Phase 35 — Context-aware render prompt generator.

Derives a photorealistic render prompt from:
  - Project style, orientation, and site context
  - Room type and camera view angle (exterior / interior / top-down)
  - Material plan — floor finish, wall finish, ceiling (if generated)
  - Client brief — budget level, style preference, location/climate note
  - Camera suggestion — name gives view type (exterior, living, bedroom, etc.)
  - Mood/atmosphere target derived from brief and budget

Output is a single well-engineered prompt string suitable for:
  - Midjourney / Stable Diffusion / ComfyUI via text-to-image
  - Blender render preset description (pass as --render-comment)
  - DALL-E 3 or similar API prompt

No external API calls — purely deterministic Python.
"""
from __future__ import annotations

import re

from app.core.models import ArchitectureProject


# ── Style mappings ────────────────────────────────────────────────────────────

_BUDGET_QUALITY: dict[str, str] = {
    "economy":  "clean, functional, warm, cost-conscious interiors",
    "standard": "contemporary, well-appointed, balanced proportions",
    "premium":  "luxury, bespoke finishes, high-end materials, editorial quality",
}

_BUILDING_STYLE: dict[str, str] = {
    "contemporary":   "clean lines, flat roof, large glazing, minimal ornamentation",
    "modern":         "open plan, geometric, floor-to-ceiling windows",
    "traditional":    "sloped roof, brick or plaster facade, classic proportions",
    "colonial":       "symmetrical facade, verandah, pitched roof, heritage palette",
    "mediterranean":  "terracotta roof tiles, arched openings, warm stucco walls",
    "industrial":     "exposed concrete, steel frames, raw materials, high ceilings",
    "minimal":        "monochromatic palette, flush surfaces, hidden hardware",
}

_ORIENTATION_NOTE: dict[str, str] = {
    "north": "north-facing entrance, subdued natural light, softer shadows",
    "south": "south-facing entrance, sun-drenched interiors, warm afternoon light",
    "east":  "east-facing entrance, bright morning light, golden hour shadows",
    "west":  "west-facing entrance, dramatic sunset light, long evening shadows",
}

_MATERIAL_ADJECTIVE: dict[str, str] = {
    "marble":     "polished marble flooring, veining, reflective surface",
    "vitrified":  "vitrified tile floor, glossy, neutral tone",
    "ceramic":    "ceramic tile floor, matte finish, consistent texture",
    "granite":    "granite floor, speckled, durable stone",
    "timber":     "warm timber flooring, wood grain texture",
    "concrete":   "polished concrete floor, cool industrial aesthetic",
    "terrazzo":   "terrazzo floor, terrazzo chips in cement matrix",
    "hardwood":   "hardwood floor, rich warm tones",
    "stone":      "natural stone floor, textured surface",
}

# ── View / camera types ────────────────────────────────────────────────────────

def _classify_view(camera_name: str | None) -> str:
    if not camera_name:
        return "exterior"
    n = camera_name.lower()
    if any(kw in n for kw in ("top", "bird", "aerial", "plan")):
        return "top"
    if any(kw in n for kw in ("exterior", "front", "facade", "street")):
        return "exterior"
    if any(kw in n for kw in ("living", "lounge", "salon")):
        return "living"
    if any(kw in n for kw in ("master", "bedroom", "bed")):
        return "bedroom"
    if any(kw in n for kw in ("kitchen", "cook", "pantry")):
        return "kitchen"
    if any(kw in n for kw in ("toilet", "bath", "wc", "shower")):
        return "toilet"
    return "exterior"


_VIEW_PROMPT_PREFIX: dict[str, str] = {
    "exterior": "photorealistic architectural exterior rendering",
    "top":      "architectural aerial view rendering, orthographic",
    "living":   "photorealistic interior rendering of living room",
    "bedroom":  "photorealistic interior rendering of bedroom",
    "kitchen":  "photorealistic interior rendering of kitchen",
    "toilet":   "photorealistic interior rendering of bathroom",
}

_VIEW_LIGHTING: dict[str, str] = {
    "exterior": "natural daylight, blue sky, soft shadows, HDRI environment",
    "top":      "ambient light, no harsh shadows, clear plan view",
    "living":   "warm interior lighting, table lamps, natural light from windows",
    "bedroom":  "soft indirect lighting, warm bedside lamps, morning diffuse light",
    "kitchen":  "bright task lighting, under-cabinet LEDs, natural window light",
    "toilet":   "bathroom lighting, LED strips, clean bright ambient",
}

_VIEW_ATMOSPHERE: dict[str, str] = {
    "exterior": "dramatic architecture photography, dusk or golden hour",
    "top":      "technical illustration, clean diagrammatic aerial",
    "living":   "cosy yet contemporary, editorial interior photography",
    "bedroom":  "serene, restful, hotel suite quality",
    "kitchen":  "clean and functional, culinary editorial, magazine quality",
    "toilet":   "spa-like, pristine, minimalist bathroom editorial",
}


# ── Material extraction ────────────────────────────────────────────────────────

def _get_floor_material_note(project: ArchitectureProject, view: str) -> str:
    if not project.material_plan.generated:
        return ""
    finishes = project.material_plan.room_finishes
    if not finishes:
        return ""

    # Find most relevant room for the view type
    target_types: dict[str, list[str]] = {
        "living":  ["living", "lounge", "dining"],
        "bedroom": ["master_bedroom", "bedroom"],
        "kitchen": ["kitchen", "kitchenette"],
        "toilet":  ["bathroom", "master_bathroom", "toilet"],
    }
    candidate_types = target_types.get(view, [])
    rooms_by_type = {r.id: r for r in project.rooms if r.type in candidate_types}

    # Pick first matching finish
    for finish in finishes:
        if finish.room_id in rooms_by_type:
            mat = finish.floor_material.lower()
            for key, adj in _MATERIAL_ADJECTIVE.items():
                if key in mat:
                    return adj
    # Fallback: use first finish
    if finishes:
        mat = finishes[0].floor_material.lower()
        for key, adj in _MATERIAL_ADJECTIVE.items():
            if key in mat:
                return adj
    return ""


# ── Main entry ────────────────────────────────────────────────────────────────

def generate_render_prompt(
    project: ArchitectureProject,
    camera_name: str | None = None,
    *,
    extra_tags: list[str] | None = None,
) -> str:
    """Return a photorealistic render prompt string for *project*.

    Args:
        project:     The ArchitectureProject to describe.
        camera_name: Name of the camera preset (e.g. "exterior_front", "living_room").
                     Determines view type and lighting treatment.
        extra_tags:  Additional prompt tags to append (e.g. ["no people", "--ar 16:9"]).

    Returns:
        A single prompt string.
    """
    view = _classify_view(camera_name)

    # ── Base prefix (view type) ────────────────────────────────────────────────
    prefix = _VIEW_PROMPT_PREFIX.get(view, "photorealistic architectural rendering")

    # ── Building style ────────────────────────────────────────────────────────
    style_raw = (project.building.style or "").lower()
    style_desc = ""
    for key, desc in _BUILDING_STYLE.items():
        if key in style_raw:
            style_desc = desc
            break
    if not style_desc and style_raw:
        style_desc = f"{style_raw} architectural style"

    # ── Client brief ──────────────────────────────────────────────────────────
    brief = project.client_brief
    budget_quality = _BUDGET_QUALITY.get(getattr(brief, "budget_level", "standard"), _BUDGET_QUALITY["standard"])
    style_pref = getattr(brief, "style_preference", "") or ""

    # ── Orientation / light ───────────────────────────────────────────────────
    orientation = (project.site.orientation or "east").lower()
    orientation_note = _ORIENTATION_NOTE.get(orientation, "")
    lighting = _VIEW_LIGHTING.get(view, "natural daylight")

    # ── Materials ─────────────────────────────────────────────────────────────
    floor_mat = _get_floor_material_note(project, view)

    # ── Atmosphere ───────────────────────────────────────────────────────────
    atmosphere = _VIEW_ATMOSPHERE.get(view, "editorial quality, professional photography")

    # ── Site context (India urban) ─────────────────────────────────────────────
    location_note = "India, tropical climate, lush green surroundings"

    # ── Assemble ──────────────────────────────────────────────────────────────
    parts: list[str] = [prefix]
    if style_desc:
        parts.append(style_desc)
    if style_pref:
        parts.append(f"{style_pref} design language")
    if budget_quality:
        parts.append(budget_quality)
    if floor_mat:
        parts.append(floor_mat)
    parts.append(lighting)
    if orientation_note and view in ("exterior", "top"):
        parts.append(orientation_note)
    parts.append(atmosphere)
    parts.append(location_note)
    parts.append("8K, ultra-detailed, architectural photography, 35mm lens, shot on Phase One")

    if extra_tags:
        parts.extend(extra_tags)

    return ", ".join(parts)


def generate_all_render_prompts(project: ArchitectureProject) -> list[dict]:
    """Generate one render prompt per standard camera view. Returns list of {name, view, prompt}."""
    cameras = [
        ("exterior_front",  "Exterior — front facade"),
        ("exterior_aerial", "Aerial / bird's-eye view"),
        ("living_room",     "Living room interior"),
        ("master_bedroom",  "Master bedroom interior"),
        ("kitchen_view",    "Kitchen interior"),
        ("bathroom_view",   "Bathroom / toilet interior"),
    ]
    return [
        {
            "name": name,
            "label": label,
            "view": _classify_view(name),
            "prompt": generate_render_prompt(project, camera_name=name),
        }
        for name, label in cameras
    ]
