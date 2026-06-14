"""Phase 16 — Rhino exporter tests.

Covers: script structure (layers / BooleanDifference / extrusions / roof),
        massing height alignment (16.2), API flow (201 + download).
"""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.sample_factory import create_sample_project
from app.core.exports import export_rhino
from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app


@pytest.fixture
def sample():
    return create_sample_project()


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def project_with_design(client: TestClient):
    sample = client.get("/projects/sample").json()
    proj = client.post("/projects", json={"name": "Rhino House"}).json()
    client.patch(f"/projects/{proj['id']}", json={"project": sample})
    return proj["id"]


# ── 16.1 Script structure ─────────────────────────────────────────────────────


def test_rhino_exporter_writes_file(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    export_rhino(sample, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_rhino_exporter_returns_bytes(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    result = export_rhino(sample, out)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_rhino_script_is_valid_python(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    # ast.parse raises SyntaxError on invalid Python
    tree = ast.parse(script)
    assert tree is not None


def test_rhino_script_imports_rhinoscriptsyntax(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    assert "import rhinoscriptsyntax as rs" in script


def test_rhino_script_defines_all_layers(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    for layer in ["Scotch::Site", "Scotch::Walls", "Scotch::Doors",
                  "Scotch::Windows", "Scotch::Labels", "Scotch::Roof"]:
        assert layer in script, f"Missing layer definition: {layer}"


def test_rhino_script_has_boolean_difference(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    assert "BooleanDifference" in script


def test_rhino_script_has_one_outer_box_per_room(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    # Each room gets a _wall_rN outer box
    outer_count = sum(1 for line in script.splitlines()
                      if line.strip().startswith("_wall_r"))
    assert outer_count == len(sample.rooms), (
        f"Expected {len(sample.rooms)} outer wall boxes, got {outer_count}"
    )


def test_rhino_script_has_one_boolean_diff_per_room_for_hollow(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    # First BooleanDifference per room hollows the walls (outer − inner)
    # Count lines that hollow walls (pattern: _res = rs.BooleanDifference([_wall_rN...])
    hollow_lines = [l for l in script.splitlines()
                    if "_res = rs.BooleanDifference([_wall_r" in l]
    assert len(hollow_lines) == len(sample.rooms)


def test_rhino_script_has_room_names(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    for room in sample.rooms:
        assert room.name in script, f"Room name {room.name!r} missing from script"


def test_rhino_script_has_text_dots_for_labels(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    dot_count = sum(1 for line in script.splitlines()
                    if "AddTextDot" in line)
    assert dot_count == len(sample.rooms), (
        f"Expected {len(sample.rooms)} text dots, got {dot_count}"
    )


def test_rhino_script_has_unit_detection(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    assert "rs.UnitSystem()" in script
    assert "FT = 304.8" in script   # millimetres default
    assert "FT = 0.3048" in script  # metres
    assert "FT = 1.0" in script     # feet


# ── 16.2 Massing alignment ────────────────────────────────────────────────────


def test_rhino_extrusion_height_matches_floor_height(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    fh = sample.building.floor_height if sample.building else 10.0
    assert f"WALL_H = {fh}" in script


def test_rhino_roof_slab_present(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    assert "Roof Slab" in script
    assert "Scotch::Roof" in script
    assert "_roof = _box(0.0, 0.0, WALL_H" in script


def test_rhino_site_boundary_uses_site_dimensions(tmp_path, sample):
    out = tmp_path / "floor_plan_rhino.py"
    script = export_rhino(sample, out).decode("utf-8")
    assert f"SITE_W = {sample.site.width}" in script
    assert f"SITE_D = {sample.site.depth}" in script
    assert "AddPolyline" in script


# ── API flow ──────────────────────────────────────────────────────────────────


def test_api_export_rhino(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/rhino")
    assert r.status_code == 201
    body = r.json()
    assert body["format"] == "rhino"
    assert body["filename"].endswith(".py")
    assert "rhino" in body["filename"]


def test_api_download_rhino(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/rhino")
    r = client.get(f"/projects/{project_with_design}/exports/floor_plan_rhino.py")
    assert r.status_code == 200
    content = r.content.decode("utf-8")
    assert "import rhinoscriptsyntax as rs" in content
    assert "BooleanDifference" in content


def test_api_export_rhino_rejects_no_design(client):
    proj = client.post("/projects", json={"name": "Empty"}).json()
    r = client.post(f"/projects/{proj['id']}/exports/rhino")
    assert r.status_code == 409
