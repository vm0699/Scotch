import pytest
from pydantic import ValidationError

from app.core.models import ArchitectureProject, Building, Room, Site


def minimal_project(**overrides) -> dict:
    data = {
        "id": "p1",
        "name": "Test",
        "units": "feet",
        "site": {"width": 30, "depth": 50, "orientation": "east"},
        "building": {"type": "residential", "style": "modern", "floors": 1, "floor_height": 10},
    }
    data.update(overrides)
    return data


def test_minimal_project_validates() -> None:
    project = ArchitectureProject.model_validate(minimal_project())
    assert project.units == "feet"
    assert project.rooms == []
    assert project.site.orientation == "east"


def test_brief_example_shape_validates() -> None:
    project = ArchitectureProject.model_validate(
        minimal_project(
            rooms=[{"id": "living", "name": "Living", "type": "living", "x": 0, "y": 0, "width": 14, "depth": 12}],
            doors=[{"id": "d1", "room_id": "living", "wall": "north", "offset": 5, "width": 3.5}],
            windows=[{"id": "w1", "room_id": "living", "wall": "north", "offset": 9.5, "width": 4}],
            parameters=[{"key": "site_width", "label": "Site width", "value": 30, "unit": "ft", "category": "site"}],
            warnings=[{"id": "warn1", "severity": "info", "message": "note"}],
        )
    )
    assert project.rooms[0].width == 14
    assert project.doors[0].wall == "north"
    assert project.parameters[0].editable is True


@pytest.mark.parametrize("field,value", [("width", 0), ("width", -5), ("depth", 0)])
def test_site_rejects_non_positive_dimensions(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        Site.model_validate({"width": 30, "depth": 50, field: value})


def test_room_rejects_non_positive_dimensions() -> None:
    with pytest.raises(ValidationError):
        Room(id="r", name="R", type="room", x=0, y=0, width=0, depth=10)


def test_invalid_units_rejected() -> None:
    with pytest.raises(ValidationError):
        ArchitectureProject.model_validate(minimal_project(units="furlongs"))


def test_invalid_orientation_rejected() -> None:
    with pytest.raises(ValidationError):
        Site.model_validate({"width": 30, "depth": 50, "orientation": "up"})


def test_building_rejects_zero_floors() -> None:
    with pytest.raises(ValidationError):
        Building(floors=0)


def test_json_round_trip() -> None:
    project = ArchitectureProject.model_validate(minimal_project())
    again = ArchitectureProject.model_validate_json(project.model_dump_json())
    assert again == project
