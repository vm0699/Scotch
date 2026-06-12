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
