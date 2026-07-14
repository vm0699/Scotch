"""Phase 43 Stage 43.3 — Interior generation tests.

Covers:
  - catalog-dimension resolution (spec width/depth/height overridden, no mutation of shared state)
  - deterministic furnishing: every bedroom spec produces a catalog_id-linked item
  - interior validator: bounds, overlap, door-swing collision
  - generate_room_interior: deterministic path always works (no AI key needed);
    ai/hybrid mode gracefully falls back with no key configured
  - API: POST generate, GET interior, 404s
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.architecture.furniture_defaults import ROOM_FURNITURE, get_template
from app.core.architecture.interior_designer import (
    _resolve_catalog_dims,
    furnish_room_deterministic,
    generate_room_interior,
)
from app.core.catalog import get_catalog_item
from app.core.models.project import Door, FurnitureItem, Room
from app.core.validation import validate_room_furniture
from app.main import app

client = TestClient(app)


def _bedroom(room_id: str = "r1", w: float = 12.0, d: float = 10.0) -> Room:
    return Room(id=room_id, name="Bedroom", type="bedroom", x=0.0, y=0.0, width=w, depth=d)


# ── Catalog-dimension resolution ─────────────────────────────────────────────


def test_resolve_catalog_dims_overrides_from_catalog() -> None:
    spec = next(s for s in ROOM_FURNITURE["bedroom"] if s.type == "double_bed")
    resolved = _resolve_catalog_dims(spec)
    catalog_item = get_catalog_item("bed_single_frame")
    assert resolved.width == catalog_item.footprint_w
    assert resolved.depth == catalog_item.footprint_d
    assert resolved.height == catalog_item.height


def test_resolve_catalog_dims_does_not_mutate_shared_spec() -> None:
    spec = next(s for s in ROOM_FURNITURE["bedroom"] if s.type == "double_bed")
    original_width = spec.width
    _resolve_catalog_dims(spec)
    assert spec.width == original_width  # shared ROOM_FURNITURE entry untouched


def test_resolve_catalog_dims_passthrough_when_no_catalog_id() -> None:
    spec = next(s for s in ROOM_FURNITURE["dining"] if s.type == "dining_table")
    assert spec.catalog_id is None
    resolved = _resolve_catalog_dims(spec)
    assert resolved is spec


# ── Deterministic furnishing ──────────────────────────────────────────────────


def test_bedroom_template_is_fully_catalog_backed() -> None:
    specs = get_template("bedroom", 14.0, 12.0)
    assert len(specs) >= 5
    assert all(s.catalog_id for s in specs)


def test_furnish_room_deterministic_bedroom_links_catalog_ids() -> None:
    room = _bedroom(w=14.0, d=12.0)
    items = furnish_room_deterministic(room)
    assert len(items) >= 4
    assert all(item.catalog_id for item in items)
    # every placed item's footprint matches its catalog's real dims (rotation-swapped)
    for item in items:
        catalog_item = get_catalog_item(item.catalog_id)
        expected = {round(catalog_item.footprint_w, 2), round(catalog_item.footprint_d, 2)}
        assert round(item.width, 2) in expected
        assert round(item.depth, 2) in expected


def test_furnish_room_deterministic_small_room_still_works() -> None:
    room = _bedroom(w=9.0, d=8.0)
    items = furnish_room_deterministic(room)
    assert isinstance(items, list)  # never raises — smaller room just fits fewer items


def test_furnish_room_deterministic_no_template_returns_empty() -> None:
    room = Room(id="c1", name="Corridor", type="corridor", x=0, y=0, width=4, depth=10)
    assert furnish_room_deterministic(room) == []


# ── Validator ─────────────────────────────────────────────────────────────────


def _make_project_for_validation(room: Room, doors: list[Door] | None = None):
    from app.core.architecture.sample_factory import create_sample_project

    project = create_sample_project()
    return project.model_copy(update={"rooms": [room], "doors": doors or [], "windows": []})


def test_validate_room_furniture_bounds_error() -> None:
    room = _bedroom(w=10.0, d=10.0)
    project = _make_project_for_validation(room)
    bad_item = FurnitureItem(
        id="f1", type="bed", label="Bed", room_id=room.id,
        x=8.0, y=8.0, width=5.0, depth=5.0, rotation=0, height=2.0,
    )
    result = validate_room_furniture(room, [bad_item], project)
    assert not result.valid
    assert any("outside room" in e for e in result.errors)


def test_validate_room_furniture_overlap_error() -> None:
    room = _bedroom(w=10.0, d=10.0)
    project = _make_project_for_validation(room)
    a = FurnitureItem(id="f1", type="bed", label="Bed", room_id=room.id, x=1, y=1, width=3, depth=3, rotation=0, height=2)
    b = FurnitureItem(id="f2", type="chair", label="Chair", room_id=room.id, x=2, y=2, width=2, depth=2, rotation=0, height=2)
    result = validate_room_furniture(room, [a, b], project)
    assert not result.valid
    assert any("overlaps" in e for e in result.errors)


def test_validate_room_furniture_door_swing_collision() -> None:
    room = _bedroom(w=10.0, d=10.0)
    door = Door(id="d1", room_id=room.id, wall="north", offset=3.0, width=3.0)
    project = _make_project_for_validation(room, doors=[door])
    blocking_item = FurnitureItem(
        id="f1", type="chair", label="Chair", room_id=room.id,
        x=3.5, y=0.2, width=1.0, depth=1.0, rotation=0, height=3,
    )
    result = validate_room_furniture(room, [blocking_item], project)
    assert not result.valid
    assert any("blocks a door swing" in e for e in result.errors)


def test_validate_room_furniture_clear_layout_is_valid() -> None:
    room = _bedroom(w=12.0, d=12.0)
    door = Door(id="d1", room_id=room.id, wall="north", offset=0.0, width=3.0)
    project = _make_project_for_validation(room, doors=[door])
    item = FurnitureItem(
        id="f1", type="bed", label="Bed", room_id=room.id,
        x=6.0, y=6.0, width=3.0, depth=3.0, rotation=0, height=2,
    )
    result = validate_room_furniture(room, [item], project)
    assert result.valid
    assert result.errors == []


# ── generate_room_interior orchestrator ───────────────────────────────────────


def test_generate_room_interior_deterministic_mode() -> None:
    from app.core.architecture.floorplan_generator import generate_floorplan
    from app.core.architecture.requirement_parser import parse_prompt

    project, _ = generate_floorplan(
        parse_prompt("1BHK house for a couple, 25x40 ft east-facing site, living room, 1 bedroom, 1 bathroom, kitchen")
    )
    bedroom = next(r for r in project.rooms if r.type in ("bedroom", "master_bedroom"))
    items, warnings = generate_room_interior(project, bedroom.id, mode="deterministic")
    assert len(items) > 0
    assert all(f.room_id == bedroom.id for f in items)
    assert isinstance(warnings, list)


def test_generate_room_interior_ai_mode_falls_back_without_key(monkeypatch) -> None:
    from app.config import get_settings
    from app.core.architecture.floorplan_generator import generate_floorplan
    from app.core.architecture.requirement_parser import parse_prompt

    get_settings.cache_clear()
    monkeypatch.setenv("SCOTCH_ANTHROPIC_API_KEY", "")
    project, _ = generate_floorplan(
        parse_prompt("1BHK house for a couple, 25x40 ft east-facing site, living room, 1 bedroom, 1 bathroom, kitchen")
    )
    bedroom = next(r for r in project.rooms if r.type in ("bedroom", "master_bedroom"))

    items, warnings = generate_room_interior(project, bedroom.id, mode="ai", style="modern")
    assert len(items) > 0  # deterministic fallback still furnished the room
    assert any("fallback" in w.lower() or "unavailable" in w.lower() for w in warnings)
    get_settings.cache_clear()


def test_generate_room_interior_unknown_room_raises() -> None:
    from app.core.architecture.sample_factory import create_sample_project

    project = create_sample_project()
    try:
        generate_room_interior(project, "does-not-exist")
        assert False, "expected ValueError"
    except ValueError:
        pass


# ── API ─────────────────────────────────────────────────────────────────────


def _create_test_project() -> tuple[str, str]:
    response = client.post(
        "/generate/from-prompt",
        json={
            "prompt": "1BHK house for a couple, 25x40 ft east-facing site, living room, 1 bedroom, 1 bathroom, kitchen",
            "mode": "deterministic",
        },
    )
    assert response.status_code == 200
    project = response.json()["project"]
    created = client.post("/projects", json={"name": "Interior API Test"})
    assert created.status_code == 201
    project_id = created.json()["id"]
    saved = client.patch(f"/projects/{project_id}", json={"project": project, "change_type": "generate"})
    assert saved.status_code == 200
    bedroom = next(r for r in project["rooms"] if r["type"] in ("bedroom", "master_bedroom"))
    return project_id, bedroom["id"]


def test_api_generate_interior_deterministic() -> None:
    project_id, room_id = _create_test_project()
    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/generate",
        json={"mode": "deterministic"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["furniture"]) > 0
    assert body["room_interior"]["status"] == "designed"
    assert all(f["catalog_id"] for f in body["furniture"])


def test_api_get_interior_after_generate() -> None:
    project_id, room_id = _create_test_project()
    client.post(f"/projects/{project_id}/rooms/{room_id}/interior/generate", json={"mode": "deterministic"})
    response = client.get(f"/projects/{project_id}/rooms/{room_id}/interior")
    assert response.status_code == 200
    assert len(response.json()["furniture"]) > 0


def test_api_generate_interior_unknown_room_404() -> None:
    project_id, _ = _create_test_project()
    response = client.post(f"/projects/{project_id}/rooms/nope/interior/generate", json={})
    assert response.status_code == 404


def test_api_generate_interior_unknown_project_404() -> None:
    response = client.post("/projects/does-not-exist/rooms/r1/interior/generate", json={})
    assert response.status_code == 404


def test_api_generate_interior_does_not_touch_other_rooms_furniture() -> None:
    project_id, room_id = _create_test_project()
    before = client.get(f"/projects/{project_id}").json()["project"]
    other_room_furniture_before = [f for f in before["furniture"] if f["room_id"] != room_id]

    client.post(f"/projects/{project_id}/rooms/{room_id}/interior/generate", json={"mode": "deterministic"})

    after = client.get(f"/projects/{project_id}").json()["project"]
    other_room_furniture_after = [f for f in after["furniture"] if f["room_id"] != room_id]
    assert len(other_room_furniture_after) == len(other_room_furniture_before)
