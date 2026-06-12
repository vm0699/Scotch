from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_full_crud_flow(client: TestClient) -> None:
    created = client.post("/projects", json={"name": "Flow House", "prompt": "2bhk"})
    assert created.status_code == 201
    project_id = created.json()["id"]

    listing = client.get("/projects")
    assert [p["id"] for p in listing.json()] == [project_id]

    fetched = client.get(f"/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Flow House"

    sample = client.get("/projects/sample").json()
    patched = client.patch(
        f"/projects/{project_id}",
        json={"name": "Flow Villa", "project": sample},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Flow Villa"
    assert len(patched.json()["project"]["rooms"]) == 8

    deleted = client.delete(f"/projects/{project_id}")
    assert deleted.status_code == 204
    assert client.get(f"/projects/{project_id}").status_code == 404
    assert client.get("/projects").json() == []


def test_create_requires_name(client: TestClient) -> None:
    assert client.post("/projects", json={}).status_code == 422


def test_update_rejects_invalid_design(client: TestClient) -> None:
    project_id = client.post("/projects", json={"name": "Bad Data"}).json()["id"]
    sample = client.get("/projects/sample").json()
    sample["rooms"][0]["x"] = 999  # push a room outside the site
    response = client.patch(f"/projects/{project_id}", json={"project": sample})
    assert response.status_code == 422
    assert "outside" in str(response.json()["detail"]["errors"])


def test_unknown_project_returns_404(client: TestClient) -> None:
    assert client.get("/projects/ghost").status_code == 404
    assert client.patch("/projects/ghost", json={"name": "x"}).status_code == 404
    assert client.delete("/projects/ghost").status_code == 404
