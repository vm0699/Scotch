"""Phase 43 — Interior generation + editing API.

POST /projects/{id}/rooms/{room_id}/interior/generate  — furnish one room
GET  /projects/{id}/rooms/{room_id}/interior            — current interior + status
POST /projects/{id}/rooms/{room_id}/interior/edit        — move/rotate/delete/swap/add one item
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.architecture.interior_designer import generate_room_interior
from app.core.catalog import CatalogNotFoundError, get_catalog_item
from app.core.models.project import ArchitectureProject, FurnitureItem, Material, Room, RoomInterior
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store
from app.core.validation import validate_room_furniture

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

router = APIRouter(prefix="/projects", tags=["interior"])


# ── Request / response models ─────────────────────────────────────────────────


class InteriorGenerateRequest(BaseModel):
    mode: str = Field(default="deterministic", description='"deterministic" | "ai" | "hybrid"')
    style: str = ""
    prompt: str = ""


class InteriorGenerateAllRequest(BaseModel):
    mode: str = Field(default="deterministic", description='"deterministic" | "ai" | "hybrid"')
    style: str = ""
    overwrite: bool = Field(
        default=False, description="Regenerate rooms that already have furniture, not just empty ones."
    )


class RoomInteriorResult(BaseModel):
    room_id: str
    room_name: str
    status: str  # "designed" | "skipped" | "empty_template"
    item_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class InteriorGenerateAllResponse(BaseModel):
    results: list[RoomInteriorResult]
    project: ArchitectureProject


class InteriorEditRequest(BaseModel):
    action: Literal["move", "rotate", "delete", "swap", "add", "recolor"]
    item_id: str | None = None  # required for move/rotate/delete/swap/recolor
    x: float | None = None  # move, add
    y: float | None = None  # move, add
    rotation: Literal[0, 90, 180, 270] | None = None  # rotate, add
    catalog_id: str | None = None  # swap, add
    color: str | None = None  # recolor — hex, e.g. "#3b82f6"
    slot: str = "primary"  # recolor — which material_slot to tint


class InteriorResponse(BaseModel):
    room_id: str
    furniture: list[FurnitureItem]
    warnings: list[str]
    room_interior: RoomInterior
    project: ArchitectureProject


# ── Shared helpers ────────────────────────────────────────────────────────────


def _load(project_id: str, store: ProjectStore) -> ArchitectureProject:
    try:
        stored = store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(status_code=422, detail="Project has no design — generate a floor plan first.")
    return stored.project


def _room_or_404(project: ArchitectureProject, room_id: str) -> Room:
    room = next((r for r in project.rooms if r.id == room_id), None)
    if room is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")
    return room


def _footprint_at_rotation(catalog_id: str, rotation: int) -> tuple[float, float, float]:
    item = get_catalog_item(catalog_id)
    w, d = (item.footprint_d, item.footprint_w) if rotation in (90, 270) else (item.footprint_w, item.footprint_d)
    return w, d, item.height


def _persist(
    store: ProjectStore,
    project_id: str,
    project: ArchitectureProject,
    room_id: str,
    room_items: list[FurnitureItem],
    *,
    status: str,
    style: str = "",
    mode: str = "",
    warnings: list[str] | None = None,
    materials: list[Material] | None = None,
) -> InteriorResponse:
    other_furniture = [f for f in project.furniture if f.room_id != room_id]
    room_interior = RoomInterior(
        room_id=room_id,
        status=status,
        style=style,
        mode=mode,
        last_generated_at=datetime.now(timezone.utc).isoformat(),
        warnings=warnings or [],
    )
    other_interiors = [ri for ri in project.room_interiors if ri.room_id != room_id]

    update: dict = {
        "furniture": other_furniture + room_items,
        "show_furniture": True,
        "room_interiors": other_interiors + [room_interior],
    }
    if materials is not None:
        update["materials"] = materials

    updated = project.model_copy(update=update)
    store.update_project(project_id, project=updated, change_type="edit")
    return InteriorResponse(
        room_id=room_id, furniture=room_items, warnings=warnings or [], room_interior=room_interior, project=updated
    )


def _get_or_create_tint_material(project: ArchitectureProject, color: str) -> tuple[Material, list[Material]]:
    """Recolor = a Material entry (reusing project.materials, the same model
    walls/floors already use) with base_color set to the requested tint,
    referenced from FurnitureItem.material_overrides[slot]. Deterministic id
    from the color itself, so re-picking the same color reuses one entry
    instead of accumulating duplicates."""
    material_id = f"furniture-tint-{color.lstrip('#').lower()}"
    existing = next((m for m in project.materials if m.id == material_id), None)
    if existing:
        return existing, project.materials
    material = Material(id=material_id, name=f"Tint {color}", target="furniture", base_color=color)
    return material, [*project.materials, material]


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/{project_id}/rooms/{room_id}/interior/generate", response_model=InteriorResponse)
def generate_interior(
    project_id: str,
    room_id: str,
    req: InteriorGenerateRequest = InteriorGenerateRequest(),
    store: ProjectStore = Depends(get_project_store),
) -> InteriorResponse:
    project = _load(project_id, store)
    _room_or_404(project, room_id)

    try:
        items, warnings = generate_room_interior(
            project, room_id, mode=req.mode, style=req.style, prompt=req.prompt
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _persist(store, project_id, project, room_id, items, status="designed", style=req.style, mode=req.mode, warnings=warnings)


@router.post("/{project_id}/interior/generate-all", response_model=InteriorGenerateAllResponse)
def generate_all_interiors(
    project_id: str,
    req: InteriorGenerateAllRequest = InteriorGenerateAllRequest(),
    store: ProjectStore = Depends(get_project_store),
) -> InteriorGenerateAllResponse:
    """Furnish every room in one action (Stage 43.20) — the same generator as
    the single-room endpoint, run room by room. Rooms with no matching
    catalog template (e.g. a corridor) come back with zero items and are
    reported as "empty_template", not an error — same graceful behavior as
    generating them one at a time. Skips rooms that already have furniture
    unless overwrite=True, so this is safe to call on a partially-furnished
    project without clobbering manual work."""
    project = _load(project_id, store)
    results: list[RoomInteriorResult] = []

    for room in project.rooms:
        existing_items = [f for f in project.furniture if f.room_id == room.id]
        if existing_items and not req.overwrite:
            results.append(
                RoomInteriorResult(
                    room_id=room.id, room_name=room.name, status="skipped", item_count=len(existing_items)
                )
            )
            continue

        try:
            items, warnings = generate_room_interior(project, room.id, mode=req.mode, style=req.style)
        except ValueError as exc:
            results.append(RoomInteriorResult(room_id=room.id, room_name=room.name, status="skipped", warnings=[str(exc)]))
            continue

        if not items:
            results.append(RoomInteriorResult(room_id=room.id, room_name=room.name, status="empty_template"))
            continue

        # Reassign `project` after each persist — _persist computes "other
        # rooms' furniture" from whatever `project` it's given, so the next
        # iteration must see this room's just-saved items or it would wipe
        # them back out when it persists the next room.
        response = _persist(
            store, project_id, project, room.id, items, status="designed", style=req.style, mode=req.mode,
            warnings=warnings,
        )
        project = response.project
        results.append(
            RoomInteriorResult(room_id=room.id, room_name=room.name, status="designed", item_count=len(items), warnings=warnings)
        )

    return InteriorGenerateAllResponse(results=results, project=project)


@router.get("/{project_id}/rooms/{room_id}/interior", response_model=InteriorResponse)
def get_interior(
    project_id: str,
    room_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> InteriorResponse:
    project = _load(project_id, store)
    _room_or_404(project, room_id)

    items = [f for f in project.furniture if f.room_id == room_id]
    room_interior = next(
        (ri for ri in project.room_interiors if ri.room_id == room_id),
        RoomInterior(room_id=room_id, status="designed" if items else "empty"),
    )
    return InteriorResponse(
        room_id=room_id, furniture=items, warnings=room_interior.warnings, room_interior=room_interior, project=project
    )


@router.post("/{project_id}/rooms/{room_id}/interior/edit", response_model=InteriorResponse)
def edit_interior(
    project_id: str,
    room_id: str,
    req: InteriorEditRequest,
    store: ProjectStore = Depends(get_project_store),
) -> InteriorResponse:
    """Move/rotate/delete/swap/add one item. Every edit is re-validated
    (bounds, overlap, door-swing) before it's persisted — an edit that would
    break the room is rejected with 422, not silently saved."""
    project = _load(project_id, store)
    room = _room_or_404(project, room_id)

    items = [f for f in project.furniture if f.room_id == room_id]
    by_id = {f.id: f for f in items}
    # A room can already carry a pre-existing violation (e.g. furnished via the
    # whole-project /generate/from-prompt flow, which — unlike this room's own
    # deterministic generator — isn't door-aware). An edit shouldn't become
    # impossible just because something ELSE in the room was already wrong;
    # only reject when THIS edit introduces a violation that wasn't already there.
    errors_before = set(validate_room_furniture(room, items, project).errors)

    if req.action in ("move", "rotate", "delete", "swap", "recolor") and (not req.item_id or req.item_id not in by_id):
        raise HTTPException(status_code=404, detail=f"Furniture item '{req.item_id}' not found in room '{room_id}'")

    updated_materials = project.materials

    if req.action == "delete":
        items = [f for f in items if f.id != req.item_id]

    elif req.action == "move":
        if req.x is None or req.y is None:
            raise HTTPException(status_code=422, detail="move requires x and y")
        items = [f.model_copy(update={"x": req.x, "y": req.y}) if f.id == req.item_id else f for f in items]

    elif req.action == "rotate":
        if req.rotation is None:
            raise HTTPException(status_code=422, detail="rotate requires rotation")
        target = by_id[req.item_id]
        swap_dims = (req.rotation % 180) != (target.rotation % 180)
        w, d = (target.depth, target.width) if swap_dims else (target.width, target.depth)
        items = [
            f.model_copy(update={"rotation": req.rotation, "width": w, "depth": d}) if f.id == req.item_id else f
            for f in items
        ]

    elif req.action == "swap":
        if not req.catalog_id:
            raise HTTPException(status_code=422, detail="swap requires catalog_id")
        target = by_id[req.item_id]
        try:
            w, d, h = _footprint_at_rotation(req.catalog_id, target.rotation)
            new_label = get_catalog_item(req.catalog_id).label
        except CatalogNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        items = [
            f.model_copy(update={"catalog_id": req.catalog_id, "label": new_label, "width": w, "depth": d, "height": h})
            if f.id == req.item_id
            else f
            for f in items
        ]

    elif req.action == "recolor":
        if not req.color or not _HEX_COLOR_RE.match(req.color):
            raise HTTPException(status_code=422, detail="recolor requires a 6-digit hex color, e.g. #3b82f6")
        target = by_id[req.item_id]
        catalog_entry = get_catalog_item(target.catalog_id) if target.catalog_id else None
        slot_def = next((s for s in (catalog_entry.material_slots if catalog_entry else []) if s.slot == req.slot), None)
        if catalog_entry and slot_def is not None and not slot_def.editable:
            raise HTTPException(status_code=422, detail=f"Material slot '{req.slot}' on this item is not editable")
        new_material, updated_materials = _get_or_create_tint_material(project, req.color)
        items = [
            f.model_copy(update={"material_overrides": {**f.material_overrides, req.slot: new_material.id}})
            if f.id == req.item_id
            else f
            for f in items
        ]

    else:  # add
        if not req.catalog_id or req.x is None or req.y is None:
            raise HTTPException(status_code=422, detail="add requires catalog_id, x, y")
        rotation = req.rotation or 0
        try:
            w, d, h = _footprint_at_rotation(req.catalog_id, rotation)
            catalog_item = get_catalog_item(req.catalog_id)
        except CatalogNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        items.append(
            FurnitureItem(
                id=str(uuid.uuid4()),
                type=catalog_item.category,
                label=catalog_item.label,
                room_id=room_id,
                x=req.x,
                y=req.y,
                width=w,
                depth=d,
                rotation=rotation,  # type: ignore[arg-type]
                height=h,
                catalog_id=req.catalog_id,
            )
        )

    result = validate_room_furniture(room, items, project)
    new_errors = [e for e in result.errors if e not in errors_before]
    if new_errors:
        raise HTTPException(status_code=422, detail={"message": "Edit rejected", "errors": new_errors})

    existing_interior = next((ri for ri in project.room_interiors if ri.room_id == room_id), None)
    return _persist(
        store,
        project_id,
        project,
        room_id,
        items,
        status="designed",
        style=existing_interior.style if existing_interior else "",
        mode=existing_interior.mode if existing_interior else "deterministic",
        warnings=[w.message for w in result.warnings],
        materials=updated_materials,
    )
