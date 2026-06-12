from app.core.architecture.sample_factory import create_sample_project
from app.core.models import Door, Room
from app.core.validation import validate_project


def test_sample_project_is_valid() -> None:
    result = validate_project(create_sample_project())
    assert result.valid
    assert result.errors == []


def test_sample_project_gets_open_area_advisory() -> None:
    # The sample intentionally leaves the rear ~45% of the plot unbuilt.
    result = validate_project(create_sample_project())
    assert any(w.id == "warn-open-area" and w.severity == "info" for w in result.warnings)


def test_duplicate_room_ids_fail() -> None:
    project = create_sample_project()
    project.rooms.append(project.rooms[0].model_copy())
    result = validate_project(project)
    assert not result.valid
    assert any("Duplicate room id" in e for e in result.errors)


def test_room_outside_site_fails() -> None:
    project = create_sample_project()
    project.rooms.append(
        Room(id="shed", name="Shed", type="storage", x=25, y=45, width=10, depth=10)
    )
    result = validate_project(project)
    assert not result.valid
    assert any("outside" in e for e in result.errors)


def test_bad_level_reference_fails() -> None:
    project = create_sample_project()
    project.rooms[0].level = 3  # building has 1 floor
    result = validate_project(project)
    assert not result.valid
    assert any("level 3" in e for e in result.errors)


def test_door_to_unknown_room_fails() -> None:
    project = create_sample_project()
    project.doors.append(Door(id="d-ghost", room_id="nope", wall="north", offset=1, width=3))
    result = validate_project(project)
    assert not result.valid
    assert any("unknown room" in e for e in result.errors)


def test_oversized_opening_warns_but_passes() -> None:
    project = create_sample_project()
    project.doors.append(Door(id="d-wide", room_id="bath-1", wall="north", offset=4, width=4))
    result = validate_project(project)
    assert result.valid
    assert any(w.id == "warn-fit-d-wide" for w in result.warnings)


def test_overlapping_rooms_warn() -> None:
    project = create_sample_project()
    project.rooms.append(
        Room(id="overlap", name="Overlap", type="storage", x=11, y=1, width=5, depth=5)
    )
    result = validate_project(project)
    assert any(w.id.startswith("warn-overlap-") for w in result.warnings)
