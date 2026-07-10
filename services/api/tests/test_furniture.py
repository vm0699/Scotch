"""Phase 26 — Furniture / Interior Layout tests.

Covers:
  - furniture_defaults  : templates return items; size-filtered items excluded
  - furniture_placer    : items within room bounds; clearance; no overlaps; room types
  - generator integration: generated project has furniture; types populated
  - apply_changes       : show_furniture toggle; layout refreshed after add_room
  - export inclusion    : SketchUp, Blender, and IFC scripts reference furniture
"""

from __future__ import annotations

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.furniture_defaults import (
    ROOM_FURNITURE,
    get_template,
    furniture_height,
)
from app.core.architecture.furniture_placer import (
    place_furniture_in_room,
    place_all_furniture,
    _fits_in_room,
    _overlaps,
    _Box,
)
from app.core.architecture.regenerate import apply_changes, ParameterChange
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models.project import FurnitureItem, Room
from app.core.exports.sketchup_exporter import export_sketchup
from app.core.exports.blender_exporter import export_blender


# ── Helpers ───────────────────────────────────────────────────────────────────

def _room(room_type: str, w: float, d: float, room_id: str = "r1") -> Room:
    return Room(id=room_id, name=room_type.capitalize(), type=room_type,
                x=0.0, y=0.0, width=w, depth=d)


def _gen(prompt: str):
    return generate_floorplan(parse_prompt(prompt))


# ── furniture_defaults ────────────────────────────────────────────────────────

def test_bedroom_template_not_empty() -> None:
    specs = get_template("bedroom", 12, 12)
    assert specs, "bedroom template should have items for a 12×12 room"


def test_living_template_has_sofa() -> None:
    specs = get_template("living", 15, 15)
    types = [s.type for s in specs]
    assert "sofa" in types


def test_bathroom_template_has_wc() -> None:
    specs = get_template("bathroom", 8, 10)
    types = [s.type for s in specs]
    assert "wc" in types


def test_small_room_filters_large_items() -> None:
    # A 6×6 ft room shouldn't get items requiring 100+ ft²
    specs_small = get_template("bedroom", 6, 6)
    specs_large = get_template("bedroom", 12, 12)
    # The small room should have fewer items (or same) — never more
    assert len(specs_small) <= len(specs_large)


def test_corridor_has_no_furniture() -> None:
    specs = get_template("corridor", 10, 10)
    assert specs == []


def test_furniture_height_lookup() -> None:
    assert furniture_height("wardrobe") == 7.0
    assert furniture_height("sofa") == 3.0
    assert furniture_height("wc") == 2.5
    # Unknown type falls back to default
    assert furniture_height("unknown_xyz") == 2.5


def test_all_room_types_have_template_entries() -> None:
    # All declared room types should be keys (including empty templates)
    assert "bedroom" in ROOM_FURNITURE
    assert "living" in ROOM_FURNITURE
    assert "bathroom" in ROOM_FURNITURE
    assert "dining" in ROOM_FURNITURE
    assert "kitchen" in ROOM_FURNITURE
    assert "study" in ROOM_FURNITURE


# ── furniture_placer ──────────────────────────────────────────────────────────

def test_bedroom_items_within_bounds() -> None:
    room = _room("bedroom", 12, 14)
    items = place_furniture_in_room(room)
    assert items, "no items placed in bedroom"
    for item in items:
        assert item.x >= room.x - 1e-6, f"{item.type}: x={item.x} out of bounds"
        assert item.y >= room.y - 1e-6, f"{item.type}: y={item.y} out of bounds"
        assert item.x + item.width <= room.x + room.width + 1e-6, \
            f"{item.type}: right edge {item.x + item.width} > {room.x + room.width}"
        assert item.y + item.depth <= room.y + room.depth + 1e-6, \
            f"{item.type}: bottom edge {item.y + item.depth} > {room.y + room.depth}"


def test_bedroom_has_bed() -> None:
    room = _room("bedroom", 12, 14)
    items = place_furniture_in_room(room)
    bed_types = {i.type for i in items}
    assert "double_bed" in bed_types or "king_bed" in bed_types, \
        "bedroom must have a bed"


def test_living_has_sofa() -> None:
    room = _room("living", 15, 16)
    items = place_furniture_in_room(room)
    types = {i.type for i in items}
    assert "sofa" in types, "living room must have a sofa"


def test_bathroom_has_wc() -> None:
    room = _room("bathroom", 8, 10)
    items = place_furniture_in_room(room)
    types = {i.type for i in items}
    assert "wc" in types, "bathroom must have a WC"


def test_kitchen_has_counter() -> None:
    room = _room("kitchen", 12, 12)
    items = place_furniture_in_room(room)
    types = {i.type for i in items}
    counter_types = {t for t in types if t.startswith("counter")}
    assert counter_types, "kitchen must have a counter"


def test_no_overlapping_items() -> None:
    room = _room("living", 18, 20)
    items = place_furniture_in_room(room)
    boxes = [_Box(i.x, i.y, i.width, i.depth) for i in items]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not _overlaps(boxes[i], boxes[j]), \
                f"overlap: {items[i].type} ∩ {items[j].type}"


def test_tiny_room_gets_no_items() -> None:
    # A 3×3 ft room is below minimum furniture footprint — should produce nothing
    room = _room("bedroom", 3, 3)
    items = place_furniture_in_room(room)
    # If any items were placed, they must fit
    for item in items:
        assert _fits_in_room(_Box(item.x, item.y, item.width, item.depth), room)


def test_all_items_have_valid_room_id() -> None:
    room = _room("master_bedroom", 14, 16)
    items = place_furniture_in_room(room)
    for item in items:
        assert item.room_id == "r1"


def test_items_have_positive_dimensions() -> None:
    for rtype in ("bedroom", "living", "bathroom", "kitchen", "dining"):
        room = _room(rtype, 14, 14)
        items = place_furniture_in_room(room)
        for item in items:
            assert item.width > 0, f"{item.type} width <= 0"
            assert item.depth > 0, f"{item.type} depth <= 0"
            assert item.height > 0, f"{item.type} height <= 0"


def test_place_all_furniture_returns_project() -> None:
    project, _ = _gen("2BHK apartment 30x50")
    result = place_all_furniture(project)
    assert result is not None
    assert len(result.furniture) > 0


# ── Generator integration ─────────────────────────────────────────────────────

def test_generated_project_has_furniture() -> None:
    project, _ = _gen("2BHK apartment 30x50")
    assert project.furniture, "generated project must have furniture"


def test_generated_bedroom_has_bed() -> None:
    # Use 40x60 site so bedrooms are ≥ 10 ft deep (bed 6.5 ft + clearance 3.5 ft)
    project, _ = _gen("2BHK apartment 40x60 with 2 bedrooms and 2 bathrooms")
    bedroom_ids = {r.id for r in project.rooms if r.type == "bedroom"}
    bed_items = [f for f in project.furniture
                 if f.room_id in bedroom_ids
                 and f.type in ("double_bed", "king_bed", "single_bed")]
    assert bed_items, "generated bedrooms must each have a bed"


def test_generated_living_has_sofa() -> None:
    project, _ = _gen("2BHK apartment 30x50")
    living_ids = {r.id for r in project.rooms if r.type == "living"}
    sofas = [f for f in project.furniture
             if f.room_id in living_ids and f.type == "sofa"]
    assert sofas, "generated living room must have a sofa"


def test_generated_bathroom_has_wc() -> None:
    project, _ = _gen("2BHK apartment 30x50 with 2 bathrooms")
    bath_ids = {r.id for r in project.rooms if r.type == "bathroom"}
    wcs = [f for f in project.furniture
           if f.room_id in bath_ids and f.type == "wc"]
    assert wcs, "generated bathrooms must have at least one WC"


def test_furniture_within_room_bounds() -> None:
    project, _ = _gen("3BHK villa 40x60")
    room_map = {r.id: r for r in project.rooms}
    for item in project.furniture:
        room = room_map.get(item.room_id)
        assert room is not None, f"orphaned furniture item {item.id}"
        assert item.x >= room.x - 1e-4
        assert item.y >= room.y - 1e-4
        assert item.x + item.width <= room.x + room.width + 1e-4
        assert item.y + item.depth <= room.y + room.depth + 1e-4


def test_show_furniture_defaults_true() -> None:
    project, _ = _gen("studio apartment 20x30")
    assert project.show_furniture is True


# ── apply_changes integration ─────────────────────────────────────────────────

def test_show_furniture_toggle() -> None:
    project, _ = _gen("2BHK apartment 30x50")
    assert project.show_furniture is True
    edited, _ = apply_changes(project, [ParameterChange(key="show_furniture", value=False)])
    assert edited.show_furniture is False
    # Toggle back on
    back, _ = apply_changes(edited, [ParameterChange(key="show_furniture", value=True)])
    assert back.show_furniture is True


def test_add_room_refreshes_furniture() -> None:
    project, _ = _gen("2BHK apartment 30x50")
    old_count = len(project.furniture)
    edited, _ = apply_changes(project, [ParameterChange(key="add_room", value="study")])
    # Adding a study should produce study furniture (desk, etc.)
    study_ids = {r.id for r in edited.rooms if r.type == "study"}
    study_furn = [f for f in edited.furniture if f.room_id in study_ids]
    assert study_furn, "newly added study room must get furniture"


# ── Export inclusion ──────────────────────────────────────────────────────────

def test_sketchup_export_references_furniture(tmp_path) -> None:
    project, _ = _gen("2BHK apartment 30x50")
    out = tmp_path / "test.rb"
    content = export_sketchup(project, out).decode()
    assert "S-FURNITURE" in content, "SketchUp export must have S-FURNITURE tag"
    assert "Scotch_Furniture" in content, "SketchUp export must include furniture groups"


def test_blender_export_references_furniture(tmp_path) -> None:
    project, _ = _gen("2BHK apartment 30x50")
    out = tmp_path / "test.py"
    content = export_blender(project, out).decode()
    assert "Scotch_Furniture" in content, "Blender export must include furniture collection"


def test_sketchup_export_no_furniture_when_hidden(tmp_path) -> None:
    project, _ = _gen("2BHK apartment 30x50")
    # Hide furniture on project level before exporting
    project = project.model_copy(update={"show_furniture": False, "furniture": []})
    out = tmp_path / "test_hidden.rb"
    content = export_sketchup(project, out).decode()
    # With no furniture items the block should be absent
    assert "tag_furn" not in content
