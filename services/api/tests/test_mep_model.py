"""Tests for MEP model schema and back-compat (Phase 29.2)."""

import json

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models.project import (
    ACPlan,
    ArchitectureProject,
    ElectricalPlan,
    LightingPlan,
    MEPPlan,
    PlumbingPlan,
    ServicePoint,
    ServiceRoute,
)
from app.core.validation import validate_project


def _base_project() -> ArchitectureProject:
    project, _ = generate_floorplan(parse_prompt("2BHK 30x50"))
    return project


def test_new_project_has_mep_plan() -> None:
    project = _base_project()
    assert project.mep_plan is not None


def test_mep_plan_defaults_not_generated() -> None:
    project = _base_project()
    assert project.mep_plan.generated is False
    assert project.mep_plan.stale is False


def test_mep_sub_plans_empty_by_default() -> None:
    project = _base_project()
    mep = project.mep_plan
    assert mep.plumbing.points == []
    assert mep.electrical.points == []
    assert mep.lighting.points == []
    assert mep.ac.points == []


def test_old_project_loads_without_mep() -> None:
    """A serialized project without mep_plan must still load via back-compat defaults."""
    project, _ = generate_floorplan(parse_prompt("studio 20x30"))
    data = project.model_dump()
    # Strip mep fields to simulate old serialization
    data.pop("mep_plan", None)
    data.pop("dimensions", None)
    data.pop("stairs", None)
    data.pop("show_mep", None)
    data.pop("show_dimensions", None)
    loaded = ArchitectureProject.model_validate(data)
    assert loaded.mep_plan is not None
    assert loaded.dimensions == []
    assert loaded.stairs == []
    assert loaded.show_mep is False


def test_service_point_model() -> None:
    sp = ServicePoint(
        id="p-1",
        system="plumbing",
        kind="wc",
        room_id="bath-1",
        x=5.0,
        y=10.0,
    )
    assert sp.confidence == 0.85
    assert sp.needs_review is False
    assert sp.user_override is False


def test_service_route_model() -> None:
    sr = ServiceRoute(
        id="r-1",
        system="plumbing",
        polyline=[[0.0, 0.0], [5.0, 0.0], [5.0, 10.0]],
        kind="supply",
    )
    assert len(sr.polyline) == 3
    assert sr.needs_review is True


def test_mep_plan_serialises_round_trip() -> None:
    project = _base_project()
    data = json.loads(project.model_dump_json())
    loaded = ArchitectureProject.model_validate(data)
    assert loaded.mep_plan.generated == project.mep_plan.generated


def test_plumbing_plan_model() -> None:
    pp = PlumbingPlan(
        points=[ServicePoint(id="p1", system="plumbing", kind="sink", room_id="k1", x=1.0, y=1.0)],
        routes=[],
    )
    assert len(pp.points) == 1
    assert pp.needs_review is True


def test_project_validates_with_mep_data() -> None:
    project = _base_project()
    room = project.rooms[0]
    point = ServicePoint(id="sp-test", system="plumbing", kind="basin", room_id=room.id, x=room.x + 1, y=room.y + 1)
    mep = MEPPlan(
        plumbing=PlumbingPlan(points=[point]),
        generated=True,
    )
    project2 = project.model_copy(update={"mep_plan": mep})
    result = validate_project(project2)
    assert result.valid, result.errors
