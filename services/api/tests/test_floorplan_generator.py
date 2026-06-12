import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.validation import validate_project

TEST_PROMPTS = [
    "Design a 2BHK apartment on a 30x50 ft east-facing site with living room, "
    "kitchen, 2 bedrooms, 2 bathrooms, balcony, and parking.",
    "studio apartment 20x30",
    "3BHK villa 40x60 north-facing with dining and 3 bathrooms",
    "small cafe 25x40",
    "office layout 50x80",
]


@pytest.mark.parametrize("prompt", TEST_PROMPTS)
def test_prompt_set_generates_valid_projects(prompt: str) -> None:
    project, summary = generate_floorplan(parse_prompt(prompt))
    result = validate_project(project)
    assert result.valid, result.errors
    assert project.rooms, "generator produced no rooms"
    assert summary


@pytest.mark.parametrize("prompt", TEST_PROMPTS)
def test_rooms_stay_inside_site(prompt: str) -> None:
    project, _ = generate_floorplan(parse_prompt(prompt))
    for room in project.rooms:
        assert room.x + room.width <= project.site.width + 1e-6
        assert room.y + room.depth <= project.site.depth + 1e-6


def test_2bhk_program_contents() -> None:
    project, _ = generate_floorplan(parse_prompt(TEST_PROMPTS[0]))
    types = [r.type for r in project.rooms]
    ids = {r.id for r in project.rooms}
    assert types.count("bedroom") == 2
    assert types.count("bathroom") == 2
    assert {"parking", "living", "balcony", "kitchen", "bed-master"} <= ids


def test_zoning_living_before_bedrooms() -> None:
    project, _ = generate_floorplan(parse_prompt(TEST_PROMPTS[0]))
    rooms = {r.id: r for r in project.rooms}
    assert rooms["living"].y < rooms["bed-master"].y
    assert rooms["parking"].y == 0  # parking at the entrance
    assert rooms["kitchen"].y <= rooms["bed-master"].y  # kitchen between living and bedrooms


def test_every_non_parking_room_has_a_door() -> None:
    project, _ = generate_floorplan(parse_prompt(TEST_PROMPTS[0]))
    doored = {d.room_id for d in project.doors}
    for room in project.rooms:
        if room.type != "parking":
            assert room.id in doored


def test_assumptions_surface_as_info_warnings() -> None:
    project, _ = generate_floorplan(parse_prompt("design me a house"))
    info = [w for w in project.warnings if w.severity == "info"]
    assert any("Site size not specified" in w.message for w in info)


def test_office_falls_back_gracefully() -> None:
    project, _ = generate_floorplan(parse_prompt("office layout 50x80"))
    assert any(w.id == "warn-office-fallback" for w in project.warnings)
    assert any(r.type == "office" for r in project.rooms)


def test_tight_site_compresses_with_warning() -> None:
    project, _ = generate_floorplan(
        parse_prompt("3BHK villa on a 20x25 site with dining, parking, balcony")
    )
    result = validate_project(project)
    assert result.valid, result.errors
    assert any(w.id == "warn-depth-compressed" for w in project.warnings)


def test_cafe_program_contents() -> None:
    project, _ = generate_floorplan(parse_prompt("small cafe 25x40"))
    ids = {r.id for r in project.rooms}
    assert {"seating", "counter", "kitchen", "restroom"} <= ids
    seating = next(r for r in project.rooms if r.id == "seating")
    assert seating.y == 0  # seating at the entrance
