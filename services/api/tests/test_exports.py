"""Phase 7 — Export tests.

Covers: per-exporter file output, layer/group presence, manifest appending,
API flow (201 + download + list), no-design rejection (409).
"""

import json
from pathlib import Path

import ezdxf
import pytest
from fastapi.testclient import TestClient

from app.core.architecture.sample_factory import create_sample_project
from app.core.exports import export_dxf, export_json, export_png, export_svg
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
    """A stored project that already has a generated design."""
    sample = client.get("/projects/sample").json()
    proj = client.post("/projects", json={"name": "Export House"}).json()
    client.patch(f"/projects/{proj['id']}", json={"project": sample})
    return proj["id"]


# ── 7.1 JSON exporter ────────────────────────────────────────────────────────


def test_json_exporter_writes_file(tmp_path, sample):
    out = tmp_path / "exports" / "floor_plan.json"
    export_json(sample, out)
    assert out.exists()
    data = json.loads(out.read_bytes())
    assert data["id"] == sample.id
    assert "rooms" in data
    assert isinstance(data["rooms"], list)


def test_json_exporter_returns_bytes(tmp_path, sample):
    out = tmp_path / "floor_plan.json"
    result = export_json(sample, out)
    assert isinstance(result, bytes)
    assert b'"rooms"' in result


# ── 7.2 SVG exporter ─────────────────────────────────────────────────────────


def test_svg_exporter_writes_file(tmp_path, sample):
    out = tmp_path / "floor_plan.svg"
    export_svg(sample, out)
    assert out.exists()


def test_svg_has_required_layer_groups(tmp_path, sample):
    out = tmp_path / "floor_plan.svg"
    svg = export_svg(sample, out).decode("utf-8")
    for layer in ("site", "rooms", "doors", "windows", "labels", "dimensions"):
        assert f'id="{layer}"' in svg, f"Missing SVG layer group: {layer}"


def test_svg_contains_room_names(tmp_path, sample):
    out = tmp_path / "floor_plan.svg"
    svg = export_svg(sample, out).decode("utf-8")
    for room in sample.rooms:
        assert room.name in svg


def test_svg_is_valid_xml(tmp_path, sample):
    import xml.etree.ElementTree as ET
    out = tmp_path / "floor_plan.svg"
    svg_bytes = export_svg(sample, out)
    # Should not raise
    root = ET.fromstring(svg_bytes.decode("utf-8"))
    assert root.tag.endswith("svg")


# ── 7.3 PNG exporter ─────────────────────────────────────────────────────────


def test_png_exporter_writes_file(tmp_path, sample):
    out = tmp_path / "floor_plan.png"
    export_png(sample, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_png_is_valid_image(tmp_path, sample):
    from PIL import Image
    out = tmp_path / "floor_plan.png"
    export_png(sample, out)
    img = Image.open(str(out))
    assert img.format == "PNG"
    assert img.width > 0 and img.height > 0


# ── 7.4 DXF exporter ─────────────────────────────────────────────────────────


def test_dxf_exporter_writes_file(tmp_path, sample):
    out = tmp_path / "floor_plan.dxf"
    export_dxf(sample, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_dxf_has_required_layers(tmp_path, sample):
    out = tmp_path / "floor_plan.dxf"
    export_dxf(sample, out)
    doc = ezdxf.readfile(str(out))
    layer_names = [layer.dxf.name for layer in doc.layers]
    for expected in ("A-SITE", "A-WALL", "A-DOOR", "A-WINDOW", "A-ROOM-TEXT", "A-DIMS"):
        assert expected in layer_names, f"Missing DXF layer: {expected}"


def test_dxf_has_entities_on_wall_layer(tmp_path, sample):
    out = tmp_path / "floor_plan.dxf"
    export_dxf(sample, out)
    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    wall_ents = [e for e in msp if e.dxf.layer == "A-WALL"]
    assert len(wall_ents) == len(sample.rooms)


# ── 7.5 Manifest + API ───────────────────────────────────────────────────────


def test_manifest_appended_after_export(tmp_path, sample):
    from datetime import datetime, timezone
    from app.core.models import ExportManifest
    store = LocalProjectStore(tmp_path)
    stored = store.create_project("Test")

    # Inject design
    store.update_project(stored.id, project=sample)

    m = ExportManifest(
        filename="floor_plan.svg",
        format="svg",
        path="/some/path.svg",
        created_at=datetime.now(timezone.utc),
    )
    store.save_export_manifest(stored.id, m)
    manifests = store.list_export_manifests(stored.id)
    assert len(manifests) == 1
    assert manifests[0].format == "svg"


def test_api_export_json(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/json")
    assert r.status_code == 201
    body = r.json()
    assert body["format"] == "json"
    assert body["filename"].endswith(".json")


def test_api_export_svg(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/svg")
    assert r.status_code == 201
    assert r.json()["format"] == "svg"


def test_api_export_png(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/png")
    assert r.status_code == 201
    assert r.json()["format"] == "png"


def test_api_export_dxf(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/dxf")
    assert r.status_code == 201
    assert r.json()["format"] == "dxf"


def test_api_list_exports(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/json")
    client.post(f"/projects/{project_with_design}/exports/svg")
    r = client.get(f"/projects/{project_with_design}/exports")
    assert r.status_code == 200
    formats = [m["format"] for m in r.json()]
    assert "json" in formats
    assert "svg" in formats


def test_api_download_export(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/svg")
    r = client.get(f"/projects/{project_with_design}/exports/floor_plan.svg")
    assert r.status_code == 200
    assert b"<svg" in r.content


def test_api_export_rejects_project_without_design(client):
    proj = client.post("/projects", json={"name": "Empty"}).json()
    r = client.post(f"/projects/{proj['id']}/exports/json")
    assert r.status_code == 409


def test_api_export_404_for_unknown_project(client):
    r = client.post("/projects/nonexistent/exports/svg")
    assert r.status_code == 404
