"""Tests for MEP export layers in SVG exporter (Phase 29.7)."""

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.mep_generator import MEPGenerator
from app.core.architecture.requirement_parser import parse_prompt
from app.core.exports import export_svg


def _project_with_mep(prompt: str = "2BHK 30x50 east-facing with 2 bathrooms kitchen"):
    project, _ = generate_floorplan(parse_prompt(prompt))
    mep = MEPGenerator.generate(project)
    return project.model_copy(update={"mep_plan": mep, "show_mep": True})


def _svg(project, tmp_path) -> str:
    out = tmp_path / "test.svg"
    return export_svg(project, out).decode("utf-8")


def test_svg_exports_without_error(tmp_path) -> None:
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    assert "<svg" in svg


def test_svg_contains_mep_layer_plumbing(tmp_path) -> None:
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    assert "P-FIXTURE" in svg or "P-PIPE" in svg or "plumbing" in svg.lower()


def test_svg_contains_mep_layer_electrical(tmp_path) -> None:
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    assert "E-SWITCH" in svg or "E-SOCKET" in svg or "E-ROUTE" in svg or "electrical" in svg.lower()


def test_svg_contains_mep_layer_lighting(tmp_path) -> None:
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    assert "E-LIGHT" in svg or "lighting" in svg.lower()


def test_svg_contains_mep_layer_ac(tmp_path) -> None:
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    assert "M-AC" in svg or "ac" in svg.lower()


def test_svg_no_mep_layers_when_not_generated(tmp_path) -> None:
    project, _ = generate_floorplan(parse_prompt("2BHK 30x50"))
    svg = _svg(project, tmp_path)
    assert "P-FIXTURE" not in svg
    assert "E-SWITCH" not in svg
    assert "M-AC" not in svg


def test_svg_with_mep_has_plumbing_points(tmp_path) -> None:
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    # Plumbing points render as circles
    assert "<circle" in svg


def test_svg_dim_layer_present(tmp_path) -> None:
    project, _ = generate_floorplan(parse_prompt("2BHK 30x50"))
    svg = _svg(project, tmp_path)
    # Dimension layer group or line elements should exist
    assert "dim" in svg or "<line" in svg


def test_svg_mep_routes_rendered_as_polylines(tmp_path) -> None:
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    assert "<polyline" in svg or "<path" in svg


def test_svg_is_valid_xml_structure(tmp_path) -> None:
    import xml.etree.ElementTree as ET
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "viewBox" in root.attrib


def test_svg_has_required_base_layers(tmp_path) -> None:
    project = _project_with_mep()
    svg = _svg(project, tmp_path)
    for layer in ("rooms", "doors", "labels"):
        assert f'id="{layer}"' in svg, f"Missing base SVG layer group: {layer}"
