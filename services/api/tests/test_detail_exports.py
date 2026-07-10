"""Tests for Detail Drawing SVG exporter (Phase 30.7)."""

import xml.etree.ElementTree as ET

import pytest

from app.core.architecture.detail_engine import DetailEngine
from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.exports.detail_exporter import export_detail_svg


def _project(prompt="2BHK 30x50 east-facing with 2 bathrooms kitchen 2 floors"):
    p, _ = generate_floorplan(parse_prompt(prompt))
    return p


def _toilet_detail(project):
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    return DetailEngine.generate(project, "toilet", bath.id)


def _tile_detail(project):
    room = next(r for r in project.rooms if r.type != "stair")
    return DetailEngine.generate(project, "tile_layout", room.id)


def _wall_section_detail(project):
    room = project.rooms[0]
    return DetailEngine.generate(project, "wall_section", room.id)


def test_toilet_detail_exports_svg() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    svg = export_detail_svg(drawing)
    assert isinstance(svg, bytes)
    assert svg.startswith(b"<svg")


def test_svg_is_valid_xml() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    svg = export_detail_svg(drawing)
    root = ET.fromstring(svg.decode("utf-8"))
    assert root.tag.endswith("svg")


def test_svg_has_viewbox() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    svg = export_detail_svg(drawing).decode("utf-8")
    assert "viewBox" in svg


def test_svg_has_title_block() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    svg = export_detail_svg(drawing).decode("utf-8")
    assert "title-block" in svg
    assert drawing.name in svg


def test_svg_has_scale_annotation() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    svg = export_detail_svg(drawing).decode("utf-8")
    assert drawing.scale in svg


def test_svg_has_outline_layer() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    svg = export_detail_svg(drawing).decode("utf-8")
    assert 'id="outline"' in svg


def test_svg_has_dim_layer() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    svg = export_detail_svg(drawing).decode("utf-8")
    assert 'id="dim"' in svg


def test_svg_has_annotation_layer() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    svg = export_detail_svg(drawing).decode("utf-8")
    assert 'id="annotation"' in svg or "annotation" in svg


def test_tile_layout_svg_has_many_lines() -> None:
    project = _project()
    drawing = _tile_detail(project)
    svg = export_detail_svg(drawing).decode("utf-8")
    # Tile grid should produce many <line> elements
    assert svg.count("<line") >= 4


def test_wall_section_svg_has_hatch() -> None:
    project = _project()
    drawing = _wall_section_detail(project)
    svg = export_detail_svg(drawing).decode("utf-8")
    assert 'id="hatch"' in svg or "<polygon" in svg


def test_review_flag_watermark() -> None:
    project = _project()
    drawing = _toilet_detail(project)
    assert drawing.needs_review is True
    svg = export_detail_svg(drawing).decode("utf-8")
    assert "FOR REVIEW" in svg or "NOT CONSTRUCTION" in svg


def test_door_elevation_exports_svg() -> None:
    project = _project()
    if not project.doors:
        pytest.skip("No doors")
    drawing = DetailEngine.generate(project, "door_window", project.doors[0].id)
    svg = export_detail_svg(drawing)
    root = ET.fromstring(svg.decode("utf-8"))
    assert root.tag.endswith("svg")


def test_stair_section_exports_svg() -> None:
    project = _project()
    if not project.stairs:
        pytest.skip("No stairs")
    drawing = DetailEngine.generate(project, "stair", project.stairs[0].id)
    svg = export_detail_svg(drawing)
    assert svg.startswith(b"<svg")
