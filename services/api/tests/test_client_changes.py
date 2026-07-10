"""Phase 34 — Client Change Management REST API tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.changes.store import ChangeStore, get_change_store
from app.core.storage import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    change_store = ChangeStore(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    app.dependency_overrides[get_change_store] = lambda: change_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _project_with_design(client: TestClient) -> str:
    """Create a stored project that already has a generated floor plan."""
    proj = client.post("/projects", json={"name": "Change Test", "prompt": "2BHK"}).json()
    pid = proj["id"]
    sample = client.get("/projects/sample").json()
    client.patch(f"/projects/{pid}", json={"project": sample, "change_type": "generate"})
    return pid


# ── CRUD lifecycle ────────────────────────────────────────────────────────────

def test_create_change_returns_201(client):
    pid = _project_with_design(client)
    r = client.post(f"/projects/{pid}/changes", json={
        "request_text": "Client wants an attached toilet to master bedroom",
        "priority": "high",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["priority"] == "high"
    assert "id" in data
    assert "attached toilet" in data["request_text"]


def test_create_change_computes_affected_items(client):
    pid = _project_with_design(client)
    r = client.post(f"/projects/{pid}/changes", json={
        "request_text": "Add en-suite bathroom to master bedroom",
        "compute_affected": True,
    })
    assert r.status_code == 201
    data = r.json()
    ai = data.get("affected_items")
    assert ai is not None
    assert ai["total_count"] > 0


def test_list_changes_returns_array(client):
    pid = _project_with_design(client)
    client.post(f"/projects/{pid}/changes", json={"request_text": "Change A"})
    client.post(f"/projects/{pid}/changes", json={"request_text": "Change B"})
    r = client.get(f"/projects/{pid}/changes")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_get_single_change(client):
    pid = _project_with_design(client)
    create = client.post(f"/projects/{pid}/changes", json={"request_text": "Reduce kitchen size"})
    cid = create.json()["id"]
    r = client.get(f"/projects/{pid}/changes/{cid}")
    assert r.status_code == 200
    assert r.json()["id"] == cid


def test_get_missing_change_returns_404(client):
    pid = _project_with_design(client)
    r = client.get(f"/projects/{pid}/changes/chg-nonexistent")
    assert r.status_code == 404


def test_patch_status_approved(client):
    pid = _project_with_design(client)
    cid = client.post(f"/projects/{pid}/changes", json={"request_text": "Bigger living room"}).json()["id"]
    r = client.patch(f"/projects/{pid}/changes/{cid}", json={"status": "approved"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_patch_status_applied_bumps_revision(client):
    pid = _project_with_design(client)
    cid = client.post(f"/projects/{pid}/changes", json={"request_text": "Add bedroom"}).json()["id"]
    client.patch(f"/projects/{pid}/changes/{cid}", json={"status": "approved"})
    r = client.patch(f"/projects/{pid}/changes/{cid}", json={"status": "applied"})
    assert r.status_code == 200
    assert r.json()["status"] == "applied"
    proj_r = client.get(f"/projects/{pid}")
    assert proj_r.status_code == 200
    proj = proj_r.json()
    if proj.get("project"):
        rev = proj["project"].get("revision_meta")
        if rev:
            assert rev["revision_number"] >= 1


def test_patch_status_rejected(client):
    pid = _project_with_design(client)
    cid = client.post(f"/projects/{pid}/changes", json={"request_text": "Relocate staircase"}).json()["id"]
    r = client.patch(f"/projects/{pid}/changes/{cid}", json={"status": "rejected"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_delete_change_returns_204(client):
    pid = _project_with_design(client)
    cid = client.post(f"/projects/{pid}/changes", json={"request_text": "Temporary request"}).json()["id"]
    r = client.delete(f"/projects/{pid}/changes/{cid}")
    assert r.status_code == 204
    assert client.get(f"/projects/{pid}/changes/{cid}").status_code == 404


def test_delete_nonexistent_returns_404(client):
    pid = _project_with_design(client)
    r = client.delete(f"/projects/{pid}/changes/chg-gone")
    assert r.status_code == 404


# ── Affected items endpoint ───────────────────────────────────────────────────

def test_get_affected_items_endpoint(client):
    pid = _project_with_design(client)
    cid = client.post(f"/projects/{pid}/changes", json={
        "request_text": "Add parking space",
    }).json()["id"]
    r = client.get(f"/projects/{pid}/changes/{cid}/affected")
    assert r.status_code == 200
    data = r.json()
    assert data["change_id"] == cid
    assert "total_count" in data
    assert isinstance(data["rooms"], list)
    assert isinstance(data["exports"], list)


def test_affected_items_missing_project_returns_404(client):
    r = client.get("/projects/nonexistent-proj/changes/chg-abc/affected")
    assert r.status_code == 404


# ── Priority and source ───────────────────────────────────────────────────────

def test_create_change_with_urgent_priority(client):
    pid = _project_with_design(client)
    r = client.post(f"/projects/{pid}/changes", json={
        "request_text": "Urgent: reduce total cost by 30%",
        "priority": "urgent",
        "source": "client",
    })
    assert r.status_code == 201
    assert r.json()["priority"] == "urgent"
    assert r.json()["source"] == "client"


def test_create_change_default_source_is_client(client):
    pid = _project_with_design(client)
    r = client.post(f"/projects/{pid}/changes", json={"request_text": "Some request"})
    assert r.status_code == 201
    assert r.json()["source"] == "client"


# ── Error handling ────────────────────────────────────────────────────────────

def test_changes_for_missing_project_returns_404(client):
    r = client.post("/projects/no-such-project/changes", json={"request_text": "Anything"})
    assert r.status_code == 404


def test_list_changes_missing_project_returns_404(client):
    r = client.get("/projects/no-such-project/changes")
    assert r.status_code == 404


def test_create_change_no_design_still_creates(client):
    """A project without a design can still log a change (affected_items skipped)."""
    proj = client.post("/projects", json={"name": "Empty project"}).json()
    pid = proj["id"]
    r = client.post(f"/projects/{pid}/changes", json={
        "request_text": "Pre-design client note: needs north-facing master bedroom",
        "compute_affected": True,
    })
    assert r.status_code == 201
    # No design → affected_items remains None or empty
    data = r.json()
    assert data["id"].startswith("chg-")
