"""Phase 23.6 — Render route tests.

Covers:
- DeterministicRenderProvider returns conditioning bytes (no-key fallback)
- DeterministicRenderProvider returns placeholder PNG when no conditioning image
- Style preset list returns 5 items
- GET /render/styles endpoint
- POST /projects/{id}/render — missing camera_id rejected
- POST /projects/{id}/render — valid request returns render_b64
- POST /projects/{id}/render — 409 before generation
- POST /projects/{id}/render — 404 for missing project
"""

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.ai.provider import DeterministicRenderProvider
from app.core.architecture.sample_factory import create_sample_project
from app.core.render.styles import list_styles, get_style
from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def project_with_design(client: TestClient):
    """Stored project that has a generated design."""
    sample = client.get("/projects/sample").json()
    proj = client.post("/projects", json={"name": "Render House"}).json()
    client.patch(f"/projects/{proj['id']}", json={"project": sample})
    return proj["id"]


# ── Provider unit tests ───────────────────────────────────────────────────────


def test_no_key_fallback_returns_conditioning_image():
    """DeterministicRenderProvider with conditioning returns the decoded bytes."""
    project = create_sample_project()
    # Create a 1×1 white PNG as the conditioning image
    white_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    provider = DeterministicRenderProvider()
    result = provider.render_image(project, "exterior_quarter", "photorealistic_exterior", white_png_b64)
    assert isinstance(result, bytes)
    assert result == base64.b64decode(white_png_b64)


def test_no_key_fallback_with_data_url_prefix():
    """DeterministicRenderProvider strips data-URL prefix before decoding."""
    project = create_sample_project()
    white_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    data_url = f"data:image/png;base64,{white_png_b64}"
    provider = DeterministicRenderProvider()
    result = provider.render_image(project, "exterior_quarter", "photorealistic_exterior", data_url)
    assert result == base64.b64decode(white_png_b64)


def test_no_key_fallback_returns_placeholder_without_conditioning():
    """DeterministicRenderProvider returns a valid PNG when no conditioning image."""
    project = create_sample_project()
    provider = DeterministicRenderProvider()
    result = provider.render_image(project, "exterior_quarter", "photorealistic_exterior", None)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # Valid PNG magic bytes
    assert result[:4] == b"\x89PNG"


# ── Style preset tests ────────────────────────────────────────────────────────


def test_style_list_returns_5_items():
    """list_styles() returns exactly 5 presets."""
    styles = list_styles()
    assert len(styles) == 5


def test_style_ids_are_unique():
    """All style ids are distinct."""
    styles = list_styles()
    ids = [s.id for s in styles]
    assert len(ids) == len(set(ids))


def test_style_presets_have_required_fields():
    """Each RenderStyle has id, name, description, swatch_color."""
    for s in list_styles():
        assert s.id
        assert s.name
        assert s.description
        assert s.swatch_color.startswith("#")
        assert s.prompt_suffix
        assert s.negative_prompt


def test_get_style_fallback():
    """get_style with unknown id returns first preset, not an error."""
    style = get_style("totally_unknown_style_xyz")
    assert style.id == list_styles()[0].id


# ── API tests ─────────────────────────────────────────────────────────────────


def test_get_render_styles_endpoint(client: TestClient):
    """GET /render/styles returns 5 items with correct shape."""
    resp = client.get("/render/styles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    for item in data:
        assert "id" in item
        assert "name" in item
        assert "description" in item
        assert "swatch_color" in item


def test_render_route_rejects_missing_camera_id(client: TestClient, project_with_design: str):
    """POST /projects/{id}/render with empty camera_id → 422."""
    resp = client.post(
        f"/projects/{project_with_design}/render",
        json={"camera_id": "", "style": "photorealistic_exterior"},
    )
    assert resp.status_code == 422


def test_render_route_returns_base64(client: TestClient, project_with_design: str):
    """POST /projects/{id}/render with valid inputs returns render_b64."""
    resp = client.post(
        f"/projects/{project_with_design}/render",
        json={"camera_id": "exterior_quarter", "style": "photorealistic_exterior"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "render_b64" in data
    assert data["style"] == "photorealistic_exterior"
    assert data["camera_id"] == "exterior_quarter"
    # render_b64 must be valid base64
    decoded = base64.b64decode(data["render_b64"])
    assert len(decoded) > 0


def test_render_route_accepts_conditioning_image(client: TestClient, project_with_design: str):
    """Conditioning image is accepted and returned by deterministic provider."""
    white_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    resp = client.post(
        f"/projects/{project_with_design}/render",
        json={
            "camera_id": "exterior_quarter",
            "style": "architectural_sketch",
            "conditioning_image_b64": white_png_b64,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert base64.b64decode(data["render_b64"]) == base64.b64decode(white_png_b64)


def test_render_route_404_on_missing_project(client: TestClient):
    """POST /projects/nonexistent/render → 404."""
    resp = client.post(
        "/projects/does-not-exist/render",
        json={"camera_id": "exterior_quarter", "style": "photorealistic_exterior"},
    )
    assert resp.status_code == 404


def test_render_route_409_before_generation(client: TestClient):
    """POST /projects/{id}/render → 409 when no design generated yet."""
    proj = client.post("/projects", json={"name": "Empty Render"}).json()
    resp = client.post(
        f"/projects/{proj['id']}/render",
        json={"camera_id": "exterior_quarter", "style": "photorealistic_exterior"},
    )
    assert resp.status_code == 409
