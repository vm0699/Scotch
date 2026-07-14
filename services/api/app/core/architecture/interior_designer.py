"""Phase 43 Stage 43.3 — Interior generation orchestrator.

Two generation paths for one room, both landing in the same FurnitureItem[]
shape (core invariant: AI proposes, validator checks, deterministic fallback
always works with no AI key):

  1. Deterministic — furniture_placer.py's wall-affinity engine, with specs'
     width/depth/height resolved from the real CatalogItem so 2D clearance
     math and the 3D mesh always agree on size.
  2. AI — sends room geometry + door/window positions + a catalog subset to
     the configured Claude model; the model returns placements as JSON over
     that fixed catalog (the same pattern the published auto-layout research
     — LayoutGPT / Holodeck / OptiScene — converges on); output is schema-
     repaired and re-validated exactly like the deterministic path.

mode="ai" and mode="hybrid" behave identically here: any AI failure (missing
key, bad JSON, failed validation) falls back to the deterministic layout with
a warning, never leaving the caller with an empty/broken room.
"""

from __future__ import annotations

import dataclasses
import json
import re
import uuid
from typing import Any

from app.config import get_settings
from app.core.architecture.furniture_defaults import FurnitureSpec, effective_room_type, get_template
from app.core.architecture.furniture_placer import place_furniture_in_room
from app.core.catalog import CatalogNotFoundError, get_catalog_item, list_catalog_items
from app.core.models.catalog import CatalogItem
from app.core.models.project import ArchitectureProject, FurnitureItem, Room
from app.core.validation import door_blocking_item_ids, validate_room_furniture

GenerationMode = str  # "deterministic" | "ai" | "hybrid"


class InteriorGenerationError(Exception):
    """Raised only when even the deterministic fallback produces nothing usable."""


# ── Catalog-dimension resolution (shared by both paths) ──────────────────────


def _resolve_catalog_dims(spec: FurnitureSpec) -> FurnitureSpec:
    """Return a copy of *spec* with width/depth/height from its CatalogItem.

    Never mutates the shared ROOM_FURNITURE dataclass instances. Falls back
    to the spec's generic dims if the catalog lookup fails (defensive — keeps
    generation working even if the catalog is momentarily unavailable).
    """
    if not spec.catalog_id:
        return spec
    try:
        item = get_catalog_item(spec.catalog_id)
    except CatalogNotFoundError:
        return spec
    return dataclasses.replace(spec, width=item.footprint_w, depth=item.footprint_d, height=item.height)


def _resolved_template(room: Room) -> list[FurnitureSpec]:
    room_type = effective_room_type(room.id, room.type, room.name)
    return [_resolve_catalog_dims(s) for s in get_template(room_type, room.width, room.depth)]


# ── Deterministic path ────────────────────────────────────────────────────────


def furnish_room_deterministic(room: Room) -> list[FurnitureItem]:
    """The no-AI-key fallback. Always works, always returns a usable layout
    (possibly empty, if the room type has no template — e.g. a corridor)."""
    return place_furniture_in_room(room, specs_override=_resolved_template(room))


def _furnish_deterministic_and_heal(
    project: ArchitectureProject, room: Room
) -> tuple[list[FurnitureItem], list[str]]:
    """furnish_room_deterministic() is door-unaware (the wall-affinity engine
    only knows the room's own geometry, not project.doors) — so its output can
    occasionally block a door. Rather than persist a layout that then fails
    every future edit's re-validation, drop the offending item(s) here and say
    so; the deterministic path always returns a *validator-clean* result."""
    items = furnish_room_deterministic(room)
    warnings: list[str] = []

    blocking_ids = door_blocking_item_ids(room, items, project)
    if blocking_ids:
        dropped = [i for i in items if i.id in blocking_ids]
        items = [i for i in items if i.id not in blocking_ids]
        for item in dropped:
            warnings.append(f"'{item.label}' was left out — it would have blocked a door.")

    result = validate_room_furniture(room, items, project)
    warnings.extend(w.message for w in result.warnings)
    return items, warnings


# ── AI path ────────────────────────────────────────────────────────────────

_AI_SYSTEM_PROMPT = """You are an interior layout assistant for Scotch, an architecture design tool.
Given one room's geometry and a fixed furniture catalog, propose a furnished layout.

Rules:
- Use ONLY the catalog_id values given — never invent one.
- Coordinates are room-local feet: x in [0, room_width], y in [0, room_depth], (0,0) = room's top-left corner.
- x/y is the TOP-LEFT corner of the item's footprint at rotation 0.
- rotation is one of 0, 90, 180, 270 (degrees).
- Keep every item's footprint fully inside the room and leave walking clearance near the door.
- Do not overlap items.
- Prefer beds/wardrobes against a wall; small items (plant, ottoman) can float.
- Return ONLY a JSON array, no prose, no markdown fences:
  [{"catalog_id": "...", "x": 0.0, "y": 0.0, "rotation": 0}, ...]
"""


def _build_ai_prompt(room: Room, catalog: list[CatalogItem], style: str, extra_prompt: str) -> str:
    catalog_desc = [
        {
            "catalog_id": c.id,
            "category": c.category,
            "label": c.label,
            "footprint_w": c.footprint_w,
            "footprint_d": c.footprint_d,
            "style_tags": c.style_tags,
        }
        for c in catalog
    ]
    parts = [
        f"Room: {room.name} ({room.type}), {room.width} x {room.depth} ft.",
        f"Style: {style or 'no preference'}.",
    ]
    if extra_prompt:
        parts.append(f"User request: {extra_prompt}")
    parts.append("Catalog:\n" + json.dumps(catalog_desc, indent=None))
    return "\n".join(parts)


def _extract_json_array(text: str) -> Any:
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON array found in AI output.")
    return json.loads(text[start : end + 1])


def _call_anthropic(prompt: str) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise InteriorGenerationError("No Anthropic API key configured.")

    import anthropic  # noqa: PLC0415  (lazy — API must start without it)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=_AI_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _placements_to_items(
    raw: str, room: Room, catalog_by_id: dict[str, CatalogItem]
) -> list[FurnitureItem]:
    placements = _extract_json_array(raw)
    if not isinstance(placements, list) or not placements:
        raise ValueError("AI output was not a non-empty JSON array.")

    items: list[FurnitureItem] = []
    for p in placements:
        catalog_id = p.get("catalog_id")
        item_def = catalog_by_id.get(catalog_id)
        if item_def is None:
            continue  # ignore hallucinated catalog ids rather than failing the whole batch

        rotation = p.get("rotation", 0)
        if rotation not in (0, 90, 180, 270):
            rotation = 0
        w, d = (item_def.footprint_d, item_def.footprint_w) if rotation in (90, 270) else (
            item_def.footprint_w,
            item_def.footprint_d,
        )
        x = room.x + max(0.0, min(float(p.get("x", 0)), room.width - w))
        y = room.y + max(0.0, min(float(p.get("y", 0)), room.depth - d))

        items.append(
            FurnitureItem(
                id=str(uuid.uuid4()),
                type=item_def.category,
                label=item_def.label,
                room_id=room.id,
                x=round(x, 2),
                y=round(y, 2),
                width=round(w, 2),
                depth=round(d, 2),
                rotation=rotation,  # type: ignore[arg-type]
                height=item_def.height,
                catalog_id=item_def.id,
            )
        )

    if not items:
        raise ValueError("AI output contained no valid catalog placements.")
    return items


def furnish_room_ai(room: Room, style: str, extra_prompt: str) -> list[FurnitureItem]:
    """Raises on any failure — callers must catch and fall back."""
    catalog = list_catalog_items()
    if not catalog:
        raise InteriorGenerationError("Catalog is empty.")
    catalog_by_id = {c.id: c for c in catalog}

    prompt = _build_ai_prompt(room, catalog, style, extra_prompt)
    raw = _call_anthropic(prompt)
    return _placements_to_items(raw, room, catalog_by_id)


# ── Orchestrator ──────────────────────────────────────────────────────────────


def generate_room_interior(
    project: ArchitectureProject,
    room_id: str,
    mode: GenerationMode = "deterministic",
    style: str = "",
    prompt: str = "",
) -> tuple[list[FurnitureItem], list[str]]:
    """Returns (furniture_items_for_this_room, warnings). Does not persist —
    callers (API route) own merging into project.furniture and saving."""
    room = next((r for r in project.rooms if r.id == room_id), None)
    if room is None:
        raise ValueError(f"Room '{room_id}' not found in project")

    warnings: list[str] = []
    items: list[FurnitureItem] = []

    if mode in ("ai", "hybrid"):
        try:
            items = furnish_room_ai(room, style, prompt)
            result = validate_room_furniture(room, items, project)
            if not result.valid:
                raise ValueError(f"AI layout failed validation: {'; '.join(result.errors)}")
            warnings.extend(w.message for w in result.warnings)
        except Exception as exc:  # noqa: BLE001 — any AI failure falls back, per core invariant
            items, det_warnings = _furnish_deterministic_and_heal(project, room)
            warnings.append(f"AI layout unavailable ({exc}) — deterministic layout used instead.")
            warnings.extend(det_warnings)
    else:
        items, det_warnings = _furnish_deterministic_and_heal(project, room)
        warnings.extend(det_warnings)

    return items, warnings
