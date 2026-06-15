"""Phase 17 — Rendering Workflow MVP tests.

Covers:
  17.1 Render-friendly export — Blender + SketchUp object/group naming scheme.
  17.2 Material metadata — project.materials populated; colors/roughness present.
  17.3 Camera suggestions — 5 presets; correct types; positions outside/inside bbox.
  17.4 Blender automation — 5 cameras, lights, render engine, headless note.
  17.5 (documentation only, no pytest needed)
"""

import ast
import pytest

from app.core.architecture.cameras import derive_cameras
from app.core.architecture.materials import assign_default_materials
from app.core.architecture.sample_factory import create_sample_project
from app.core.exports.blender_exporter import export_blender
from app.core.exports.sketchup_exporter import export_sketchup
from app.core.models import ArchitectureProject, Material


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample() -> ArchitectureProject:
    return create_sample_project()


# ── Stage 17.2 — Material metadata ───────────────────────────────────────────

class TestMaterials:
    def test_assign_returns_project(self, sample):
        result = assign_default_materials(sample)
        assert isinstance(result, ArchitectureProject)

    def test_element_class_materials_present(self, sample):
        targets = {m.target for m in sample.materials}
        for expected in ("wall", "floor", "roof", "glass", "door", "exterior", "ground"):
            assert expected in targets, f"missing material target '{expected}'"

    def test_room_type_materials_added(self, sample):
        # Sample has living, bedroom, bathroom, kitchen, balcony, parking rooms
        targets = {m.target for m in sample.materials}
        assert "room:living" in targets
        assert "room:bedroom" in targets
        assert "room:bathroom" in targets

    def test_materials_have_base_color(self, sample):
        for m in sample.materials:
            assert m.base_color.startswith("#"), f"{m.name} missing hex base_color"
            assert len(m.base_color) == 7

    def test_materials_roughness_in_range(self, sample):
        for m in sample.materials:
            assert 0.0 <= m.roughness <= 1.0, f"{m.name} roughness out of range"

    def test_materials_metallic_in_range(self, sample):
        for m in sample.materials:
            assert 0.0 <= m.metallic <= 1.0, f"{m.name} metallic out of range"

    def test_idempotent(self, sample):
        once = assign_default_materials(sample)
        twice = assign_default_materials(once)
        assert len(once.materials) == len(twice.materials)

    def test_sample_factory_includes_materials(self, sample):
        assert len(sample.materials) > 0

    def test_generate_includes_materials(self):
        from app.core.architecture.floorplan_generator import generate_floorplan
        from app.core.architecture.requirement_parser import DesignRequirements
        req = DesignRequirements(
            prompt="2BHK on 30x50 east facing",
            site_width=30, site_depth=50,
            orientation="east",
            building_kind="residential",
            bedrooms=2, bathrooms=1,
            floors=1, style="modern",
            parking=True, balcony=True,
            dining=True, study=False, storage=True,
        )
        project, _ = generate_floorplan(req)
        assert len(project.materials) > 0
        targets = {m.target for m in project.materials}
        assert "wall" in targets


# ── Stage 17.3 — Camera suggestions ──────────────────────────────────────────

class TestCameras:
    def test_returns_five_cameras(self, sample):
        cams = derive_cameras(sample)
        assert len(cams) == 5

    def test_camera_names_unique(self, sample):
        cams = derive_cameras(sample)
        names = [c.name for c in cams]
        assert len(names) == len(set(names))

    def test_exterior_quarter_is_perspective(self, sample):
        cams = {c.name: c for c in derive_cameras(sample)}
        assert cams["exterior_quarter"].type == "perspective"

    def test_top_ortho_is_orthographic(self, sample):
        cams = {c.name: c for c in derive_cameras(sample)}
        assert cams["top_ortho"].type == "orthographic"

    def test_exterior_camera_outside_site_bbox(self, sample):
        cams = {c.name: c for c in derive_cameras(sample)}
        ext = cams["exterior_quarter"]
        sw, sd = sample.site.width, sample.site.depth
        # NE exterior: x > sw or plan_y < 0
        px, _, pz = ext.position
        assert px > sw or pz < 0, "exterior_quarter should be outside site footprint"

    def test_living_interior_camera_inside_bbox(self, sample):
        cams = {c.name: c for c in derive_cameras(sample)}
        interior = cams["living_interior"]
        sw, sd = sample.site.width, sample.site.depth
        px, _, pz = interior.position
        assert 0 <= px <= sw and 0 <= pz <= sd, "living_interior should be inside site"

    def test_balcony_view_present_when_balcony_room(self, sample):
        cams = {c.name: c for c in derive_cameras(sample)}
        assert "balcony_view" in cams

    def test_positions_have_three_components(self, sample):
        for cam in derive_cameras(sample):
            assert len(cam.position) == 3
            assert len(cam.target) == 3

    def test_descriptions_non_empty(self, sample):
        for cam in derive_cameras(sample):
            assert cam.description, f"camera '{cam.name}' has empty description"

    def test_cameras_api_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        # Use sample endpoint to get a valid project ID, then cameras
        from app.core.storage import get_project_store
        from app.core.architecture.sample_factory import create_sample_project
        store = get_project_store()
        sp = store.create_project("render-cam-test")
        store.update_project(sp.id, project=create_sample_project())
        resp = client.get(f"/projects/{sp.id}/cameras")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert all("name" in c and "position" in c and "target" in c for c in data)


# ── Stage 17.1 — Render-friendly export (Blender naming) ─────────────────────

class TestBlenderRenderReady:
    @pytest.fixture
    def script(self, sample, tmp_path):
        out = tmp_path / "floor_plan_blender.py"
        export_blender(sample, out)
        return out.read_text(encoding="utf-8")

    def test_scotch_wall_prefix_in_objects(self, script):
        assert "Scotch_Wall_" in script

    def test_scotch_floor_prefix_in_objects(self, script):
        assert "Scotch_Floor_" in script

    def test_scotch_roof_in_script(self, script):
        assert "Scotch_Roof" in script

    def test_scotch_glass_prefix_in_objects(self, script):
        assert "Scotch_Glass_" in script

    def test_scotch_ground_in_script(self, script):
        assert "Scotch_Ground" in script

    def test_collection_names_follow_scheme(self, script):
        for col in ("Scotch_Walls", "Scotch_Floors", "Scotch_Roof", "Scotch_Glass", "Scotch_Site"):
            assert col in script, f"collection '{col}' missing from Blender script"

    def test_valid_python(self, script):
        ast.parse(script)

    def test_material_color_from_project_materials(self, script):
        # Material hints from project.materials should appear in the script
        assert "scotch_mat(" in script

    def test_cycles_comment_present(self, script):
        assert "CYCLES" in script

    def test_headless_render_note(self, script):
        assert "--background" in script


# ── Stage 17.1 — Render-friendly export (SketchUp naming) ────────────────────

class TestSketchUpRenderReady:
    @pytest.fixture
    def script(self, sample, tmp_path):
        out = tmp_path / "floor_plan.rb"
        export_sketchup(sample, out)
        return out.read_text(encoding="utf-8")

    def test_scotch_room_group_names(self, script):
        assert "Scotch_Room_" in script

    def test_scotch_ground_group_name(self, script):
        assert "Scotch_Ground" in script

    def test_scotch_roof_group_name(self, script):
        assert "Scotch_Roof" in script

    def test_scotch_glass_material(self, script):
        assert "Scotch_Glass" in script

    def test_scotch_wall_material(self, script):
        assert "Scotch_Wall" in script


# ── Stage 17.4 — Blender automation (cameras + lights) ───────────────────────

class TestBlenderAutomation:
    @pytest.fixture
    def script(self, sample, tmp_path):
        out = tmp_path / "floor_plan_blender.py"
        export_blender(sample, out)
        return out.read_text(encoding="utf-8")

    def test_five_camera_definitions(self, script):
        # Each camera is defined as 'cam_<name>_data = bpy.data.cameras.new(...)'
        count = script.count("bpy.data.cameras.new(")
        assert count == 5

    def test_sun_key_light(self, script):
        assert "Scotch_Sun_Key" in script

    def test_area_fill_light(self, script):
        assert "Scotch_Area_Fill" in script

    def test_rim_light(self, script):
        assert "Scotch_Sun_Rim" in script

    def test_eevee_render_engine(self, script):
        assert "BLENDER_EEVEE" in script

    def test_resolution_1920x1080(self, script):
        assert "resolution_x     = 1920" in script
        assert "resolution_y     = 1080" in script

    def test_render_output_path(self, script):
        assert "render.filepath" in script

    def test_world_background(self, script):
        assert "scene.world" in script

    def test_track_to_constraint(self, script):
        assert "TRACK_TO" in script
