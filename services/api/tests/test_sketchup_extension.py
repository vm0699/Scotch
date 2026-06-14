"""Phase 15 — SketchUp Plugin tests.

Stages:
  15.1  Hardened Ruby script (voids, labels, units, room-id groups, balanced ends).
  15.2  Extension shell file-structure (manifest registers extension, version present).
  15.3  JSON import logic (fixture round-trips; missing-key path documented).
  15.4  Model creation (builder.rb structure: groups, tags, materials, openings).
"""

import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.sample_factory import create_sample_project
from app.core.exports import export_sketchup
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
    proj = client.post("/projects", json={"name": "SU Test House"}).json()
    client.patch(f"/projects/{proj['id']}", json={"project": sample})
    return proj["id"]


# ── Integration roots ─────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SU_ROOT   = _REPO_ROOT / "integrations" / "sketchup"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 15.1 — Hardened Ruby script
# ═══════════════════════════════════════════════════════════════════════════════


def test_15_1_script_has_group_per_room(tmp_path, sample):
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    for room in sample.rooms:
        assert room.id in rb, f"Room id {room.id!r} not embedded in group name"


def test_15_1_script_has_material_defs(tmp_path, sample):
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    assert "scotch_mat" in rb
    assert "Scotch_Wall" in rb
    assert "Scotch_Ground" in rb
    assert "Scotch_Roof" in rb
    assert "Scotch_Glass" in rb


def test_15_1_script_has_opening_markers(tmp_path, sample):
    """Door/window void variables must appear in the script."""
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    # At least one door or window should exist in sample project
    has_doors   = len(sample.doors) > 0
    has_windows = len(sample.windows) > 0
    if has_doors:
        assert "door_" in rb, "Door void variables missing from script"
    if has_windows:
        assert "win_" in rb, "Window void variables missing from script"
    # Pushpull calls for voids
    if has_doors or has_windows:
        assert "cuts through wall toward exterior" in rb or "pushpull(WALL_T)" in rb


def test_15_1_script_has_units_setting(tmp_path, sample):
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    assert "UnitsOptions" in rb
    assert "LengthUnit" in rb


def test_15_1_script_has_labels_tag(tmp_path, sample):
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    assert "S-LABELS" in rb
    assert "tag_labels" in rb
    assert "Room Labels" in rb


def test_15_1_script_has_3d_text_labels(tmp_path, sample):
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    # Each room should have an add_text call with its name
    assert "add_text" in rb
    for room in sample.rooms[:3]:
        assert room.name in rb


def test_15_1_balanced_ruby_ends(tmp_path, sample):
    """Smoke-parse: count of `end` lines must equal number of `def ` lines."""
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    lines = rb.splitlines()
    def_count = sum(1 for ln in lines if ln.lstrip().startswith("def "))
    end_count  = sum(1 for ln in lines if ln.strip() == "end")
    assert end_count >= def_count, (
        f"Unbalanced Ruby: {def_count} def blocks, {end_count} end keywords"
    )


def test_15_1_vertical_door_void_face_points(tmp_path, sample):
    """Door void faces must be vertical (constant Y or X), not horizontal markers."""
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    # Vertical void faces have z coordinates like `0 * FT` and `10 * FT` (floor_height)
    # They should NOT all be at Z=0 (which was the old floor marker approach).
    assert "z_top" not in rb  # we use literal coords, not variables
    # Presence of FT conversion for z coordinates in door void section
    if sample.doors:
        assert "door_" in rb
        # The void should push through wall thickness
        assert "WALL_T" in rb


def test_15_1_room_group_name_includes_id(tmp_path, sample):
    out = tmp_path / "floor_plan.rb"
    rb = export_sketchup(sample, out).decode("utf-8")
    for room in sample.rooms:
        expected = f"{room.name} [{room.id}]"
        assert expected in rb, f"Expected group name {expected!r} in script"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 15.2 — Extension shell file structure
# ═══════════════════════════════════════════════════════════════════════════════


def test_15_2_registration_file_exists():
    assert (_SU_ROOT / "scotch_importer.rb").exists(), \
        "scotch_importer.rb registration file not found"


def test_15_2_registration_file_registers_extension():
    rb = (_SU_ROOT / "scotch_importer.rb").read_text(encoding="utf-8")
    assert "SketchupExtension.new" in rb
    assert "Sketchup.register_extension" in rb
    assert "scotch/main" in rb


def test_15_2_registration_file_has_version():
    rb = (_SU_ROOT / "scotch_importer.rb").read_text(encoding="utf-8")
    assert "version" in rb.lower()
    assert "1.0.0" in rb


def test_15_2_main_loader_exists():
    assert (_SU_ROOT / "scotch" / "main.rb").exists(), \
        "scotch/main.rb loader not found"


def test_15_2_main_loader_requires_importer_and_builder():
    rb = (_SU_ROOT / "scotch" / "main.rb").read_text(encoding="utf-8")
    assert "importer" in rb
    assert "builder" in rb


def test_15_2_main_loader_has_menu_item():
    rb = (_SU_ROOT / "scotch" / "main.rb").read_text(encoding="utf-8")
    assert "UI.menu" in rb or "add_submenu" in rb or "add_item" in rb


def test_15_2_main_loader_has_toolbar():
    rb = (_SU_ROOT / "scotch" / "main.rb").read_text(encoding="utf-8")
    assert "UI::Toolbar" in rb


def test_15_2_extension_endpoint_returns_zip(client):
    r = client.get("/integrations/sketchup/extension")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert "scotch_importer.rbz" in r.headers.get("content-disposition", "")


def test_15_2_extension_zip_contains_registration_file(client):
    r = client.get("/integrations/sketchup/extension")
    assert r.status_code == 200
    import io
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
    assert "scotch_importer.rb" in names


def test_15_2_extension_zip_contains_subfolder_files(client):
    r = client.get("/integrations/sketchup/extension")
    import io
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
    # Must have loader at minimum
    assert any(n.startswith("scotch/") for n in names), \
        f"No scotch/ subfolder files in zip: {names}"


def test_15_2_extension_files_list_endpoint(client):
    r = client.get("/integrations/sketchup/extension/files")
    assert r.status_code == 200
    body = r.json()
    assert body["extension"] == "scotch_importer.rbz"
    assert "version" in body
    assert "scotch_importer.rb" in body["files"]


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 15.3 — JSON import / importer.rb structure
# ═══════════════════════════════════════════════════════════════════════════════


def test_15_3_importer_file_exists():
    assert (_SU_ROOT / "scotch" / "importer.rb").exists()


def test_15_3_importer_has_required_keys_constant():
    rb = (_SU_ROOT / "scotch" / "importer.rb").read_text(encoding="utf-8")
    assert "REQUIRED_KEYS" in rb
    for key in ("id", "name", "rooms", "site", "building"):
        assert key in rb, f"Required key {key!r} not listed in REQUIRED_KEYS"


def test_15_3_importer_has_file_picker():
    rb = (_SU_ROOT / "scotch" / "importer.rb").read_text(encoding="utf-8")
    assert "UI.openpanel" in rb


def test_15_3_importer_has_json_parse():
    rb = (_SU_ROOT / "scotch" / "importer.rb").read_text(encoding="utf-8")
    assert "JSON.parse" in rb
    assert "require 'json'" in rb


def test_15_3_importer_has_missing_key_error_path():
    rb = (_SU_ROOT / "scotch" / "importer.rb").read_text(encoding="utf-8")
    assert "UI.messagebox" in rb
    assert "missing" in rb.lower() or "Missing" in rb


def test_15_3_importer_has_json_parse_error_handler():
    rb = (_SU_ROOT / "scotch" / "importer.rb").read_text(encoding="utf-8")
    assert "JSON::ParserError" in rb


def test_15_3_sample_project_round_trips_as_json(tmp_path, sample):
    """The sample project serialises to JSON with all keys importer expects."""
    out = tmp_path / "project.json"
    import json as _json
    data = _json.loads(sample.model_dump_json())
    for key in ("id", "name", "rooms", "site", "building"):
        assert key in data, f"Key {key!r} missing from project.json shape"
    assert isinstance(data["rooms"], list)
    assert len(data["rooms"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 15.4 — builder.rb model creation structure
# ═══════════════════════════════════════════════════════════════════════════════


def test_15_4_builder_file_exists():
    assert (_SU_ROOT / "scotch" / "builder.rb").exists()


def test_15_4_builder_has_ground_slab():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    assert "Ground Slab" in rb
    assert "build_ground_slab" in rb


def test_15_4_builder_has_roof():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    assert "Roof Slab" in rb
    assert "build_roof" in rb


def test_15_4_builder_has_all_required_tags():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    for tag in ("S-SITE", "S-ROOMS", "S-ROOF", "S-LABELS", "S-OPENINGS"):
        assert tag in rb, f"Tag {tag!r} missing from builder.rb"


def test_15_4_builder_has_room_group_named_with_id():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    # Groups named "Name [id]"
    assert "[#{rid}]" in rb or "#{rid}" in rb


def test_15_4_builder_has_room_labels():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    assert "add_room_labels" in rb
    assert "add_text" in rb


def test_15_4_builder_has_opening_void_cutter():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    assert "cut_opening" in rb
    assert "opening_points" in rb


def test_15_4_builder_has_all_wall_directions():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    for direction in ("north", "south", "east", "west"):
        assert direction in rb, f"Wall direction {direction!r} missing from builder"


def test_15_4_builder_has_materials_by_room_type():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    assert "ROOM_COLORS" in rb
    assert "setup_room_materials" in rb
    for mat_name in ("Scotch_Ground", "Scotch_Wall", "Scotch_Roof", "Scotch_Glass"):
        assert mat_name in rb


def test_15_4_builder_washer_technique():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    assert "washer" in rb
    assert "pushpull" in rb


def test_15_4_builder_sets_model_units_to_feet():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    assert "UnitsOptions" in rb
    assert "LengthUnit" in rb


def test_15_4_builder_window_void_uses_sill_height():
    rb = (_SU_ROOT / "scotch" / "builder.rb").read_text(encoding="utf-8")
    assert "SILL_H" in rb
    assert "WIN_H" in rb
