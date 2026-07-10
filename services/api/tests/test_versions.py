"""Tests for Phase 19 — Versioning & History.

Covers:
- Auto-snapshot created when PATCH includes change_type
- No snapshot created when change_type is omitted
- Snapshot count grows monotonically per change
- list_versions returns reverse-chronological order
- get_version returns full snapshot
- restore writes snapshot as active project and appends a 'restore' version
- restore never destroys history
- diff endpoint detects added / removed / resized rooms
- All four /versions API endpoints respond correctly
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.models import ArchitectureProject
from app.core.storage import get_project_store
from app.core.storage.local_store import LocalProjectStore

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _minimal_project(n_rooms: int = 2) -> dict:
    rooms = []
    for i in range(n_rooms):
        rooms.append({
            "id": f"room-{i}",
            "name": f"Room {i}",
            "type": "bedroom",
            "x": i * 12,
            "y": 0,
            "width": 10,
            "depth": 12,
            "level": 0,
        })
    return {
        "id": "proj-test",
        "name": "Test",
        "units": "feet",
        "site": {"width": 40, "depth": 30, "orientation": "north"},
        "building": {"type": "residential", "style": "modern", "floors": 1, "floor_height": 9.0},
        "levels": [{"index": 0, "name": "Ground", "elevation": 0.0}],
        "rooms": rooms,
        "walls": [],
        "doors": [],
        "windows": [],
        "materials": [],
        "parameters": [],
        "notes": [],
        "warnings": [],
    }


@pytest.fixture()
def stored_project_id() -> str:
    resp = client.post("/projects", json={"name": "History Test"})
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Storage-level tests ───────────────────────────────────────────────────────

def test_no_version_without_change_type(stored_project_id: str):
    """PATCH without change_type must not create a version sidecar."""
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": _minimal_project()},
    )
    resp = client.get(f"/projects/{stored_project_id}/versions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_auto_version_on_generate(stored_project_id: str):
    """PATCH with change_type='generate' creates one version."""
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": _minimal_project(), "change_type": "generate"},
    )
    resp = client.get(f"/projects/{stored_project_id}/versions")
    assert resp.status_code == 200
    versions = resp.json()
    assert len(versions) == 1
    assert versions[0]["change_type"] == "generate"


def test_version_summary_is_populated(stored_project_id: str):
    """Auto-generated summary is non-empty."""
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": _minimal_project(), "change_type": "generate"},
    )
    versions = client.get(f"/projects/{stored_project_id}/versions").json()
    assert versions[0]["summary"]


def test_custom_summary_stored(stored_project_id: str):
    """Caller-supplied version_summary is persisted verbatim."""
    client.patch(
        f"/projects/{stored_project_id}",
        json={
            "project": _minimal_project(),
            "change_type": "edit",
            "version_summary": "Narrowed living room",
        },
    )
    versions = client.get(f"/projects/{stored_project_id}/versions").json()
    assert versions[0]["summary"] == "Narrowed living room"


def test_three_sequential_changes_yield_three_versions(stored_project_id: str):
    """generate → regenerate → edit produces exactly 3 ordered versions."""
    for ct in ("generate", "regenerate", "edit"):
        client.patch(
            f"/projects/{stored_project_id}",
            json={"project": _minimal_project(), "change_type": ct},
        )
    versions = client.get(f"/projects/{stored_project_id}/versions").json()
    assert len(versions) == 3
    types = [v["change_type"] for v in versions]
    assert types == ["edit", "regenerate", "generate"]  # newest first


def test_list_versions_reverse_chronological(stored_project_id: str):
    """Versions are returned newest-first."""
    for ct in ("generate", "edit"):
        client.patch(
            f"/projects/{stored_project_id}",
            json={"project": _minimal_project(), "change_type": ct},
        )
    versions = client.get(f"/projects/{stored_project_id}/versions").json()
    ts = [v["created_at"] for v in versions]
    assert ts == sorted(ts, reverse=True)


def test_list_versions_includes_room_count_and_area(stored_project_id: str):
    """Meta row has room_count and total_area matching the snapshot."""
    project = _minimal_project(n_rooms=3)
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": project, "change_type": "generate"},
    )
    meta = client.get(f"/projects/{stored_project_id}/versions").json()[0]
    assert meta["room_count"] == 3
    assert meta["total_area"] > 0


def test_list_versions_includes_thumbnail(stored_project_id: str):
    """Meta row has a non-empty inline SVG thumbnail."""
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": _minimal_project(), "change_type": "generate"},
    )
    meta = client.get(f"/projects/{stored_project_id}/versions").json()[0]
    assert meta["thumbnail"]
    assert "<svg" in meta["thumbnail"]


# ── get_version ───────────────────────────────────────────────────────────────

def test_get_version_returns_full_snapshot(stored_project_id: str):
    """GET /versions/{id} returns the full ProjectVersion including snapshot."""
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": _minimal_project(), "change_type": "generate"},
    )
    meta = client.get(f"/projects/{stored_project_id}/versions").json()[0]
    version_id = meta["version_id"]

    resp = client.get(f"/projects/{stored_project_id}/versions/{version_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"] == version_id
    assert "snapshot" in data
    assert "rooms" in data["snapshot"]


def test_get_version_404_on_unknown_id(stored_project_id: str):
    """Unknown version_id returns 404."""
    resp = client.get(f"/projects/{stored_project_id}/versions/nonexistent-id")
    assert resp.status_code == 404


# ── restore ───────────────────────────────────────────────────────────────────

def test_restore_sets_active_project(stored_project_id: str):
    """POST /restore updates the active project to the snapshot."""
    project_v1 = _minimal_project(n_rooms=2)
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": project_v1, "change_type": "generate"},
    )
    meta_v1 = client.get(f"/projects/{stored_project_id}/versions").json()[0]

    # Make a second version with 3 rooms
    project_v2 = _minimal_project(n_rooms=3)
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": project_v2, "change_type": "edit"},
    )

    # Restore to v1 (2 rooms)
    resp = client.post(
        f"/projects/{stored_project_id}/versions/{meta_v1['version_id']}/restore"
    )
    assert resp.status_code == 200
    active = client.get(f"/projects/{stored_project_id}").json()
    assert len(active["project"]["rooms"]) == 2


def test_restore_appends_restore_version(stored_project_id: str):
    """Restoring appends a 'restore' version without deleting prior history."""
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": _minimal_project(), "change_type": "generate"},
    )
    meta = client.get(f"/projects/{stored_project_id}/versions").json()[0]

    client.post(f"/projects/{stored_project_id}/versions/{meta['version_id']}/restore")

    versions = client.get(f"/projects/{stored_project_id}/versions").json()
    assert len(versions) == 2  # original + restore
    types = [v["change_type"] for v in versions]
    assert "restore" in types
    assert "generate" in types


def test_restore_never_destroys_history(stored_project_id: str):
    """Multiple restores accumulate history, never truncate it."""
    for ct in ("generate", "edit"):
        client.patch(
            f"/projects/{stored_project_id}",
            json={"project": _minimal_project(), "change_type": ct},
        )

    # Restore twice
    meta = client.get(f"/projects/{stored_project_id}/versions").json()[-1]
    client.post(f"/projects/{stored_project_id}/versions/{meta['version_id']}/restore")
    client.post(f"/projects/{stored_project_id}/versions/{meta['version_id']}/restore")

    versions = client.get(f"/projects/{stored_project_id}/versions").json()
    assert len(versions) == 4  # generate + edit + restore + restore


# ── diff ─────────────────────────────────────────────────────────────────────

def test_diff_detects_added_rooms(stored_project_id: str):
    """Diff detects rooms present in B but not in A."""
    proj_a = _minimal_project(n_rooms=1)
    proj_b = _minimal_project(n_rooms=2)
    # Give proj_b a unique room id so it shows as "added"
    proj_b["rooms"][1]["id"] = "room-extra"

    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": proj_a, "change_type": "generate"},
    )
    vid_a = client.get(f"/projects/{stored_project_id}/versions").json()[0]["version_id"]

    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": proj_b, "change_type": "edit"},
    )
    vid_b = client.get(f"/projects/{stored_project_id}/versions").json()[0]["version_id"]

    resp = client.get(f"/projects/{stored_project_id}/versions/{vid_a}/diff/{vid_b}")
    assert resp.status_code == 200
    diff = resp.json()
    assert diff["total_rooms_delta"] == 1
    assert len(diff["added_rooms"]) == 1
    assert diff["added_rooms"][0]["room_id"] == "room-extra"


def test_diff_detects_removed_rooms(stored_project_id: str):
    """Diff detects rooms present in A but not in B."""
    proj_a = _minimal_project(n_rooms=2)
    proj_b = _minimal_project(n_rooms=1)

    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": proj_a, "change_type": "generate"},
    )
    vid_a = client.get(f"/projects/{stored_project_id}/versions").json()[0]["version_id"]

    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": proj_b, "change_type": "edit"},
    )
    vid_b = client.get(f"/projects/{stored_project_id}/versions").json()[0]["version_id"]

    resp = client.get(f"/projects/{stored_project_id}/versions/{vid_a}/diff/{vid_b}")
    assert resp.status_code == 200
    diff = resp.json()
    assert diff["total_rooms_delta"] == -1
    assert len(diff["removed_rooms"]) == 1


def test_diff_detects_resized_rooms(stored_project_id: str):
    """Diff detects rooms whose dimensions changed between versions."""
    proj_a = _minimal_project(n_rooms=1)
    proj_b = _minimal_project(n_rooms=1)
    proj_b["rooms"][0]["width"] = 15  # enlarged

    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": proj_a, "change_type": "generate"},
    )
    vid_a = client.get(f"/projects/{stored_project_id}/versions").json()[0]["version_id"]

    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": proj_b, "change_type": "edit"},
    )
    vid_b = client.get(f"/projects/{stored_project_id}/versions").json()[0]["version_id"]

    resp = client.get(f"/projects/{stored_project_id}/versions/{vid_a}/diff/{vid_b}")
    diff = resp.json()
    assert len(diff["resized_rooms"]) == 1
    assert diff["resized_rooms"][0]["area_delta"] > 0


def test_diff_404_on_unknown_version(stored_project_id: str):
    """Diff returns 404 if either version id does not exist."""
    client.patch(
        f"/projects/{stored_project_id}",
        json={"project": _minimal_project(), "change_type": "generate"},
    )
    vid = client.get(f"/projects/{stored_project_id}/versions").json()[0]["version_id"]

    resp = client.get(f"/projects/{stored_project_id}/versions/{vid}/diff/bogus-id")
    assert resp.status_code == 404


# ── 404 on unknown project ────────────────────────────────────────────────────

def test_list_versions_404_on_unknown_project():
    resp = client.get("/projects/does-not-exist/versions")
    assert resp.status_code == 404


def test_get_version_404_on_unknown_project():
    resp = client.get("/projects/does-not-exist/versions/v-123")
    assert resp.status_code == 404


def test_restore_404_on_unknown_project():
    resp = client.post("/projects/does-not-exist/versions/v-123/restore")
    assert resp.status_code == 404
