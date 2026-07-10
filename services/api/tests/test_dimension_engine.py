"""Tests for AutoDimensionEngine (Phase 29.0)."""

from app.core.architecture.dimension_engine import AutoDimensionEngine
from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.validation import validate_project


def _make_project(prompt: str = "2BHK 30x50 east-facing"):
    project, _ = generate_floorplan(parse_prompt(prompt))
    return project


def test_derive_returns_dims_for_generated_project() -> None:
    project = _make_project()
    dims = AutoDimensionEngine.derive(project)
    assert len(dims) > 0


def test_derive_includes_site_dims() -> None:
    project = _make_project()
    dims = AutoDimensionEngine.derive(project)
    ids = {d.id for d in dims}
    assert "dim-site-width" in ids
    assert "dim-site-depth" in ids


def test_derive_site_dim_values_match_site() -> None:
    project = _make_project()
    dims = {d.id: d for d in AutoDimensionEngine.derive(project)}
    assert abs(dims["dim-site-width"].value - project.site.width) < 1e-6
    assert abs(dims["dim-site-depth"].value - project.site.depth) < 1e-6


def test_derive_room_dims_for_every_room() -> None:
    project = _make_project()
    dims = AutoDimensionEngine.derive(project)
    dim_room_ids = {d.id for d in dims if d.dim_type == "room"}
    for room in project.rooms:
        assert f"dim-{room.id}-w" in dim_room_ids
        assert f"dim-{room.id}-d" in dim_room_ids


def test_derive_room_dim_values_match_room() -> None:
    project = _make_project()
    dims = {d.id: d for d in AutoDimensionEngine.derive(project)}
    for room in project.rooms:
        w_dim = dims[f"dim-{room.id}-w"]
        d_dim = dims[f"dim-{room.id}-d"]
        assert abs(w_dim.value - room.width) < 1e-6
        assert abs(d_dim.value - room.depth) < 1e-6


def test_derive_layers() -> None:
    project = _make_project()
    dims = AutoDimensionEngine.derive(project)
    layers = {d.layer for d in dims}
    assert "dim-external" in layers
    assert "dim-room" in layers


def test_derive_labels_use_feet_notation() -> None:
    project = _make_project()
    # Default units are feet; labels should use ′ / ″
    dims = AutoDimensionEngine.derive(project)
    site_w = next(d for d in dims if d.id == "dim-site-width")
    assert "′" in site_w.label


def test_derive_stair_entities_no_stairs() -> None:
    project = _make_project("studio 20x30")
    stairs = AutoDimensionEngine.derive_stair_entities(project)
    # If no stair rooms exist, list should be empty
    stair_rooms = [r for r in project.rooms if r.type == "stair"]
    assert len(stairs) == len(stair_rooms)


def test_derive_stair_entities_doesnt_duplicate() -> None:
    # Generate a multi-floor project that likely has stairs
    project, _ = generate_floorplan(parse_prompt("3BHK villa 40x60 2 floors"))
    stairs1 = AutoDimensionEngine.derive_stair_entities(project)
    # Running again should not add duplicates
    project2 = project.model_copy(update={"stairs": stairs1})
    stairs2 = AutoDimensionEngine.derive_stair_entities(project2)
    assert len(stairs2) == len(stairs1)


def test_generator_populates_dimensions() -> None:
    project = _make_project()
    # generator now calls AutoDimensionEngine.derive
    assert len(project.dimensions) > 0


def test_derived_dims_still_pass_validation() -> None:
    project = _make_project()
    result = validate_project(project)
    assert result.valid, result.errors
