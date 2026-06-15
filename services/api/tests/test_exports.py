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


# ── 11.1 DXF deepening ───────────────────────────────────────────────────────


def test_dxf_has_hatch_layer(tmp_path, sample):
    out = tmp_path / "floor_plan.dxf"
    export_dxf(sample, out)
    doc = ezdxf.readfile(str(out))
    layer_names = [layer.dxf.name for layer in doc.layers]
    assert "A-HATCH" in layer_names


def test_dxf_has_anno_and_title_layers(tmp_path, sample):
    out = tmp_path / "floor_plan.dxf"
    export_dxf(sample, out)
    doc = ezdxf.readfile(str(out))
    layer_names = [layer.dxf.name for layer in doc.layers]
    assert "A-ANNO" in layer_names
    assert "A-TITLE" in layer_names


def test_dxf_hatch_count_matches_rooms(tmp_path, sample):
    out = tmp_path / "floor_plan.dxf"
    export_dxf(sample, out)
    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    hatches = [e for e in msp if e.dxftype() == "HATCH"]
    assert len(hatches) == len(sample.rooms)


def test_dxf_title_block_has_text_entities(tmp_path, sample):
    out = tmp_path / "floor_plan.dxf"
    export_dxf(sample, out)
    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    title_texts = [
        e for e in msp
        if e.dxf.layer == "A-TITLE" and e.dxftype() in ("TEXT", "MTEXT")
    ]
    assert len(title_texts) >= 2  # at minimum: project name + subtitle


def test_dxf_north_arrow_entities_on_anno_layer(tmp_path, sample):
    out = tmp_path / "floor_plan.dxf"
    export_dxf(sample, out)
    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    anno_ents = [e for e in msp if e.dxf.layer == "A-ANNO"]
    assert len(anno_ents) >= 3  # circle + arrow lines + N text


# ── 11.2 SketchUp Ruby exporter ──────────────────────────────────────────────


def test_sketchup_exporter_writes_file(tmp_path, sample):
    from app.core.exports import export_sketchup
    out = tmp_path / "floor_plan.rb"
    export_sketchup(sample, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_sketchup_exporter_returns_bytes(tmp_path, sample):
    from app.core.exports import export_sketchup
    out = tmp_path / "floor_plan.rb"
    result = export_sketchup(sample, out)
    assert isinstance(result, bytes)


def test_sketchup_has_ruby_structure(tmp_path, sample):
    from app.core.exports import export_sketchup
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    assert "require 'sketchup'" in rb
    assert "model.start_operation" in rb
    assert "model.commit_operation" in rb


def test_sketchup_has_all_room_names(tmp_path, sample):
    from app.core.exports import export_sketchup
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    for room in sample.rooms:
        assert room.name in rb, f"Room {room.name!r} missing from SketchUp script"


def test_sketchup_has_geometry_primitives(tmp_path, sample):
    from app.core.exports import export_sketchup
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    assert "Geom::Point3d.new" in rb
    assert "pushpull" in rb
    assert "Ground Slab" in rb
    assert "Roof Slab" in rb


def test_sketchup_has_materials(tmp_path, sample):
    from app.core.exports import export_sketchup
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    assert "scotch_mat" in rb
    assert "Scotch_Wall" in rb


def test_sketchup_has_tags(tmp_path, sample):
    from app.core.exports import export_sketchup
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    assert "S-SITE" in rb
    assert "S-ROOMS" in rb
    assert "S-ROOF" in rb


def test_api_export_sketchup(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/sketchup")
    assert r.status_code == 201
    body = r.json()
    assert body["format"] == "sketchup"
    assert body["filename"].endswith(".rb")


def test_api_download_sketchup(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/sketchup")
    r = client.get(f"/projects/{project_with_design}/exports/floor_plan.rb")
    assert r.status_code == 200
    assert b"require 'sketchup'" in r.content


# ── 11.4 Blender Python exporter ─────────────────────────────────────────────


def test_blender_exporter_writes_file(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    export_blender(sample, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_blender_exporter_returns_bytes(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    result = export_blender(sample, out)
    assert isinstance(result, bytes)


def test_blender_has_bpy_imports(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    py = export_blender(sample, out).decode("utf-8")
    assert "import bpy" in py
    assert "import bmesh" in py


def test_blender_has_all_room_names(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    py = export_blender(sample, out).decode("utf-8")
    for room in sample.rooms:
        safe = room.name.replace(" ", "_").replace("'", "")
        assert safe in py, f"Room safe-name {safe!r} missing from Blender script"


def test_blender_has_boolean_modifiers(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    py = export_blender(sample, out).decode("utf-8")
    assert "BOOLEAN" in py
    assert "DIFFERENCE" in py


def test_blender_has_cameras(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    py = export_blender(sample, out).decode("utf-8")
    assert "Cam_Top" in py
    assert "Cam_Exterior" in py
    assert "ORTHO" in py


def test_blender_has_lighting(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    py = export_blender(sample, out).decode("utf-8")
    assert "SUN" in py
    assert "AREA" in py


def test_blender_has_render_settings(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    py = export_blender(sample, out).decode("utf-8")
    assert "BLENDER_EEVEE" in py
    assert "resolution_x" in py


def test_blender_has_materials(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    py = export_blender(sample, out).decode("utf-8")
    assert "scotch_mat" in py
    assert "Principled BSDF" in py


def test_blender_collections(tmp_path, sample):
    from app.core.exports import export_blender
    out = tmp_path / "floor_plan.py"
    py = export_blender(sample, out).decode("utf-8")
    for col in ("Scotch_Site", "Scotch_Walls", "Scotch_Lighting", "Scotch_Cameras"):
        assert col in py, f"Collection {col!r} missing from Blender script"


def test_api_export_blender(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/blender")
    assert r.status_code == 201
    body = r.json()
    assert body["format"] == "blender"
    assert body["filename"].endswith(".py")


def test_api_download_blender(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/blender")
    r = client.get(f"/projects/{project_with_design}/exports/floor_plan.py")
    assert r.status_code == 200
    assert b"import bpy" in r.content


# ── 12.1 Sheet SVG exporter ──────────────────────────────────────────────────


def test_sheet_svg_writes_file(tmp_path, sample):
    from app.core.exports import export_sheet_svg
    out = tmp_path / "presentation_sheet.svg"
    export_sheet_svg(sample, out)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_sheet_svg_returns_bytes(tmp_path, sample):
    from app.core.exports import export_sheet_svg
    out = tmp_path / "presentation_sheet.svg"
    result = export_sheet_svg(sample, out)
    assert isinstance(result, bytes)


def test_sheet_svg_is_valid_xml(tmp_path, sample):
    import xml.etree.ElementTree as ET
    from app.core.exports import export_sheet_svg
    out = tmp_path / "presentation_sheet.svg"
    data = export_sheet_svg(sample, out)
    root = ET.fromstring(data.decode("utf-8"))
    assert root.tag.endswith("svg")


def test_sheet_svg_has_all_layer_groups(tmp_path, sample):
    from app.core.exports import export_sheet_svg
    out = tmp_path / "presentation_sheet.svg"
    svg = export_sheet_svg(sample, out).decode("utf-8")
    for layer_id in ("sheet-border", "title-block", "plan-viewport", "schedule", "legend", "notes", "footer"):
        assert f'id="{layer_id}"' in svg, f"Missing SVG layer: {layer_id}"


def test_sheet_svg_contains_project_title(tmp_path, sample):
    from app.core.exports import export_sheet_svg
    out = tmp_path / "presentation_sheet.svg"
    svg = export_sheet_svg(sample, out, title="Arch Test House").decode("utf-8")
    assert "Arch Test House" in svg


def test_sheet_svg_has_room_schedule(tmp_path, sample):
    from app.core.exports import export_sheet_svg
    out = tmp_path / "presentation_sheet.svg"
    svg = export_sheet_svg(sample, out).decode("utf-8")
    for room in sample.rooms[:3]:
        assert room.name in svg


def test_sheet_svg_a3_viewbox(tmp_path, sample):
    from app.core.exports import export_sheet_svg
    out = tmp_path / "presentation_sheet.svg"
    svg = export_sheet_svg(sample, out, page_size="A3").decode("utf-8")
    assert "420" in svg and "297" in svg and "viewBox" in svg


def test_api_export_sheet_svg(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/sheet_svg")
    assert r.status_code == 201
    body = r.json()
    assert body["format"] == "sheet_svg"
    assert body["filename"] == "presentation_sheet.svg"


def test_api_download_sheet_svg(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/sheet_svg")
    r = client.get(f"/projects/{project_with_design}/exports/presentation_sheet.svg")
    assert r.status_code == 200
    assert b"<svg" in r.content


# ── 12.2 Sheet PDF exporter ──────────────────────────────────────────────────


def test_sheet_pdf_writes_file(tmp_path, sample):
    from app.core.exports import export_sheet_pdf
    out = tmp_path / "presentation_sheet.pdf"
    export_sheet_pdf(sample, out)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_sheet_pdf_returns_bytes(tmp_path, sample):
    from app.core.exports import export_sheet_pdf
    out = tmp_path / "presentation_sheet.pdf"
    result = export_sheet_pdf(sample, out)
    assert isinstance(result, bytes)


def test_sheet_pdf_has_pdf_header(tmp_path, sample):
    from app.core.exports import export_sheet_pdf
    out = tmp_path / "presentation_sheet.pdf"
    data = export_sheet_pdf(sample, out)
    assert data[:4] == b"%PDF", "File does not start with PDF magic bytes"


def test_sheet_pdf_has_content(tmp_path, sample):
    from app.core.exports import export_sheet_pdf
    out = tmp_path / "presentation_sheet.pdf"
    data = export_sheet_pdf(sample, out)
    assert len(data) > 3000


def test_sheet_pdf_with_custom_title(tmp_path, sample):
    from app.core.exports import export_sheet_pdf
    out = tmp_path / "presentation_sheet.pdf"
    data = export_sheet_pdf(sample, out, title="Custom Title", subtitle="Phase 12")
    assert data[:4] == b"%PDF"
    assert len(data) > 1000


def test_api_export_sheet_pdf(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/sheet_pdf")
    assert r.status_code == 201
    body = r.json()
    assert body["format"] == "sheet_pdf"
    assert body["filename"] == "presentation_sheet.pdf"


def test_api_download_sheet_pdf(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/sheet_pdf")
    r = client.get(f"/projects/{project_with_design}/exports/presentation_sheet.pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    assert r.headers["content-type"] == "application/pdf"
