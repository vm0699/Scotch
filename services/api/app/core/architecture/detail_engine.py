"""DetailEngine — generates DetailDrawing objects from templates + project objects.

All output is advisory/conceptual (confidence scores + needs_review flags).
Geometry primitives are computed server-side from the linked object dimensions
and template parameters. Details go stale when source objects change.

Usage:
    from app.core.architecture.detail_engine import DetailEngine
    drawing = DetailEngine.generate(project, "toilet", source_id="bath-1")
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.models.project import (
    ArchitectureProject,
    ArcPrimitive,
    DetailDrawing,
    DimPrimitive,
    HatchPrimitive,
    LinePrimitive,
    StairEntity,
    TextPrimitive,
)
from app.core.units import UnitConversionService

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "data" / "detail_templates"

_TYPE_TO_FILE: dict[str, str] = {
    "toilet": "toilet_detail.json",
    "kitchen": "kitchen_detail.json",
    "door_window": "door_window_detail.json",
    "wall_section": "wall_section_detail.json",
    "tile_layout": "tile_layout_detail.json",
    "stair": "stair_detail.json",
}


def _load_template(detail_type: str) -> dict[str, Any]:
    fname = _TYPE_TO_FILE.get(detail_type)
    if not fname:
        return {}
    path = _TEMPLATES_DIR / fname
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def _rect_lines(x: float, y: float, w: float, h: float, layer: str = "outline") -> list[LinePrimitive]:
    return [
        LinePrimitive(p1=[x, y], p2=[x + w, y], layer=layer),
        LinePrimitive(p1=[x + w, y], p2=[x + w, y + h], layer=layer),
        LinePrimitive(p1=[x + w, y + h], p2=[x, y + h], layer=layer),
        LinePrimitive(p1=[x, y + h], p2=[x, y], layer=layer),
    ]


def _dim(p1: list[float], p2: list[float], value: float, units: str) -> DimPrimitive:
    label = UnitConversionService.format_dimension(value, units)
    return DimPrimitive(p1=p1, p2=p2, value=value, label=label)


def _label(x: float, y: float, text: str, h: float = 0.3) -> TextPrimitive:
    return TextPrimitive(pos=[x, y], text=text, height=h, layer="annotation")


# ── Toilet Detail ─────────────────────────────────────────────────────────────


def _gen_toilet(project: ArchitectureProject, source_id: str, tmpl: dict) -> DetailDrawing:
    room = next((r for r in project.rooms if r.id == source_id), None)
    if room is None:
        raise ValueError(f"Room '{source_id}' not found")

    W = room.width
    H = room.depth
    units = project.units
    primitives: list = []

    # Room outline
    primitives += _rect_lines(0, 0, W, H, "outline")

    # Fixtures
    for fix in tmpl.get("fixtures", []):
        fx = fix["x_frac"] * W
        fy = fix["y_frac"] * H
        fw = min(fix["width_ft"], W * 0.45)
        fd = min(fix["depth_ft"], H * 0.45)
        primitives += _rect_lines(fx, fy, fw, fd, "fixture")
        primitives.append(_label(fx + fw / 2, fy + fd / 2, fix["label"], 0.25))

    # Dimensions
    primitives.append(_dim([0, -0.5], [W, -0.5], W, units))
    primitives.append(_dim([-0.5, 0], [-0.5, H], H, units))

    return DetailDrawing(
        id=f"det-toilet-{source_id}",
        name=f"WC Detail — {room.name}",
        detail_type="toilet",
        source_object_ids=[source_id],
        primitives=primitives,
        canvas_width=W + 2,
        canvas_height=H + 2,
        scale=tmpl.get("scale", "1:20"),
        view="plan",
        warnings=list(tmpl.get("annotations", [])),
        annotations=list(tmpl.get("annotations", [])),
        confidence=tmpl.get("confidence", 0.82),
        needs_review=tmpl.get("needs_review", True),
    )


# ── Kitchen Detail ────────────────────────────────────────────────────────────


def _gen_kitchen(project: ArchitectureProject, source_id: str, tmpl: dict) -> DetailDrawing:
    room = next((r for r in project.rooms if r.id == source_id), None)
    if room is None:
        raise ValueError(f"Room '{source_id}' not found")

    W = room.width
    H = room.depth
    cd = tmpl.get("counter_depth_ft", 2.0)
    units = project.units
    primitives: list = []

    # Room outline
    primitives += _rect_lines(0, 0, W, H, "outline")

    # Counter along north wall (y=0 side)
    counter_w = W
    primitives += _rect_lines(0, 0, counter_w, cd, "fixture")
    primitives.append(_label(counter_w / 2, cd / 2, "Counter", 0.2))

    # Counter along west wall
    primitives += _rect_lines(0, cd, cd, H - cd, "fixture")
    primitives.append(_label(cd / 2, cd + (H - cd) / 2, "Counter", 0.2))

    # Appliances along north counter
    apps = tmpl.get("appliances", [])
    spacing = W / max(len(apps) + 1, 2)
    sink_pos: list[float] | None = None
    stove_pos: list[float] | None = None
    fridge_pos: list[float] | None = None
    for i, app in enumerate(apps):
        aw = min(app.get("width_ft", 2.0), 2.5)
        ad = min(app.get("depth_ft", 2.0), cd - 0.1)
        ax = spacing * (i + 1) - aw / 2
        ay = 0
        primitives += _rect_lines(ax, ay, aw, ad, "appliance")
        primitives.append(_label(ax + aw / 2, ay + ad / 2, app["label"], 0.2))
        cx, cy = ax + aw / 2, ay + ad / 2
        if app["id"] == "sink":
            sink_pos = [cx, cy]
        elif app["id"] == "stove":
            stove_pos = [cx, cy]
        elif app["id"] == "fridge":
            fridge_pos = [H * 0.1, H * 0.5]  # on west wall

    # Work triangle (advisory dashed lines)
    if tmpl.get("show_work_triangle") and sink_pos and stove_pos and fridge_pos:
        for a, b in [(sink_pos, stove_pos), (stove_pos, fridge_pos), (fridge_pos, sink_pos)]:
            primitives.append(LinePrimitive(p1=a, p2=b, layer="annotation", style="dashed", weight=0.3))

    primitives.append(_dim([0, -0.5], [W, -0.5], W, units))
    primitives.append(_dim([-0.5, 0], [-0.5, H], H, units))

    return DetailDrawing(
        id=f"det-kitchen-{source_id}",
        name=f"Kitchen Detail — {room.name}",
        detail_type="kitchen",
        source_object_ids=[source_id],
        primitives=primitives,
        canvas_width=W + 2,
        canvas_height=H + 2,
        scale=tmpl.get("scale", "1:20"),
        view="plan",
        warnings=list(tmpl.get("annotations", [])),
        annotations=list(tmpl.get("annotations", [])),
        confidence=tmpl.get("confidence", 0.80),
        needs_review=tmpl.get("needs_review", True),
    )


# ── Door / Window Elevation ───────────────────────────────────────────────────


def _gen_door_window(project: ArchitectureProject, source_id: str, tmpl: dict) -> DetailDrawing:
    units = project.units
    # Try door first, then window
    door = next((d for d in project.doors if d.id == source_id), None)
    window = next((w for w in project.windows if w.id == source_id), None)
    obj = door or window
    if obj is None:
        raise ValueError(f"Door/window '{source_id}' not found")

    is_door = door is not None
    W = obj.width
    H = tmpl.get("standard_door_height_ft", 7.0) if is_door else (
        tmpl.get("standard_window_head_height_ft", 7.0) - tmpl.get("standard_window_sill_height_ft", 3.5)
    )
    sill_h = 0.0 if is_door else tmpl.get("standard_window_sill_height_ft", 3.5)
    kind = "Door" if is_door else "Window"
    primitives: list = []

    frame_t = tmpl.get("frame_thickness_in", 3.5) / 12.0

    # Outer frame
    primitives += _rect_lines(0, sill_h, W, H, "outline")
    # Inner opening (frame thickness)
    if frame_t > 0:
        primitives += _rect_lines(frame_t, sill_h + frame_t, W - 2 * frame_t, H - frame_t, "fixture")

    # Threshold / sill
    if is_door:
        primitives.append(LinePrimitive(p1=[0, 0.1], p2=[W, 0.1], layer="outline"))
    else:
        primitives += _rect_lines(0, sill_h - 0.2, W, 0.2, "fixture")

    # Door swing arc (quarter circle for door)
    if is_door:
        primitives.append(ArcPrimitive(center=[0, sill_h], radius=W, start_angle=0, end_angle=90, layer="annotation"))
        primitives.append(LinePrimitive(p1=[0, sill_h], p2=[W, sill_h], layer="annotation", style="dashed"))

    # Dimensions
    primitives.append(_dim([0, sill_h - 0.8], [W, sill_h - 0.8], W, units))
    primitives.append(_dim([W + 0.5, sill_h], [W + 0.5, sill_h + H], H, units))
    if not is_door:
        primitives.append(_dim([W + 0.5, 0], [W + 0.5, sill_h], sill_h, units))
    primitives.append(_label(W / 2, sill_h + H + 0.4, f"{kind} — {UnitConversionService.format_dimension(W, units)} wide", 0.3))

    total_canvas_h = sill_h + H + 2.0

    return DetailDrawing(
        id=f"det-dw-{source_id}",
        name=f"{kind} Elevation — {source_id}",
        detail_type="door_window",
        source_object_ids=[source_id],
        primitives=primitives,
        canvas_width=W + 3,
        canvas_height=total_canvas_h,
        scale=tmpl.get("scale", "1:10"),
        view="elevation",
        warnings=list(tmpl.get("annotations", [])),
        annotations=list(tmpl.get("annotations", [])),
        confidence=tmpl.get("confidence", 0.90),
        needs_review=tmpl.get("needs_review", False),
    )


# ── Wall Section ──────────────────────────────────────────────────────────────


def _gen_wall_section(project: ArchitectureProject, source_id: str, tmpl: dict) -> DetailDrawing:
    room = next((r for r in project.rooms if r.id == source_id), None)
    if room is None:
        raise ValueError(f"Room '{source_id}' not found")

    floor_h = project.building.floor_height
    wall_t = tmpl.get("wall_thickness_ft", 0.75)
    primitives: list = []

    # Floor layers (stack from y=0 upward)
    y = 0.0
    for layer in tmpl.get("floor_layers", []):
        d = layer["depth_ft"]
        primitives += _rect_lines(0, y, wall_t, d, "outline")
        primitives.append(HatchPrimitive(
            boundary=[[0, y], [wall_t, y], [wall_t, y + d], [0, y + d]],
            pattern=layer.get("hatch", "ANSI31"),
            angle=layer.get("angle", 45),
            layer="hatch",
        ))
        primitives.append(_label(wall_t + 0.3, y + d / 2, layer["name"], 0.2))
        y += d

    # Wall body above slab
    slab_top = y
    wall_h = floor_h
    for wl in tmpl.get("wall_layers", []):
        wd = wl["depth_ft"]
        primitives += _rect_lines(0, slab_top, wd, wall_h, "outline")
        primitives.append(HatchPrimitive(
            boundary=[[0, slab_top], [wd, slab_top], [wd, slab_top + wall_h], [0, slab_top + wall_h]],
            pattern=wl.get("hatch", "AR-BRIK"),
            angle=wl.get("angle", 0),
            layer="hatch",
        ))
        primitives.append(_label(wd + 0.3, slab_top + wall_h / 2, wl["name"], 0.2))

    # Floor-to-ceiling dimension
    primitives.append(_dim([-0.5, slab_top], [-0.5, slab_top + wall_h], wall_h, project.units))
    primitives.append(_label(wall_t / 2, -0.5, "Floor Section", 0.3))

    total_h = slab_top + wall_h + 1.5

    return DetailDrawing(
        id=f"det-section-{source_id}",
        name=f"Wall Section — {room.name}",
        detail_type="wall_section",
        source_object_ids=[source_id],
        primitives=primitives,
        canvas_width=wall_t + 4,
        canvas_height=total_h,
        scale=tmpl.get("scale", "1:20"),
        view="section",
        warnings=list(tmpl.get("annotations", [])),
        annotations=list(tmpl.get("annotations", [])),
        confidence=tmpl.get("confidence", 0.75),
        needs_review=tmpl.get("needs_review", True),
    )


# ── Tile Layout ───────────────────────────────────────────────────────────────


def _gen_tile_layout(project: ArchitectureProject, source_id: str, tmpl: dict) -> DetailDrawing:
    room = next((r for r in project.rooms if r.id == source_id), None)
    if room is None:
        raise ValueError(f"Room '{source_id}' not found")

    W = room.width
    H = room.depth
    tw = tmpl.get("default_tile_width_ft", 2.0)
    th = tmpl.get("default_tile_height_ft", 2.0)
    primitives: list = []

    # Room outline
    primitives += _rect_lines(0, 0, W, H, "outline")

    # Tile grid from centre
    cx = W / 2
    cy = H / 2
    cols = math.ceil(W / tw) + 2
    rows = math.ceil(H / th) + 2
    start_x = cx - (cols / 2) * tw
    start_y = cy - (rows / 2) * th

    for r in range(rows):
        for c in range(cols):
            tx = start_x + c * tw
            ty = start_y + r * th
            # Clip to room bounds
            x1 = max(tx, 0)
            y1 = max(ty, 0)
            x2 = min(tx + tw, W)
            y2 = min(ty + th, H)
            if x2 > x1 and y2 > y1:
                primitives += _rect_lines(x1, y1, x2 - x1, y2 - y1, "fixture")

    # Centre lines
    primitives.append(LinePrimitive(p1=[cx, 0], p2=[cx, H], layer="annotation", style="dashed", weight=0.25))
    primitives.append(LinePrimitive(p1=[0, cy], p2=[W, cy], layer="annotation", style="dashed", weight=0.25))

    # Dimensions
    primitives.append(_dim([0, -0.5], [W, -0.5], W, project.units))
    primitives.append(_dim([-0.5, 0], [-0.5, H], H, project.units))
    primitives.append(_dim([0, -1.0], [tw, -1.0], tw, project.units))

    primitives.append(_label(W / 2, H + 0.6, f"Tile Layout — {room.name}", 0.3))
    primitives.append(_label(W / 2, H + 0.25,
                             f"Tile: {UnitConversionService.format_dimension(tw, project.units)} × "
                             f"{UnitConversionService.format_dimension(th, project.units)}", 0.2))

    return DetailDrawing(
        id=f"det-tile-{source_id}",
        name=f"Tile Layout — {room.name}",
        detail_type="tile_layout",
        source_object_ids=[source_id],
        primitives=primitives,
        canvas_width=W + 2,
        canvas_height=H + 2.5,
        scale=tmpl.get("scale", "1:20"),
        view="plan",
        warnings=list(tmpl.get("annotations", [])),
        annotations=list(tmpl.get("annotations", [])),
        confidence=tmpl.get("confidence", 0.88),
        needs_review=tmpl.get("needs_review", True),
    )


# ── Stair Section ─────────────────────────────────────────────────────────────


def _gen_stair(project: ArchitectureProject, source_id: str, tmpl: dict) -> DetailDrawing:
    # Find StairEntity first, then fall back to stair Room
    stair_ent: StairEntity | None = next(
        (s for s in project.stairs if s.id == source_id or s.room_id == source_id), None
    )
    if stair_ent is None:
        raise ValueError(f"Stair '{source_id}' not found in project.stairs")

    n = stair_ent.risers
    td = stair_ent.tread_depth
    rh = stair_ent.riser_height
    total_run = n * td
    total_rise = (n + 1) * rh
    handrail_h = tmpl.get("handrail_height_ft", 3.0)
    units = project.units
    primitives: list = []

    # Stair profile: stepped outline
    x, y = 0.0, 0.0
    for i in range(n):
        # Tread (horizontal)
        primitives.append(LinePrimitive(p1=[x, y], p2=[x + td, y], layer="outline"))
        # Riser (vertical)
        primitives.append(LinePrimitive(p1=[x + td, y], p2=[x + td, y + rh], layer="outline"))
        x += td
        y += rh

    # Ground line
    primitives.append(LinePrimitive(p1=[0, 0], p2=[total_run + 0.5, 0], layer="outline", style="dashed"))
    # Closing sides
    primitives.append(LinePrimitive(p1=[0, 0], p2=[0, rh], layer="outline"))

    # Handrail
    if tmpl.get("show_handrail"):
        hr_y_start = rh + handrail_h
        hr_y_end = total_rise + handrail_h
        hr_ext = tmpl.get("handrail_extension_ft", 1.0)
        primitives.append(LinePrimitive(p1=[0, hr_y_start], p2=[total_run + hr_ext, hr_y_end], layer="annotation", weight=0.7))
        primitives.append(LinePrimitive(p1=[0, hr_y_start], p2=[0, 0], layer="annotation", style="dashed", weight=0.3))
        primitives.append(_label(total_run / 2, hr_y_end + 0.3, f"Handrail @ {UnitConversionService.format_dimension(handrail_h, units)} above nosing", 0.2))

    # Dimensions
    primitives.append(_dim([0, -0.5], [total_run, -0.5], total_run, units))
    primitives.append(_dim([total_run + 0.7, 0], [total_run + 0.7, total_rise], total_rise, units))
    primitives.append(_dim([0, -1.0], [td, -1.0], td, units))
    primitives.append(_label(td / 2, rh / 2, f"{n}R", 0.25))
    primitives.append(_label(total_run / 2, -1.5,
                             f"{n} Risers × {UnitConversionService.format_dimension(rh, units)}", 0.22))
    primitives.append(_label(total_run / 2, -1.9,
                             f"Tread: {UnitConversionService.format_dimension(td, units)}", 0.22))

    return DetailDrawing(
        id=f"det-stair-{source_id}",
        name=f"Stair Section — {stair_ent.id}",
        detail_type="stair",
        source_object_ids=[source_id, stair_ent.room_id],
        primitives=primitives,
        canvas_width=total_run + 3,
        canvas_height=total_rise + handrail_h + 3,
        scale=tmpl.get("scale", "1:20"),
        view="section",
        warnings=list(tmpl.get("annotations", [])),
        annotations=list(tmpl.get("annotations", [])),
        confidence=tmpl.get("confidence", 0.80),
        needs_review=tmpl.get("needs_review", True),
    )


# ── Public API ────────────────────────────────────────────────────────────────

_GENERATORS = {
    "toilet": _gen_toilet,
    "kitchen": _gen_kitchen,
    "door_window": _gen_door_window,
    "wall_section": _gen_wall_section,
    "tile_layout": _gen_tile_layout,
    "stair": _gen_stair,
}


class DetailEngine:
    """Generate and manage DetailDrawing objects for an ArchitectureProject."""

    @classmethod
    def generate(
        cls,
        project: ArchitectureProject,
        detail_type: str,
        source_id: str,
    ) -> DetailDrawing:
        tmpl = _load_template(detail_type)
        gen_fn = _GENERATORS.get(detail_type)
        if gen_fn is None:
            raise ValueError(f"Unsupported detail type: '{detail_type}'")
        return gen_fn(project, source_id, tmpl)

    @classmethod
    def replace_or_add(
        cls,
        drawings: list[DetailDrawing],
        new_drawing: DetailDrawing,
    ) -> list[DetailDrawing]:
        """Replace an existing drawing with the same id, or append."""
        result = [d for d in drawings if d.id != new_drawing.id]
        result.append(new_drawing)
        return result

    @classmethod
    def mark_stale_for_source(
        cls,
        drawings: list[DetailDrawing],
        source_id: str,
    ) -> list[DetailDrawing]:
        """Mark all drawings that reference source_id as stale."""
        return [
            d.model_copy(update={"stale": True}) if source_id in d.source_object_ids else d
            for d in drawings
        ]

    @classmethod
    def remove(cls, drawings: list[DetailDrawing], detail_id: str) -> list[DetailDrawing]:
        return [d for d in drawings if d.id != detail_id]
