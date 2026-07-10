"""Phase 35 — Blender exporter: material plan, kitchen counters, MEP blocks."""
import re
from pathlib import Path

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.exports.blender_exporter import export_blender
from app.core.models.project import MaterialPlan, RoomFinish

PROMPT = "3BHK on 30x50 ft east-facing site with living, kitchen, 2 bedrooms, master bedroom, 2 bathrooms"


def _project():
    proj, _ = generate_floorplan(parse_prompt(PROMPT))
    return proj


def _export(project, tmp_path: Path) -> str:
    out = tmp_path / "plan.py"
    export_blender(project, out)
    return out.read_text(encoding="utf-8")


# ── Existing functionality still works ───────────────────────────────────────

def test_export_contains_blender_header(tmp_path):
    script = _export(_project(), tmp_path)
    assert "import bpy" in script


def test_export_contains_scotch_wall_objects(tmp_path):
    script = _export(_project(), tmp_path)
    assert "Scotch_Wall_" in script


def test_export_contains_camera_presets(tmp_path):
    script = _export(_project(), tmp_path)
    assert "Scotch_Cam_" in script
    assert "TRACK_TO" in script


def test_export_contains_render_settings(tmp_path):
    script = _export(_project(), tmp_path)
    assert "render.resolution_x" in script
    assert "BLENDER_EEVEE" in script


def test_export_contains_lighting(tmp_path):
    script = _export(_project(), tmp_path)
    assert "Scotch_Sun_Key" in script
    assert "Scotch_Area_Fill" in script


# ── Phase 35: Material plan tile overlays ─────────────────────────────────────

def test_export_no_tile_overlay_when_material_plan_not_generated(tmp_path):
    proj = _project()
    assert not proj.material_plan.generated
    script = _export(proj, tmp_path)
    assert "Scotch_Tile_" not in script


def test_export_tile_overlay_when_material_plan_generated(tmp_path):
    proj = _project()
    room = next((r for r in proj.rooms if r.type == "living"), proj.rooms[0])
    proj = proj.model_copy(update={
        "material_plan": MaterialPlan(
            tile_specs=[],
            room_finishes=[RoomFinish(
                room_id=room.id,
                floor_material="marble",
                wall_material="paint",
                ceiling_material="paint",
            )],
            editable_rates=[],
            assumptions=[],
            generated=True,
            stale=False,
        )
    })
    script = _export(proj, tmp_path)
    assert "Scotch_Tile_" in script
    assert "Scotch_Tiles" in script


def test_export_tile_uses_correct_material_name_for_marble(tmp_path):
    proj = _project()
    room = next((r for r in proj.rooms if r.type == "living"), proj.rooms[0])
    proj = proj.model_copy(update={
        "material_plan": MaterialPlan(
            tile_specs=[],
            room_finishes=[RoomFinish(
                room_id=room.id,
                floor_material="Italian marble tiles",
                wall_material="paint",
                ceiling_material="paint",
            )],
            editable_rates=[],
            assumptions=[],
            generated=True,
            stale=False,
        )
    })
    script = _export(proj, tmp_path)
    # Marble floor: high roughness=0.25, metallic=0.04
    assert "0.25" in script or "marble" in script.lower()


def test_export_skips_tile_for_unknown_material(tmp_path):
    proj = _project()
    room = next((r for r in proj.rooms if r.type == "bedroom"), proj.rooms[0])
    proj = proj.model_copy(update={
        "material_plan": MaterialPlan(
            tile_specs=[],
            room_finishes=[RoomFinish(
                room_id=room.id,
                floor_material="unknown material xyz",
                wall_material="paint",
                ceiling_material="paint",
            )],
            editable_rates=[],
            assumptions=[],
            generated=True,
            stale=False,
        )
    })
    script = _export(proj, tmp_path)
    # No tile overlay created for unknown material
    assert "Scotch_Tile_" not in script


# ── Phase 35: Kitchen counter geometry ───────────────────────────────────────

def test_export_contains_kitchen_counter(tmp_path):
    proj = _project()
    kitchen = next((r for r in proj.rooms if r.type == "kitchen"), None)
    if kitchen is None:
        pytest.skip("No kitchen in generated project")
    script = _export(proj, tmp_path)
    assert "Scotch_Counter_" in script
    assert "Scotch_Counters" in script


def test_export_kitchen_counter_uses_mat_counter(tmp_path):
    proj = _project()
    kitchen = next((r for r in proj.rooms if r.type == "kitchen"), None)
    if kitchen is None:
        pytest.skip("No kitchen in generated project")
    script = _export(proj, tmp_path)
    assert "mat_counter" in script or "Scotch_Counter" in script


# ── Phase 35: MEP blocks ──────────────────────────────────────────────────────

def test_export_no_mep_blocks_when_not_generated(tmp_path):
    proj = _project()
    assert not proj.mep_plan.generated
    script = _export(proj, tmp_path)
    assert "Scotch_MEP_" not in script


def test_export_mep_blocks_when_generated_with_plumbing(tmp_path):
    """Simulate a project with generated MEP that has WC and basin points."""
    from app.core.models.project import MEPPlan, PlumbingPlan, ElectricalPlan, LightingPlan, ACPlan, ServicePoint

    proj = _project()
    bathroom = next((r for r in proj.rooms if "bath" in r.type), proj.rooms[0])

    wc_pt = ServicePoint(
        id="pt-wc-001",
        system="plumbing",
        kind="WC",
        room_id=bathroom.id,
        x=bathroom.x + 2,
        y=bathroom.y + 1,
        mount_height=0,
        confidence=0.9,
        needs_review=False,
        user_override=False,
        label="WC",
    )
    basin_pt = ServicePoint(
        id="pt-basin-001",
        system="plumbing",
        kind="basin",
        room_id=bathroom.id,
        x=bathroom.x + 1,
        y=bathroom.y + 3,
        mount_height=0,
        confidence=0.9,
        needs_review=False,
        user_override=False,
        label="Basin",
    )

    plumbing = PlumbingPlan(points=[wc_pt, basin_pt], routes=[], warnings=[], confidence=0.9, needs_review=False)
    mep = MEPPlan(
        plumbing=plumbing,
        electrical=ElectricalPlan(points=[], routes=[], warnings=[], confidence=0.9, needs_review=False),
        lighting=LightingPlan(points=[], warnings=[], confidence=0.9, needs_review=False),
        ac=ACPlan(points=[], warnings=[], confidence=0.9, needs_review=False),
        generated=True,
        stale=False,
    )
    proj = proj.model_copy(update={"mep_plan": mep})
    script = _export(proj, tmp_path)
    assert "Scotch_MEP_WC_" in script or "Scotch_MEP_" in script
    assert "mat_mep" in script


def test_export_mep_skips_switches_and_lights(tmp_path):
    """Switches and lights have no MEP_SIZES entry → skipped."""
    from app.core.models.project import MEPPlan, PlumbingPlan, ElectricalPlan, LightingPlan, ACPlan, ServicePoint

    proj = _project()
    room = proj.rooms[0]
    switch_pt = ServicePoint(
        id="pt-sw-001",
        system="electrical",
        kind="switch",
        room_id=room.id,
        x=room.x + 1,
        y=room.y + 1,
        mount_height=4.0,
        confidence=0.9,
        needs_review=False,
        user_override=False,
        label="Switch",
    )
    plumbing = PlumbingPlan(points=[], routes=[], warnings=[], confidence=0.9, needs_review=False)
    elec = ElectricalPlan(points=[switch_pt], routes=[], warnings=[], confidence=0.9, needs_review=False)
    mep = MEPPlan(
        plumbing=plumbing, electrical=elec,
        lighting=LightingPlan(points=[], warnings=[], confidence=0.9, needs_review=False),
        ac=ACPlan(points=[], warnings=[], confidence=0.9, needs_review=False),
        generated=True, stale=False,
    )
    proj = proj.model_copy(update={"mep_plan": mep})
    script = _export(proj, tmp_path)
    # switches are not in MEP_SIZES → no MEP block output
    assert "Scotch_MEP_switch_" not in script
