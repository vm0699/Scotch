"""Tests for DetailDrawing model schema and back-compat (Phase 30.3)."""

import json

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models.project import (
    ArcPrimitive,
    ArchitectureProject,
    DetailDrawing,
    DimPrimitive,
    HatchPrimitive,
    LinePrimitive,
    TextPrimitive,
)
from app.core.validation import validate_project


def _base_project():
    project, _ = generate_floorplan(parse_prompt("2BHK 30x50 east-facing with 2 bathrooms kitchen"))
    return project


def test_new_project_has_detail_drawings() -> None:
    project = _base_project()
    assert hasattr(project, "detail_drawings")
    assert project.detail_drawings == []


def test_old_project_loads_without_detail_drawings() -> None:
    project = _base_project()
    data = project.model_dump()
    data.pop("detail_drawings", None)
    loaded = ArchitectureProject.model_validate(data)
    assert loaded.detail_drawings == []


def test_line_primitive_model() -> None:
    lp = LinePrimitive(p1=[0.0, 0.0], p2=[5.0, 0.0])
    assert lp.kind == "line"
    assert lp.layer == "outline"
    assert lp.style == "solid"


def test_arc_primitive_model() -> None:
    ap = ArcPrimitive(center=[3.0, 3.0], radius=2.0, start_angle=0, end_angle=90)
    assert ap.kind == "arc"


def test_text_primitive_model() -> None:
    tp = TextPrimitive(pos=[2.5, 2.5], text="WC")
    assert tp.kind == "text"
    assert tp.height == 0.2


def test_dim_primitive_model() -> None:
    dp = DimPrimitive(p1=[0.0, -0.5], p2=[5.0, -0.5], value=5.0, label="5′-0″")
    assert dp.kind == "dim"


def test_hatch_primitive_model() -> None:
    hp = HatchPrimitive(boundary=[[0, 0], [2, 0], [2, 1], [0, 1]])
    assert hp.kind == "hatch"
    assert hp.pattern == "ANSI31"


def test_detail_drawing_model() -> None:
    drawing = DetailDrawing(
        id="det-1",
        name="Test Detail",
        detail_type="toilet",
        source_object_ids=["bath-1"],
        primitives=[
            LinePrimitive(p1=[0.0, 0.0], p2=[5.0, 0.0]),
            TextPrimitive(pos=[2.5, 2.5], text="WC"),
        ],
    )
    assert drawing.detail_type == "toilet"
    assert drawing.stale is False
    assert drawing.needs_review is True
    assert len(drawing.primitives) == 2


def test_detail_drawing_round_trip() -> None:
    drawing = DetailDrawing(
        id="det-rt",
        name="Round-trip test",
        detail_type="wall_section",
        primitives=[DimPrimitive(p1=[0, 0], p2=[5, 0], value=5.0, label="5′-0″")],
    )
    data = json.loads(drawing.model_dump_json())
    loaded = DetailDrawing.model_validate(data)
    assert loaded.id == "det-rt"
    assert len(loaded.primitives) == 1
    assert loaded.primitives[0].kind == "dim"


def test_project_with_detail_validates() -> None:
    project = _base_project()
    drawing = DetailDrawing(
        id="det-test",
        name="Test",
        detail_type="toilet",
        source_object_ids=[project.rooms[0].id],
        primitives=[LinePrimitive(p1=[0.0, 0.0], p2=[1.0, 0.0])],
    )
    project2 = project.model_copy(update={"detail_drawings": [drawing]})
    result = validate_project(project2)
    assert result.valid, result.errors


def test_project_detail_drawings_round_trip() -> None:
    project = _base_project()
    drawing = DetailDrawing(id="det-x", name="X", detail_type="kitchen")
    project2 = project.model_copy(update={"detail_drawings": [drawing]})
    data = json.loads(project2.model_dump_json())
    loaded = ArchitectureProject.model_validate(data)
    assert len(loaded.detail_drawings) == 1
    assert loaded.detail_drawings[0].id == "det-x"
