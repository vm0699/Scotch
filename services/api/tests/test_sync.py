"""Phase 25.9 — Sync protocol tests.

Covers:
- SyncContract projection (pull) — correct fields, correct room count
- push_sync round-trip — updated dimensions reflected in returned project
- push_sync ID stability — no duplicate rooms created
- push_sync added rooms — new IDs appear in diff.added and in returned project
- push_sync flagged rooms — IDs in Scotch but absent from payload → diff.flagged
- push_sync conflicts — large delta (> CONFLICT_TOLERANCE) flagged in diff.conflicts
- push_sync min-dimension guard — room below MIN_ROOM_DIM raises ValueError
- push_sync validator gate — merged model that fails layout validation → 422
- GET /projects/{id}/sync — returns SyncContract with correct rooms
- POST /projects/{id}/sync — round-trip: resize → GET → dimensions match
- POST /projects/{id}/sync — ID stability: no duplicate rooms
- POST /projects/{id}/sync — validator gate: sub-MIN_ROOM_DIM rejected (422)
- POST /projects/{id}/sync — 404 for missing project
- POST /projects/{id}/sync — 409 for project with no design
- POST /projects/{id}/sync — auto-snapshot created with change_type="sync"
- POST /projects/{id}/sync — source field stored in version summary
- conflict handling — delta > 0.5 ft flagged but still applied
- GET /projects/{id}/sync — 404 for missing project
- GET /projects/{id}/sync — 409 for project with no design
"""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.sample_factory import create_sample_project
from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.core.sync.engine import project_to_sync_contract, push_sync
from app.core.sync.models import (
    CONFLICT_TOLERANCE,
    MIN_ROOM_DIM,
    SyncPayload,
    SyncRoom,
)
from app.main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def stored_project(client: TestClient):
    """A project that has a generated design."""
    sample = client.get("/projects/sample").json()
    proj = client.post("/projects", json={"name": "Sync Test House"}).json()
    client.patch(f"/projects/{proj['id']}", json={"project": sample})
    return proj["id"], sample


@pytest.fixture
def sample():
    return create_sample_project()


# ── Engine unit tests ─────────────────────────────────────────────────────────


def test_project_to_sync_contract_room_count(sample):
    contract = project_to_sync_contract(sample, "proj-1")
    assert len(contract.rooms) == len(sample.rooms)


def test_project_to_sync_contract_fields(sample):
    contract = project_to_sync_contract(sample, "proj-1", version_ts="2026-01-01T00:00:00")
    room = contract.rooms[0]
    assert room.id
    assert room.name
    assert room.width > 0
    assert room.depth > 0
    assert contract.project_id == "proj-1"
    assert contract.source_version == "2026-01-01T00:00:00"


def test_push_sync_update_dimensions(sample):
    """Resizing a room via SyncPayload updates it in the returned project."""
    first_room = sample.rooms[0]
    new_width = first_room.width + 2.0
    new_depth = first_room.depth + 2.0

    payload = SyncPayload(
        rooms=[
            SyncRoom(
                id=first_room.id,
                name=first_room.name,
                type=first_room.type,
                x=first_room.x,
                y=first_room.y,
                width=new_width,
                depth=new_depth,
                level=first_room.level,
            )
        ],
        source="sketchup",
    )
    updated, diff = push_sync(sample, payload)
    updated_room = next(r for r in updated.rooms if r.id == first_room.id)
    assert updated_room.width == new_width
    assert updated_room.depth == new_depth
    assert first_room.id in diff.updated


def test_push_sync_id_stability(sample):
    """Sync does not create duplicate rooms — IDs remain unique."""
    # Send all existing rooms back unchanged
    payload = SyncPayload(
        rooms=[
            SyncRoom(
                id=r.id, name=r.name, type=r.type,
                x=r.x, y=r.y, width=r.width, depth=r.depth, level=r.level,
            )
            for r in sample.rooms
        ],
        source="sketchup",
    )
    updated, _diff = push_sync(sample, payload)
    ids = [r.id for r in updated.rooms]
    assert len(ids) == len(set(ids)), "Duplicate room IDs after sync"


def test_push_sync_adds_new_rooms(sample):
    """IDs not in the model are added as new rooms."""
    new_id = "new-study-99"
    payload = SyncPayload(
        rooms=[
            SyncRoom(
                id=new_id, name="Study", type="study",
                x=0, y=0, width=8, depth=8, level=0,
            )
        ],
        source="sketchup",
    )
    updated, diff = push_sync(sample, payload)
    assert new_id in diff.added
    assert any(r.id == new_id for r in updated.rooms)


def test_push_sync_flags_absent_rooms(sample):
    """Rooms in Scotch but absent from the payload are flagged, not deleted."""
    first_room = sample.rooms[0]
    payload = SyncPayload(
        rooms=[
            SyncRoom(
                id=first_room.id, name=first_room.name, type=first_room.type,
                x=first_room.x, y=first_room.y,
                width=first_room.width, depth=first_room.depth,
                level=first_room.level,
            )
        ],
        source="sketchup",
    )
    updated, diff = push_sync(sample, payload)
    # Rooms beyond the first should be flagged
    expected_flagged = {r.id for r in sample.rooms if r.id != first_room.id}
    assert expected_flagged == set(diff.flagged)
    # All original rooms still present
    assert len(updated.rooms) >= len(sample.rooms)


def test_push_sync_conflict_detection(sample):
    """A dimensional change > CONFLICT_TOLERANCE is flagged in diff.conflicts."""
    first_room = sample.rooms[0]
    big_change = first_room.width + CONFLICT_TOLERANCE + 1.0  # well above threshold
    payload = SyncPayload(
        rooms=[
            SyncRoom(
                id=first_room.id, name=first_room.name, type=first_room.type,
                x=first_room.x, y=first_room.y,
                width=big_change, depth=first_room.depth,
                level=first_room.level,
            )
        ],
        source="sketchup",
    )
    _updated, diff = push_sync(sample, payload)
    assert len(diff.conflicts) >= 1
    conflict = next(c for c in diff.conflicts if c.room_id == first_room.id)
    assert conflict.field == "width"
    assert conflict.delta > CONFLICT_TOLERANCE


def test_push_sync_conflict_still_applied(sample):
    """Conflict is applied even though it's flagged — version is the safety net."""
    first_room = sample.rooms[0]
    big_width = first_room.width + CONFLICT_TOLERANCE + 1.0
    payload = SyncPayload(
        rooms=[
            SyncRoom(
                id=first_room.id, name=first_room.name, type=first_room.type,
                x=first_room.x, y=first_room.y,
                width=big_width, depth=first_room.depth,
                level=first_room.level,
            )
        ],
        source="sketchup",
    )
    updated, diff = push_sync(sample, payload)
    assert len(diff.conflicts) >= 1
    updated_room = next(r for r in updated.rooms if r.id == first_room.id)
    assert updated_room.width == big_width  # change IS applied


def test_push_sync_min_dim_guard(sample):
    """Room below MIN_ROOM_DIM raises ValueError before touching the model."""
    payload = SyncPayload(
        rooms=[
            SyncRoom(
                id="tiny-room", name="Tiny", type="storage",
                x=0, y=0,
                width=MIN_ROOM_DIM - 0.1,  # too small
                depth=MIN_ROOM_DIM,
                level=0,
            )
        ],
        source="sketchup",
    )
    with pytest.raises(ValueError, match="minimum"):
        push_sync(sample, payload)


# ── API integration tests ─────────────────────────────────────────────────────


def test_pull_sync_returns_contract(client, stored_project):
    project_id, sample = stored_project
    resp = client.get(f"/projects/{project_id}/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project_id
    assert isinstance(data["rooms"], list)
    assert len(data["rooms"]) == len(sample["rooms"])


def test_pull_sync_room_fields(client, stored_project):
    project_id, _sample = stored_project
    resp = client.get(f"/projects/{project_id}/sync")
    room = resp.json()["rooms"][0]
    for field in ("id", "name", "type", "x", "y", "width", "depth", "level"):
        assert field in room, f"Missing field: {field}"


def test_pull_sync_404(client):
    resp = client.get("/projects/no-such-project/sync")
    assert resp.status_code == 404


def test_pull_sync_409_no_design(client):
    proj = client.post("/projects", json={"name": "Empty"}).json()
    resp = client.get(f"/projects/{proj['id']}/sync")
    assert resp.status_code == 409


def test_push_sync_round_trip_resize(client, stored_project):
    """Resize a room via push, then pull and confirm new dimensions."""
    project_id, sample = stored_project
    first_room = sample["rooms"][0]
    new_width = first_room["width"] + 2.0
    new_depth = first_room["depth"] + 2.0

    payload = {
        "rooms": [
            {
                "id": first_room["id"],
                "name": first_room["name"],
                "type": first_room["type"],
                "x": first_room["x"],
                "y": first_room["y"],
                "width": new_width,
                "depth": new_depth,
                "level": first_room.get("level", 0),
            }
        ],
        "source": "sketchup",
    }
    push_resp = client.post(f"/projects/{project_id}/sync", json=payload)
    assert push_resp.status_code == 200
    diff = push_resp.json()
    assert first_room["id"] in diff["updated"]

    # Pull and confirm dimensions in the canonical model
    pull_resp = client.get(f"/projects/{project_id}/sync")
    assert pull_resp.status_code == 200
    rooms = {r["id"]: r for r in pull_resp.json()["rooms"]}
    assert rooms[first_room["id"]]["width"] == new_width
    assert rooms[first_room["id"]]["depth"] == new_depth


def test_push_sync_no_duplicate_rooms(client, stored_project):
    """Pushing all rooms back unchanged must not create duplicates."""
    project_id, sample = stored_project
    payload = {
        "rooms": [
            {
                "id": r["id"], "name": r["name"], "type": r["type"],
                "x": r["x"], "y": r["y"],
                "width": r["width"], "depth": r["depth"],
                "level": r.get("level", 0),
            }
            for r in sample["rooms"]
        ],
        "source": "sketchup",
    }
    resp = client.post(f"/projects/{project_id}/sync", json=payload)
    assert resp.status_code == 200
    project = resp.json()["project"]
    ids = [r["id"] for r in project["rooms"]]
    assert len(ids) == len(set(ids))


def test_push_sync_validator_gate_sub_min_dim(client, stored_project):
    """Room with dimension below MIN_ROOM_DIM is rejected with 422."""
    project_id, _sample = stored_project
    payload = {
        "rooms": [
            {
                "id": "bad-room", "name": "Too Small", "type": "storage",
                "x": 0, "y": 0,
                "width": MIN_ROOM_DIM - 0.1,
                "depth": MIN_ROOM_DIM,
                "level": 0,
            }
        ],
        "source": "sketchup",
    }
    resp = client.post(f"/projects/{project_id}/sync", json=payload)
    assert resp.status_code == 422


def test_push_sync_404(client):
    payload = {"rooms": [], "source": "sketchup"}
    resp = client.post("/projects/no-such/sync", json=payload)
    assert resp.status_code == 404


def test_push_sync_409_no_design(client):
    proj = client.post("/projects", json={"name": "Empty"}).json()
    payload = {"rooms": [], "source": "sketchup"}
    resp = client.post(f"/projects/{proj['id']}/sync", json=payload)
    assert resp.status_code == 409


def test_push_sync_auto_snapshot(client, stored_project):
    """A sync push creates a version snapshot with change_type='sync'."""
    project_id, sample = stored_project
    first_room = sample["rooms"][0]
    payload = {
        "rooms": [
            {
                "id": first_room["id"], "name": first_room["name"],
                "type": first_room["type"],
                "x": first_room["x"], "y": first_room["y"],
                "width": first_room["width"] + 2.0, "depth": first_room["depth"],
                "level": first_room.get("level", 0),
            }
        ],
        "source": "sketchup",
    }
    client.post(f"/projects/{project_id}/sync", json=payload)
    versions = client.get(f"/projects/{project_id}/versions").json()
    sync_versions = [v for v in versions if v["change_type"] == "sync"]
    assert len(sync_versions) >= 1


def test_push_sync_version_summary_contains_source(client, stored_project):
    """Version summary mentions the source tool."""
    project_id, sample = stored_project
    first_room = sample["rooms"][0]
    payload = {
        "rooms": [
            {
                "id": first_room["id"], "name": first_room["name"],
                "type": first_room["type"],
                "x": first_room["x"], "y": first_room["y"],
                "width": first_room["width"] + 2.0, "depth": first_room["depth"],
                "level": first_room.get("level", 0),
            }
        ],
        "source": "sketchup",
    }
    client.post(f"/projects/{project_id}/sync", json=payload)
    versions = client.get(f"/projects/{project_id}/versions").json()
    sync_v = next((v for v in versions if v["change_type"] == "sync"), None)
    assert sync_v is not None
    assert "sketchup" in sync_v["summary"].lower()


def test_push_sync_conflict_api_flagged(client, stored_project):
    """API returns conflicts array when dimension changes exceed tolerance."""
    project_id, sample = stored_project
    first_room = sample["rooms"][0]
    big_width = first_room["width"] + CONFLICT_TOLERANCE + 2.0
    payload = {
        "rooms": [
            {
                "id": first_room["id"], "name": first_room["name"],
                "type": first_room["type"],
                "x": first_room["x"], "y": first_room["y"],
                "width": big_width, "depth": first_room["depth"],
                "level": first_room.get("level", 0),
            }
        ],
        "source": "sketchup",
    }
    resp = client.post(f"/projects/{project_id}/sync", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["conflicts"]) >= 1
    conflict = data["conflicts"][0]
    assert conflict["field"] == "width"
    assert conflict["delta"] > CONFLICT_TOLERANCE
