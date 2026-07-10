"""Tests for MEPGenerator (Phase 29.4)."""

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.mep_generator import MEPGenerator
from app.core.architecture.requirement_parser import parse_prompt
from app.core.validation import validate_project


def _project(prompt: str = "2BHK 30x50 east-facing with 2 bathrooms and kitchen"):
    p, _ = generate_floorplan(parse_prompt(prompt))
    return p


def test_generate_all_systems() -> None:
    project = _project()
    mep = MEPGenerator.generate(project)
    assert mep.generated is True
    assert mep.stale is False


def test_plumbing_points_in_wet_rooms() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["plumbing"])
    room_ids = {r.id for r in project.rooms}
    for pt in mep.plumbing.points:
        assert pt.room_id in room_ids, f"plumbing point {pt.id} has unknown room_id"
        assert pt.system == "plumbing"


def test_bathroom_gets_plumbing_fixtures() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["plumbing"])
    bath_rooms = {r.id for r in project.rooms if r.type in ("bathroom", "master_bathroom")}
    bath_points = [p for p in mep.plumbing.points if p.room_id in bath_rooms]
    assert len(bath_points) > 0, "No plumbing fixtures placed in bathroom rooms"


def test_kitchen_gets_plumbing_sink() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["plumbing"])
    kitchen_ids = {r.id for r in project.rooms if r.type == "kitchen"}
    sink_pts = [p for p in mep.plumbing.points if p.room_id in kitchen_ids and p.kind == "sink"]
    assert len(sink_pts) > 0, "No sink placed in kitchen"


def test_electrical_every_room_gets_switch() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["electrical"])
    room_ids = {r.id for r in project.rooms}
    switch_room_ids = {p.room_id for p in mep.electrical.points if p.kind == "switch"}
    # Every room should have at least a switch
    for rid in room_ids:
        assert rid in switch_room_ids, f"room {rid} has no switch"


def test_electrical_points_within_site() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["electrical"])
    for pt in mep.electrical.points:
        assert 0 <= pt.x <= project.site.width + 1, f"point {pt.id} x={pt.x} out of site"
        assert 0 <= pt.y <= project.site.depth + 1, f"point {pt.id} y={pt.y} out of site"


def test_lighting_every_room_gets_at_least_one_light() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["lighting"])
    room_ids = {r.id for r in project.rooms}
    lit_rooms = {p.room_id for p in mep.lighting.points}
    for rid in room_ids:
        assert rid in lit_rooms, f"room {rid} has no lighting point"


def test_ac_only_eligible_rooms() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["ac"])
    eligible = {"bedroom", "master_bedroom", "living", "study", "dining"}
    for pt in mep.ac.points:
        room = next(r for r in project.rooms if r.id == pt.room_id)
        assert room.type in eligible, f"AC placed in ineligible room type {room.type}"


def test_plumbing_advisory_route_between_wet_rooms() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["plumbing"])
    wet_rooms = [r for r in project.rooms if r.type in ("bathroom", "master_bathroom", "kitchen", "utility")]
    if len(wet_rooms) >= 2:
        assert len(mep.plumbing.routes) >= 1


def test_user_override_preserved_on_regen() -> None:
    project = _project()
    mep = MEPGenerator.generate(project)
    # Move a point and mark as override
    first_pt = mep.plumbing.points[0]
    mep2 = MEPGenerator.move_point(mep, first_pt.id, 99.0, 99.0)
    # Apply to project and regen
    project2 = project.model_copy(update={"mep_plan": mep2})
    mep3 = MEPGenerator.generate(project2, systems=["plumbing"])
    overrides = [p for p in mep3.plumbing.points if p.user_override]
    assert any(p.id == first_pt.id for p in overrides), "override point was lost on regen"
    override_pt = next(p for p in mep3.plumbing.points if p.id == first_pt.id)
    assert override_pt.x == 99.0 and override_pt.y == 99.0


def test_move_point_sets_override() -> None:
    project = _project()
    mep = MEPGenerator.generate(project)
    pt = mep.lighting.points[0]
    mep2 = MEPGenerator.move_point(mep, pt.id, 5.0, 5.0)
    moved = next(p for p in mep2.lighting.points if p.id == pt.id)
    assert moved.user_override is True
    assert moved.x == 5.0


def test_move_point_invalid_id() -> None:
    project = _project()
    mep = MEPGenerator.generate(project)
    with pytest.raises(ValueError):
        MEPGenerator.move_point(mep, "nonexistent-id", 0.0, 0.0)


def test_mark_stale() -> None:
    project = _project()
    mep = MEPGenerator.generate(project)
    assert mep.stale is False
    stale_mep = MEPGenerator.mark_stale(mep)
    assert stale_mep.stale is True


def test_generate_partial_system() -> None:
    project = _project()
    mep = MEPGenerator.generate(project, systems=["lighting"])
    assert len(mep.lighting.points) > 0
    # Plumbing should remain empty (not generated)
    assert len(mep.plumbing.points) == 0


def test_mep_confidence_scores_in_range() -> None:
    project = _project()
    mep = MEPGenerator.generate(project)
    for pt in (
        mep.plumbing.points
        + mep.electrical.points
        + mep.lighting.points
        + mep.ac.points
    ):
        assert 0.0 <= pt.confidence <= 1.0, f"point {pt.id} has invalid confidence {pt.confidence}"


def test_generated_project_still_validates() -> None:
    project = _project()
    mep = MEPGenerator.generate(project)
    project2 = project.model_copy(update={"mep_plan": mep})
    result = validate_project(project2)
    assert result.valid, result.errors
