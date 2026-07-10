"""Tests for DetailEngine generators (Phase 30.4)."""

import pytest

from app.core.architecture.detail_engine import DetailEngine
from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models.project import DetailDrawing
from app.core.validation import validate_project


def _project(prompt="2BHK 30x50 east-facing with 2 bathrooms kitchen 2 floors"):
    p, _ = generate_floorplan(parse_prompt(prompt))
    return p


# ── toilet ───────────────────────────────────────────────────────────────────


def test_toilet_detail_generates() -> None:
    project = _project()
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    drawing = DetailEngine.generate(project, "toilet", bath.id)
    assert drawing.detail_type == "toilet"
    assert bath.id in drawing.source_object_ids


def test_toilet_detail_has_primitives() -> None:
    project = _project()
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    drawing = DetailEngine.generate(project, "toilet", bath.id)
    assert len(drawing.primitives) > 0


def test_toilet_detail_not_stale() -> None:
    project = _project()
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    drawing = DetailEngine.generate(project, "toilet", bath.id)
    assert drawing.stale is False


def test_toilet_detail_has_annotations() -> None:
    project = _project()
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    drawing = DetailEngine.generate(project, "toilet", bath.id)
    assert len(drawing.annotations) > 0


# ── kitchen ──────────────────────────────────────────────────────────────────


def test_kitchen_detail_generates() -> None:
    project = _project()
    kitchen = next((r for r in project.rooms if r.type == "kitchen"), None)
    if kitchen is None:
        pytest.skip("No kitchen in generated plan")
    drawing = DetailEngine.generate(project, "kitchen", kitchen.id)
    assert drawing.detail_type == "kitchen"


def test_kitchen_has_work_triangle_annotation() -> None:
    project = _project()
    kitchen = next((r for r in project.rooms if r.type == "kitchen"), None)
    if kitchen is None:
        pytest.skip("No kitchen")
    drawing = DetailEngine.generate(project, "kitchen", kitchen.id)
    assert len(drawing.annotations) > 0


# ── door/window elevation ─────────────────────────────────────────────────────


def test_door_elevation_generates() -> None:
    project = _project()
    if not project.doors:
        pytest.skip("No doors")
    drawing = DetailEngine.generate(project, "door_window", project.doors[0].id)
    assert drawing.detail_type == "door_window"
    assert drawing.view == "elevation"


def test_door_elevation_has_dimensions() -> None:
    project = _project()
    if not project.doors:
        pytest.skip("No doors")
    drawing = DetailEngine.generate(project, "door_window", project.doors[0].id)
    dim_prims = [p for p in drawing.primitives if p.kind == "dim"]
    assert len(dim_prims) >= 1


# ── wall section ──────────────────────────────────────────────────────────────


def test_wall_section_generates() -> None:
    project = _project()
    room = project.rooms[0]
    drawing = DetailEngine.generate(project, "wall_section", room.id)
    assert drawing.detail_type == "wall_section"
    assert drawing.view == "section"


def test_wall_section_has_hatches() -> None:
    project = _project()
    room = project.rooms[0]
    drawing = DetailEngine.generate(project, "wall_section", room.id)
    hatch_prims = [p for p in drawing.primitives if p.kind == "hatch"]
    assert len(hatch_prims) > 0


# ── tile layout ───────────────────────────────────────────────────────────────


def test_tile_layout_generates() -> None:
    project = _project()
    room = next((r for r in project.rooms if r.type != "stair"), None)
    if room is None:
        pytest.skip("No eligible room")
    drawing = DetailEngine.generate(project, "tile_layout", room.id)
    assert drawing.detail_type == "tile_layout"
    assert drawing.view == "plan"


def test_tile_layout_has_grid_lines() -> None:
    project = _project()
    room = next(r for r in project.rooms if r.type != "stair")
    drawing = DetailEngine.generate(project, "tile_layout", room.id)
    # Should have many line primitives (tile grid)
    line_prims = [p for p in drawing.primitives if p.kind == "line"]
    assert len(line_prims) > 4


# ── stair section ─────────────────────────────────────────────────────────────


def test_stair_section_generates() -> None:
    project = _project()
    if not project.stairs:
        pytest.skip("No stair entities")
    drawing = DetailEngine.generate(project, "stair", project.stairs[0].id)
    assert drawing.detail_type == "stair"
    assert drawing.view == "section"


def test_stair_section_has_riser_lines() -> None:
    project = _project()
    if not project.stairs:
        pytest.skip("No stair entities")
    drawing = DetailEngine.generate(project, "stair", project.stairs[0].id)
    line_prims = [p for p in drawing.primitives if p.kind == "line"]
    assert len(line_prims) >= project.stairs[0].risers


# ── invalid source ────────────────────────────────────────────────────────────


def test_invalid_source_raises() -> None:
    project = _project()
    with pytest.raises(ValueError, match="not found"):
        DetailEngine.generate(project, "toilet", "nonexistent-id")


def test_invalid_detail_type_raises() -> None:
    project = _project()
    with pytest.raises(ValueError, match="Unsupported"):
        DetailEngine.generate(project, "unsupported_type", project.rooms[0].id)


# ── stale marking ─────────────────────────────────────────────────────────────


def test_mark_stale_for_source() -> None:
    project = _project()
    room = next(r for r in project.rooms if r.type != "stair")
    drawing = DetailEngine.generate(project, "tile_layout", room.id)
    drawings = [drawing]
    assert drawing.stale is False
    updated = DetailEngine.mark_stale_for_source(drawings, room.id)
    assert updated[0].stale is True


def test_mark_stale_only_affects_matching() -> None:
    project = _project()
    rooms = [r for r in project.rooms if r.type != "stair"]
    if len(rooms) < 2:
        pytest.skip("Need at least 2 rooms")
    d1 = DetailEngine.generate(project, "tile_layout", rooms[0].id)
    d2 = DetailEngine.generate(project, "tile_layout", rooms[1].id)
    updated = DetailEngine.mark_stale_for_source([d1, d2], rooms[0].id)
    assert updated[0].stale is True
    assert updated[1].stale is False


# ── replace_or_add ────────────────────────────────────────────────────────────


def test_replace_or_add_replaces_existing() -> None:
    project = _project()
    room = next(r for r in project.rooms if r.type != "stair")
    d1 = DetailEngine.generate(project, "tile_layout", room.id)
    d2 = DetailEngine.generate(project, "tile_layout", room.id)
    result = DetailEngine.replace_or_add([d1], d2)
    assert len(result) == 1
    assert result[0].id == d2.id


def test_replace_or_add_appends_new() -> None:
    project = _project()
    rooms = [r for r in project.rooms if r.type != "stair"]
    if len(rooms) < 2:
        pytest.skip("Need at least 2 rooms")
    d1 = DetailEngine.generate(project, "tile_layout", rooms[0].id)
    d2 = DetailEngine.generate(project, "tile_layout", rooms[1].id)
    result = DetailEngine.replace_or_add([d1], d2)
    assert len(result) == 2


# ── project-level validation ──────────────────────────────────────────────────


def test_project_with_detail_drawing_validates() -> None:
    project = _project()
    room = next(r for r in project.rooms if r.type != "stair")
    drawing = DetailEngine.generate(project, "tile_layout", room.id)
    project2 = project.model_copy(update={"detail_drawings": [drawing]})
    result = validate_project(project2)
    assert result.valid, result.errors
