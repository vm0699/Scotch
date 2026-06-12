from fastapi.testclient import TestClient

from app.core.models import ArchitectureProject
from app.main import app

client = TestClient(app)


def test_generate_from_prompt_returns_project_summary_warnings() -> None:
    response = client.post(
        "/generate/from-prompt",
        json={"prompt": "2BHK apartment 30x50 east-facing with parking and balcony"},
    )
    assert response.status_code == 200
    payload = response.json()
    project = ArchitectureProject.model_validate(payload["project"])
    assert project.site.width == 30
    assert "Generated" in payload["summary"]
    assert isinstance(payload["warnings"], list)


def test_empty_prompt_generates_with_assumptions() -> None:
    response = client.post("/generate/from-prompt", json={"prompt": ""})
    assert response.status_code == 200
    messages = " ".join(w["message"] for w in response.json()["warnings"])
    assert "Site size not specified" in messages


def test_generated_project_can_be_saved(tmp_path) -> None:
    from app.core.storage.factory import get_project_store
    from app.core.storage.local_store import LocalProjectStore

    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    try:
        generated = client.post(
            "/generate/from-prompt", json={"prompt": "small cafe 25x40"}
        ).json()["project"]
        project_id = client.post("/projects", json={"name": "Cafe"}).json()["id"]
        patched = client.patch(
            f"/projects/{project_id}", json={"project": generated}
        )
        assert patched.status_code == 200
        assert patched.json()["project"]["rooms"]
    finally:
        app.dependency_overrides.clear()
