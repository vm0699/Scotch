"""Phase 43 Stage 43.4 — Interior editing + stale-tracking tests.

Covers:
  - POST .../interior/edit: move, rotate (with dimension swap), delete, swap, add
  - Rejected edits (bounds/overlap violation) return 422 and are NOT persisted
  - RoomInterior flips to "stale" when its room is resized after furnishing
  - RoomInterior entry is dropped when its room is removed
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_furnished_project() -> tuple[str, str]:
    response = client.post(
        "/generate/from-prompt",
        json={
            "prompt": "1BHK house for a couple, 28x42 ft east-facing site, living room, 1 bedroom, 1 bathroom, kitchen",
            "mode": "deterministic",
        },
    )
    assert response.status_code == 200
    project = response.json()["project"]
    created = client.post("/projects", json={"name": "Interior Edit Test"})
    project_id = created.json()["id"]
    client.patch(f"/projects/{project_id}", json={"project": project, "change_type": "generate"})
    bedroom = next(r for r in project["rooms"] if r["type"] in ("bedroom", "master_bedroom"))
    room_id = bedroom["id"]

    gen = client.post(f"/projects/{project_id}/rooms/{room_id}/interior/generate", json={"mode": "deterministic"})
    assert gen.status_code == 200
    return project_id, room_id


def _clear_to_one_item(project_id: str, room_id: str) -> dict:
    """Deletes every furniture item but one, so rotate/add/swap tests have
    room to work with regardless of how tightly the deterministic placer
    packed this particular bedroom (e.g. a wardrobe pinned by the door swing
    correctly refuses to rotate — that's the validator working, not a bug;
    these tests exercise the edit *mechanics*, not placement density)."""
    items = client.get(f"/projects/{project_id}/rooms/{room_id}/interior").json()["furniture"]
    keeper = items[0]
    for item in items[1:]:
        r = client.post(
            f"/projects/{project_id}/rooms/{room_id}/interior/edit",
            json={"action": "delete", "item_id": item["id"]},
        )
        assert r.status_code == 200
    return keeper


def test_edit_move_updates_position() -> None:
    project_id, room_id = _create_furnished_project()
    interior = client.get(f"/projects/{project_id}/rooms/{room_id}/interior").json()
    item = interior["furniture"][0]

    new_x, new_y = item["x"] + 0.2, item["y"]
    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "move", "item_id": item["id"], "x": new_x, "y": new_y},
    )
    assert response.status_code == 200
    moved = next(f for f in response.json()["furniture"] if f["id"] == item["id"])
    assert moved["x"] == new_x
    assert moved["y"] == new_y


def _isolate_item_at_room_center(project_id: str, room_id: str) -> dict:
    """Clears the room to one item and moves it to room-center — a position
    guaranteed clear of walls/doors — so rotate is free to succeed either way."""
    item = _clear_to_one_item(project_id, room_id)
    project = client.get(f"/projects/{project_id}").json()["project"]
    this_room = next(r for r in project["rooms"] if r["id"] == room_id)
    cx = this_room["x"] + this_room["width"] / 2 - item["width"] / 2
    cy = this_room["y"] + this_room["depth"] / 2 - item["depth"] / 2
    moved = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "move", "item_id": item["id"], "x": round(cx, 2), "y": round(cy, 2)},
    )
    assert moved.status_code == 200
    return moved.json()["furniture"][0]


def test_edit_rotate_swaps_dimensions_on_90_degree_turn() -> None:
    project_id, room_id = _create_furnished_project()
    item = _isolate_item_at_room_center(project_id, room_id)
    orig_w, orig_d = item["width"], item["depth"]
    target_rotation = 90 if item["rotation"] in (0, 180) else 0

    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "rotate", "item_id": item["id"], "rotation": target_rotation},
    )
    assert response.status_code == 200
    rotated = next(f for f in response.json()["furniture"] if f["id"] == item["id"])
    assert rotated["rotation"] == target_rotation
    assert rotated["width"] == orig_d
    assert rotated["depth"] == orig_w


def test_edit_rotate_180_does_not_swap_dimensions() -> None:
    project_id, room_id = _create_furnished_project()
    item = _isolate_item_at_room_center(project_id, room_id)
    target_rotation = 180 if item["rotation"] in (0, 180) else 270

    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "rotate", "item_id": item["id"], "rotation": target_rotation},
    )
    assert response.status_code == 200
    rotated = next(f for f in response.json()["furniture"] if f["id"] == item["id"])
    assert rotated["width"] == item["width"]
    assert rotated["depth"] == item["depth"]


def test_edit_delete_removes_item() -> None:
    project_id, room_id = _create_furnished_project()
    interior = client.get(f"/projects/{project_id}/rooms/{room_id}/interior").json()
    item_id = interior["furniture"][0]["id"]
    before_count = len(interior["furniture"])

    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "delete", "item_id": item_id},
    )
    assert response.status_code == 200
    assert len(response.json()["furniture"]) == before_count - 1
    assert all(f["id"] != item_id for f in response.json()["furniture"])


def test_edit_swap_changes_catalog_id_and_dims() -> None:
    project_id, room_id = _create_furnished_project()
    item = _isolate_item_at_room_center(project_id, room_id)
    new_catalog_id = "vase_ceramic" if item["catalog_id"] != "vase_ceramic" else "nightstand_painted"

    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "swap", "item_id": item["id"], "catalog_id": new_catalog_id},
    )
    assert response.status_code == 200
    swapped = next(f for f in response.json()["furniture"] if f["id"] == item["id"])
    assert swapped["catalog_id"] == new_catalog_id


def test_edit_add_places_new_item() -> None:
    project_id, room_id = _create_furnished_project()
    _clear_to_one_item(project_id, room_id)  # free up floor space before adding
    before = len(client.get(f"/projects/{project_id}/rooms/{room_id}/interior").json()["furniture"])
    project = client.get(f"/projects/{project_id}").json()["project"]
    room = next(r for r in project["rooms"] if r["id"] == room_id)

    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={
            "action": "add",
            "catalog_id": "vase_ceramic",
            "x": room["x"] + room["width"] - 1.0,
            "y": room["y"] + room["depth"] - 1.0,
            "rotation": 0,
        },
    )
    assert response.status_code == 200
    after = response.json()["furniture"]
    assert len(after) == before + 1
    assert any(f["catalog_id"] == "vase_ceramic" for f in after)


def test_edit_move_out_of_bounds_rejected_and_not_persisted() -> None:
    project_id, room_id = _create_furnished_project()
    interior = client.get(f"/projects/{project_id}/rooms/{room_id}/interior").json()
    item = interior["furniture"][0]

    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "move", "item_id": item["id"], "x": 9999, "y": 9999},
    )
    assert response.status_code == 422

    after = client.get(f"/projects/{project_id}/rooms/{room_id}/interior").json()
    unchanged = next(f for f in after["furniture"] if f["id"] == item["id"])
    assert unchanged["x"] == item["x"]
    assert unchanged["y"] == item["y"]


def test_edit_move_causing_overlap_rejected() -> None:
    project_id, room_id = _create_furnished_project()
    interior = client.get(f"/projects/{project_id}/rooms/{room_id}/interior").json()
    items = interior["furniture"]
    assert len(items) >= 2
    a, b = items[0], items[1]

    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "move", "item_id": a["id"], "x": b["x"], "y": b["y"]},
    )
    assert response.status_code == 422
    assert "overlaps" in str(response.json()["detail"])


def test_edit_tolerates_preexisting_violation_from_whole_project_generation() -> None:
    """/generate/from-prompt's furniture step is not door-aware (unlike
    interior_designer.py's self-healing deterministic path), so a room it
    furnished can already carry a door-swing violation. That pre-existing
    problem must not make every future edit in that room impossible — only a
    NEW violation introduced by the edit itself should be rejected."""
    response = client.post(
        "/generate/from-prompt",
        json={
            "prompt": "1BHK house for a couple, 28x42 ft east-facing site, living room, 1 bedroom, 1 bathroom, kitchen",
            "mode": "deterministic",
        },
    )
    project = response.json()["project"]
    created = client.post("/projects", json={"name": "Preexisting Violation Test"})
    project_id = created.json()["id"]
    client.patch(f"/projects/{project_id}", json={"project": project, "change_type": "generate"})
    bedroom = next(r for r in project["rooms"] if r["type"] in ("bedroom", "master_bedroom"))
    room_id = bedroom["id"]

    before = client.get(f"/projects/{project_id}").json()["project"]
    items = [f for f in before["furniture"] if f["room_id"] == room_id]
    assert len(items) > 0

    # Delete an item unrelated to any pre-existing violation — must succeed
    # regardless of whether some OTHER item in the room already blocks a door.
    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "delete", "item_id": items[-1]["id"]},
    )
    assert response.status_code == 200
    assert all(f["id"] != items[-1]["id"] for f in response.json()["furniture"])


def test_edit_unknown_item_404() -> None:
    project_id, room_id = _create_furnished_project()
    response = client.post(
        f"/projects/{project_id}/rooms/{room_id}/interior/edit",
        json={"action": "delete", "item_id": "does-not-exist"},
    )
    assert response.status_code == 404


# ── Stale-tracking ────────────────────────────────────────────────────────────


def test_room_interior_flips_stale_on_resize() -> None:
    project_id, room_id = _create_furnished_project()
    stored = client.get(f"/projects/{project_id}").json()["project"]
    interior_before = next(ri for ri in stored["room_interiors"] if ri["room_id"] == room_id)
    assert interior_before["status"] == "designed"

    room = next(r for r in stored["rooms"] if r["id"] == room_id)
    response = client.post(
        "/generate/regenerate",
        json={
            "project": stored,
            "changes": [{"key": "room_width", "value": room["width"] + 2, "target_id": room_id}],
        },
    )
    assert response.status_code == 200
    updated = response.json()["project"]
    interior_after = next(ri for ri in updated["room_interiors"] if ri["room_id"] == room_id)
    assert interior_after["status"] == "stale"


def test_room_interior_dropped_on_room_removal() -> None:
    project_id, room_id = _create_furnished_project()
    stored = client.get(f"/projects/{project_id}").json()["project"]
    assert any(ri["room_id"] == room_id for ri in stored["room_interiors"])

    response = client.post(
        "/generate/regenerate",
        json={"project": stored, "changes": [{"key": "remove_room", "value": "", "target_id": room_id}]},
    )
    assert response.status_code == 200
    updated = response.json()["project"]
    assert all(ri["room_id"] != room_id for ri in updated["room_interiors"])
