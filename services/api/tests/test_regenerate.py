import pytest
from fastapi.testclient import TestClient

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.regenerate import ChangeError, ParameterChange, apply_changes
from app.core.architecture.requirement_parser import parse_prompt
from app.core.validation import validate_project
from app.main import app

client = TestClient(app)

PROMPT = (
    "Design a 2BHK apartment on a 30x50 ft east-facing site with living room, "
    "kitchen, 2 bedrooms, 2 bathrooms, balcony, and parking."
)


def _project():
    project, _ = generate_floorplan(parse_prompt(PROMPT))
    return project


def test_room_width_change_applies_and_revalidates() -> None:
    project = _project()
    updated, summary = apply_changes(
        project,
        [ParameterChange(key="room_width", value=16, target_id="living")],
    )
    living = next(r for r in updated.rooms if r.id == "living")
    assert living.width == 16
    assert validate_project(updated).valid
    assert "width → 16 ft" in summary
    # Original object untouched (deep copy).
    assert next(r for r in project.rooms if r.id == "living").width != 16


def test_room_rename_preserves_geometry() -> None:
    project = _project()
    before = next(r for r in project.rooms if r.id == "bed-master")
    updated, _ = apply_changes(
        project,
        [ParameterChange(key="room_name", value="Primary Suite", target_id="bed-master")],
    )
    after = next(r for r in updated.rooms if r.id == "bed-master")
    assert after.name == "Primary Suite"
    assert (after.width, after.depth) == (before.width, before.depth)


def test_site_shrink_repacks_inside_bounds() -> None:
    project = _project()
    updated, _ = apply_changes(
        project,
        [
            ParameterChange(key="site_width", value=22),
            ParameterChange(key="site_depth", value=40),
        ],
    )
    assert validate_project(updated).valid
    for room in updated.rooms:
        assert room.x + room.width <= 22 + 1e-6
        assert room.y + room.depth <= 40 + 1e-6
    assert updated.site.width == 22
    # Parameter list reflects the new values.
    width_param = next(p for p in updated.parameters if p.key == "site_width")
    assert width_param.value == 22


def test_orientation_and_style_changes() -> None:
    updated, _ = apply_changes(
        _project(),
        [
            ParameterChange(key="orientation", value="west"),
            ParameterChange(key="style", value="industrial"),
        ],
    )
    assert updated.site.orientation == "west"
    assert updated.building.style == "industrial"


def test_out_of_range_value_rejected() -> None:
    with pytest.raises(ChangeError):
        apply_changes(_project(), [ParameterChange(key="room_width", value=200, target_id="living")])
    with pytest.raises(ChangeError):
        apply_changes(_project(), [ParameterChange(key="site_width", value=2)])


def test_unknown_key_and_room_rejected() -> None:
    with pytest.raises(ChangeError):
        apply_changes(_project(), [ParameterChange(key="wall_color", value="red")])
    with pytest.raises(ChangeError):
        apply_changes(_project(), [ParameterChange(key="room_width", value=10, target_id="ghost")])


def test_stale_generation_warnings_recomputed() -> None:
    project = _project()
    # Force a clamp warning by widening a room beyond the site.
    updated, _ = apply_changes(
        project, [ParameterChange(key="room_width", value=35, target_id="living")]
    )
    assert any(w.id == "warn-clamp-living" for w in updated.warnings)
    # Then shrink it back: the clamp warning must disappear.
    fixed, _ = apply_changes(
        updated, [ParameterChange(key="room_width", value=14, target_id="living")]
    )
    assert not any(w.id == "warn-clamp-living" for w in fixed.warnings)


def test_regenerate_api_flow() -> None:
    generated = client.post("/generate/from-prompt", json={"prompt": PROMPT}).json()
    response = client.post(
        "/generate/regenerate",
        json={
            "project": generated["project"],
            "changes": [{"key": "room_width", "value": 15, "target_id": "kitchen"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    kitchen = next(r for r in payload["project"]["rooms"] if r["id"] == "kitchen")
    assert kitchen["width"] == 15
    assert payload["summary"].startswith("Applied 1 change")


def test_regenerate_api_rejects_bad_change() -> None:
    generated = client.post("/generate/from-prompt", json={"prompt": PROMPT}).json()
    response = client.post(
        "/generate/regenerate",
        json={
            "project": generated["project"],
            "changes": [{"key": "nonsense", "value": 1}],
        },
    )
    assert response.status_code == 422


# ── Phase 21 — Stable IDs + add/remove room ───────────────────────────────────

def test_id_stability_across_site_resize() -> None:
    """Room IDs must survive site-width and site-depth changes (21.1)."""
    project = _project()
    original_ids = {r.id for r in project.rooms}

    updated, _ = apply_changes(
        project,
        [
            ParameterChange(key="site_width", value=35),
            ParameterChange(key="site_depth", value=55),
        ],
    )
    updated_ids = {r.id for r in updated.rooms}
    assert original_ids == updated_ids, "Room IDs changed across site resize"


def test_id_stability_across_multiple_edits() -> None:
    """IDs must survive a chain of param edits (21.1)."""
    project = _project()
    original_ids = {r.id for r in project.rooms}

    step1, _ = apply_changes(project, [ParameterChange(key="room_width", value=16, target_id="living")])
    step2, _ = apply_changes(step1, [ParameterChange(key="site_width", value=28)])
    final_ids = {r.id for r in step2.rooms}
    assert original_ids == final_ids


def test_add_bedroom_increases_room_count() -> None:
    """add_room → bedroom results in one more bedroom (21.2)."""
    project = _project()
    bed_count_before = sum(1 for r in project.rooms if r.type == "bedroom")

    updated, summary = apply_changes(
        project, [ParameterChange(key="add_room", value="bedroom")]
    )
    bed_count_after = sum(1 for r in updated.rooms if r.type == "bedroom")
    assert bed_count_after == bed_count_before + 1
    assert validate_project(updated).valid
    assert "added" in summary.lower()


def test_add_room_generates_stable_id() -> None:
    """New bedroom gets 'bed-3' (there are already bed-master and bed-2) (21.2)."""
    project = _project()
    updated, _ = apply_changes(
        project, [ParameterChange(key="add_room", value="bedroom")]
    )
    room_ids = [r.id for r in updated.rooms]
    assert "bed-3" in room_ids


def test_add_bathroom_stable_id() -> None:
    """New bathroom gets next sequential bath-N id (21.2)."""
    project = _project()
    bath_ids_before = {r.id for r in project.rooms if r.type == "bathroom"}
    updated, _ = apply_changes(
        project, [ParameterChange(key="add_room", value="bathroom")]
    )
    bath_ids_after = {r.id for r in updated.rooms if r.type == "bathroom"}
    new_ids = bath_ids_after - bath_ids_before
    assert len(new_ids) == 1
    new_id = next(iter(new_ids))
    assert new_id.startswith("bath-")


def test_add_room_invalid_type_rejected() -> None:
    """Unknown room type in add_room raises ChangeError (21.2)."""
    with pytest.raises(ChangeError):
        apply_changes(_project(), [ParameterChange(key="add_room", value="dungeon")])


def test_remove_room_decreases_count() -> None:
    """remove_room → layout shrinks by one room (21.2)."""
    project = _project()
    before_count = len(project.rooms)

    updated, summary = apply_changes(
        project, [ParameterChange(key="remove_room", target_id="balcony", value="")]
    )
    assert len(updated.rooms) == before_count - 1
    assert all(r.id != "balcony" for r in updated.rooms)
    assert validate_project(updated).valid
    assert "removed" in summary.lower()


def test_remove_last_room_rejected() -> None:
    """Cannot remove the last remaining room (21.2)."""
    project = _project()
    # Remove rooms one by one until only one remains.
    intermediate = project
    for room in project.rooms[1:]:
        intermediate, _ = apply_changes(
            intermediate, [ParameterChange(key="remove_room", value="", target_id=room.id)]
        )
    assert len(intermediate.rooms) == 1
    # Now attempting to remove the last room must raise.
    last_id = intermediate.rooms[0].id
    with pytest.raises(ChangeError, match="last room"):
        apply_changes(intermediate, [ParameterChange(key="remove_room", value="", target_id=last_id)])


def test_remove_unknown_room_rejected() -> None:
    """remove_room with unknown target_id raises ChangeError (21.2)."""
    with pytest.raises(ChangeError):
        apply_changes(_project(), [ParameterChange(key="remove_room", value="", target_id="ghost-room")])


def test_add_then_remove_round_trip() -> None:
    """Add a room then remove it — final state matches original room count (21.2)."""
    project = _project()
    original_ids = {r.id for r in project.rooms}

    with_new, _ = apply_changes(project, [ParameterChange(key="add_room", value="study")])
    new_id = next(r.id for r in with_new.rooms if r.id not in original_ids)

    restored, _ = apply_changes(with_new, [ParameterChange(key="remove_room", value="", target_id=new_id)])
    assert {r.id for r in restored.rooms} == original_ids


def test_program_endpoint_returns_correct_structure() -> None:
    """GET /projects/{id}/program returns the program table (21.3)."""
    # Create + generate a project.
    created = client.post("/projects", json={"name": "Program Test"}).json()
    pid = created["id"]
    generated = client.post("/generate/from-prompt", json={"prompt": PROMPT}).json()
    client.patch(
        f"/projects/{pid}",
        json={"project": generated["project"], "change_type": "generate"},
    )

    resp = client.get(f"/projects/{pid}/program")
    assert resp.status_code == 200
    data = resp.json()

    assert "site" in data
    assert data["site"]["width"] > 0
    assert data["site"]["depth"] > 0
    assert "rooms" in data
    assert len(data["rooms"]) > 0
    for room in data["rooms"]:
        assert "id" in room
        assert "name" in room
        assert "width" in room
        assert "depth" in room
        assert room["area"] == pytest.approx(room["width"] * room["depth"], rel=1e-3)
    assert "totals" in data
    expected_area = sum(r["area"] for r in data["rooms"])
    assert data["totals"]["built_up_area"] == pytest.approx(expected_area, rel=1e-2)
    assert data["totals"]["room_count"] == len(data["rooms"])
    assert 0 < data["totals"]["coverage_pct"] <= 100


def test_program_endpoint_404_on_missing_project() -> None:
    """GET /projects/nonexistent/program → 404."""
    resp = client.get("/projects/nonexistent-project-id/program")
    assert resp.status_code == 404


def test_program_endpoint_409_before_generation() -> None:
    """GET /projects/{id}/program → 409 when no design generated yet."""
    created = client.post("/projects", json={"name": "Empty Program Test"}).json()
    resp = client.get(f"/projects/{created['id']}/program")
    assert resp.status_code == 409


# ── Phase 22 — multi-floor regenerate + room_level ────────────────────────────


def test_floors_change_rebuilds_levels() -> None:
    """Changing floors → project.levels list matches new floor count (22.2)."""
    project = _project()
    updated, _ = apply_changes(project, [ParameterChange(key="floors", value=2)])
    assert updated.building.floors == 2
    assert len(updated.levels) == 2
    assert updated.levels[0].index == 0
    assert updated.levels[1].index == 1


def test_floors_change_adds_stair_rooms() -> None:
    """When floors becomes 2, stair rooms are added (22.2)."""
    project = _project()
    updated, _ = apply_changes(project, [ParameterChange(key="floors", value=2)])
    stair_ids = {r.id for r in updated.rooms if r.type == "stair"}
    assert len(stair_ids) == 2, f"Expected 2 stair rooms, got {stair_ids}"


def test_floors_decrease_removes_stair_rooms() -> None:
    """Decreasing floors back to 1 removes stair rooms (22.2)."""
    project = _project()
    two_floors, _ = apply_changes(project, [ParameterChange(key="floors", value=2)])
    back_to_one, _ = apply_changes(two_floors, [ParameterChange(key="floors", value=1)])
    stair_rooms = [r for r in back_to_one.rooms if r.type == "stair"]
    assert stair_rooms == [], "Stair rooms must be removed when back to 1 floor"
    assert back_to_one.building.floors == 1
    assert len(back_to_one.levels) == 1


def test_room_level_change_moves_room() -> None:
    """room_level change key moves a room to a different floor (22.2)."""
    project = _project()
    # First go to 2 floors so level 1 is valid
    two_floors, _ = apply_changes(project, [ParameterChange(key="floors", value=2)])
    living = next(r for r in two_floors.rooms if r.type == "living")
    # Move living room to floor 1
    updated, _ = apply_changes(
        two_floors, [ParameterChange(key="room_level", value=1, target_id=living.id)]
    )
    updated_living = next(r for r in updated.rooms if r.id == living.id)
    assert updated_living.level == 1


def test_room_level_invalid_target_rejected() -> None:
    """room_level with unknown room id raises ChangeError (22.2)."""
    project = _project()
    with pytest.raises(ChangeError):
        apply_changes(project, [ParameterChange(key="room_level", value=0, target_id="ghost-room")])


def test_room_level_out_of_range_rejected() -> None:
    """room_level beyond building.floors - 1 raises ChangeError (22.2)."""
    project = _project()
    room_id = project.rooms[0].id
    with pytest.raises(ChangeError):
        apply_changes(project, [ParameterChange(key="room_level", value=5, target_id=room_id)])
