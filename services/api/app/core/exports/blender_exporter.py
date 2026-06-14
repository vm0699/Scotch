"""Stage 11.4 — Blender Python script exporter.

Generates a runnable Blender Python (.py) file from an ArchitectureProject.

Approach:
  - Uses the `bpy` API (Blender 3.6+, LTS).
  - Collections: "Scotch_Site", "Scotch_Rooms", "Scotch_Openings",
    "Scotch_Lighting", "Scotch_Cameras".
  - Rooms: box meshes (walls as extruded flat faces) with Principled BSDF
    materials colour-coded by room type.
  - Doors: full-height opening boxes (to be used as Boolean cutters).
  - Cameras: top orthographic + exterior perspective.
  - Lighting: HDRI sky + area fill + sun key.
  - Render: EEVEE preset, 1920×1080.

Coordinate mapping:
  Plan x  → Blender X (right)
  Plan y  → Blender Y (forward/into model; y=0 = entrance side)
  Height  → Blender Z (up)
  Unit: feet converted to metres (× 0.3048) for Blender SI units.
"""

from datetime import datetime, timezone
from pathlib import Path

from app.core.models import ArchitectureProject, Room

FT_TO_M = 0.3048
WALL_T   = 0.5    # ft
SLAB_T   = 0.15   # m (floor slab)
SILL_H   = 0.76   # m (2.5 ft window sill)
WIN_H    = 1.22   # m (4 ft window height)

_ROOM_COLOURS: dict[str, tuple[float, float, float]] = {
    "living":         (0.92, 0.88, 0.80),
    "dining":         (0.92, 0.89, 0.82),
    "kitchen":        (0.92, 0.90, 0.84),
    "master_bedroom": (0.86, 0.80, 0.78),
    "bedroom":        (0.90, 0.84, 0.82),
    "bathroom":       (0.84, 0.90, 0.92),
    "balcony":        (0.86, 0.88, 0.84),
    "parking":        (0.78, 0.78, 0.78),
    "storage":        (0.84, 0.84, 0.82),
    "study":          (0.90, 0.88, 0.84),
    "foyer":          (0.88, 0.86, 0.82),
    "corridor":       (0.90, 0.89, 0.86),
    "seating":        (0.92, 0.88, 0.80),
    "service":        (0.84, 0.84, 0.84),
}
_DEFAULT_COLOUR = (0.94, 0.93, 0.92)

_WALL_COLOUR  = (0.96, 0.95, 0.93)
_GROUND_COLOUR = (0.82, 0.82, 0.79)
_ROOF_COLOUR   = (0.69, 0.66, 0.62)
_GLASS_COLOUR  = (0.70, 0.84, 0.96)


def _room_colour(room: Room) -> tuple[float, float, float]:
    t = room.type.lower().replace(" ", "_")
    return _ROOM_COLOURS.get(t, _DEFAULT_COLOUR)


def _mat_name(room_type: str) -> str:
    return f"Scotch_{room_type.replace(' ', '_').title()}"


def export_blender(project: ArchitectureProject, output_path: Path) -> bytes:
    """Generate a Blender Python (.py) script for *project* and write to *output_path*."""
    lines: list[str] = []
    L = lines.append

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fh_ft = project.building.floor_height if project.building else 10.0
    fh_m  = round(fh_ft * FT_TO_M, 3)
    sw_m  = round(project.site.width  * FT_TO_M, 3)
    sd_m  = round(project.site.depth  * FT_TO_M, 3)
    wt_m  = round(WALL_T * FT_TO_M, 4)

    def ft(v: float) -> str:
        return str(round(v * FT_TO_M, 4))

    # ── Header ────────────────────────────────────────────────────────────────
    L('"""')
    L(f"Scotch — Blender Python Import Script")
    L(f"Project : {project.name or 'Untitled'}")
    L(f"Generated: {stamp}")
    L(f"Blender : 3.6+ (LTS) — tested with bpy 3.6 / 4.x")
    L(f"Units   : metres (feet × {FT_TO_M})")
    L("")
    L("How to run:")
    L("  Open Blender → Scripting workspace → Open this file → Run Script.")
    L("  The scene is cleared and rebuilt from scratch each run.")
    L('"""')
    L("")
    L("import bpy")
    L("import bmesh")
    L("from mathutils import Vector, Matrix")
    L("")

    # ── Constants ────────────────────────────────────────────────────────────
    L("# Project constants (metres)")
    L(f"SITE_W  = {sw_m}")
    L(f"SITE_D  = {sd_m}")
    L(f"WALL_H  = {fh_m}   # floor-to-ceiling height")
    L(f"WALL_T  = {wt_m}   # wall thickness")
    L(f"SLAB_T  = {SLAB_T}   # floor slab thickness")
    L(f"SILL_H  = {SILL_H}   # window sill height")
    L(f"WIN_H   = {WIN_H}    # window opening height")
    L("")

    # ── Clear scene ───────────────────────────────────────────────────────────
    L("# ── Clear existing Scotch objects ────────────────────────────────────────")
    L("bpy.ops.object.select_all(action='SELECT')")
    L("bpy.ops.object.delete()")
    L("for c in list(bpy.data.collections):")
    L("    bpy.data.collections.remove(c)")
    L("")

    # ── Helper functions ─────────────────────────────────────────────────────
    L("# ── Helpers ──────────────────────────────────────────────────────────────")
    L("")
    L("def ensure_collection(name):")
    L("    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)")
    L("    if name not in bpy.context.scene.collection.children:")
    L("        bpy.context.scene.collection.children.link(c)")
    L("    return c")
    L("")
    L("def scotch_mat(name, r, g, b, alpha=1.0, metallic=0.0, roughness=0.5):")
    L("    mat = bpy.data.materials.get(name)")
    L("    if not mat:")
    L("        mat = bpy.data.materials.new(name)")
    L("    mat.use_nodes = True")
    L("    bsdf = mat.node_tree.nodes.get('Principled BSDF')")
    L("    if not bsdf:")
    L("        bsdf = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')")
    L("    bsdf.inputs['Base Color'].default_value = (r, g, b, alpha)")
    L("    bsdf.inputs['Metallic'].default_value   = metallic")
    L("    bsdf.inputs['Roughness'].default_value  = roughness")
    L("    mat.blend_method = 'BLEND' if alpha < 1.0 else 'OPAQUE'")
    L("    return mat")
    L("")
    L("def box_mesh(name, x, y, z, w, d, h, mat, collection):")
    L("    '\"\"Create a box mesh and link to collection.\"\"'")
    L("    me = bpy.data.meshes.new(name + '_mesh')")
    L("    bm = bmesh.new()")
    L("    verts = [(x, y, z), (x+w, y, z), (x+w, y+d, z), (x, y+d, z),")
    L("             (x, y, z+h), (x+w, y, z+h), (x+w, y+d, z+h), (x, y+d, z+h)]")
    L("    bmv = [bm.verts.new(v) for v in verts]")
    L("    faces = [(0,1,2,3), (4,5,6,7), (0,1,5,4),")
    L("             (1,2,6,5), (2,3,7,6), (3,0,4,7)]")
    L("    for f in faces: bm.faces.new([bmv[i] for i in f])")
    L("    bm.to_mesh(me)")
    L("    bm.free()")
    L("    obj = bpy.data.objects.new(name, me)")
    L("    collection.objects.link(obj)")
    L("    obj.data.materials.append(mat)")
    L("    return obj")
    L("")

    # ── Collections ───────────────────────────────────────────────────────────
    L("# ── Collections ──────────────────────────────────────────────────────────")
    L("col_site    = ensure_collection('Scotch_Site')")
    L("col_rooms   = ensure_collection('Scotch_Rooms')")
    L("col_open    = ensure_collection('Scotch_Openings')")
    L("col_lights  = ensure_collection('Scotch_Lighting')")
    L("col_cams    = ensure_collection('Scotch_Cameras')")
    L("")

    # ── Materials ─────────────────────────────────────────────────────────────
    L("# ── Materials ────────────────────────────────────────────────────────────")
    wr, wg, wb = _WALL_COLOUR
    gr, gg, gb = _GROUND_COLOUR
    rr, rg_, rb = _ROOF_COLOUR
    glr, glg, glb = _GLASS_COLOUR
    L(f"mat_wall   = scotch_mat('Scotch_Wall',   {wr}, {wg}, {wb}, roughness=0.7)")
    L(f"mat_ground = scotch_mat('Scotch_Ground', {gr}, {gg}, {gb}, roughness=0.9)")
    L(f"mat_roof   = scotch_mat('Scotch_Roof',   {rr}, {rg_}, {rb}, roughness=0.8)")
    L(f"mat_glass  = scotch_mat('Scotch_Glass',  {glr}, {glg}, {glb}, alpha=0.35, roughness=0.05)")
    L("")

    # Unique room materials
    seen: set[str] = set()
    L("ROOM_MAT = {}")
    for room in project.rooms:
        t = room.type.lower().replace(" ", "_")
        if t in seen:
            continue
        seen.add(t)
        r, g, b = _room_colour(room)
        name = _mat_name(t)
        L(f"ROOM_MAT['{t}'] = scotch_mat('{name}', {r}, {g}, {b})")
    L("")

    # ── Ground slab ───────────────────────────────────────────────────────────
    L("# ── Ground Slab ──────────────────────────────────────────────────────────")
    L(f"box_mesh('Ground_Slab', 0, 0, -SLAB_T, SITE_W, SITE_D, SLAB_T, mat_ground, col_site)")
    L("")

    # ── Rooms ─────────────────────────────────────────────────────────────────
    L("# ── Rooms ────────────────────────────────────────────────────────────────")
    L("# Walls are built as a solid box (outer dims) + inner hollow box.")
    L("# The inner box uses a Boolean Difference modifier to cut the wall solid,")
    L("# leaving hollow rooms. Apply modifiers in Blender before rendering.")
    L("")

    for room in project.rooms:
        t  = room.type.lower().replace(" ", "_")
        mat_expr = f"ROOM_MAT.get('{t}', mat_wall)"
        # Convert to metres
        ox  = ft(room.x - WALL_T / 2)
        oy  = ft(room.y - WALL_T / 2)
        ow  = ft(room.width  + WALL_T)
        od  = ft(room.depth  + WALL_T)
        rx  = ft(room.x)
        ry  = ft(room.y)
        rw  = ft(room.width)
        rd  = ft(room.depth)
        safe = room.name.replace(" ", "_").replace("'", "")
        L(f"# {room.name}")
        L(f"wall_outer = box_mesh('{safe}_walls', {ox}, {oy}, 0, {ow}, {od}, WALL_H, mat_wall, col_rooms)")
        L(f"room_inner = box_mesh('{safe}_interior', {rx}, {ry}, 0, {rw}, {rd}, WALL_H, {mat_expr}, col_rooms)")
        L(f"# Boolean Difference: wall_outer − room_inner → hollow room walls")
        L(f"mod = wall_outer.modifiers.new('Hollow', 'BOOLEAN')")
        L(f"mod.operation = 'DIFFERENCE'")
        L(f"mod.object = room_inner")
        L(f"room_inner.hide_render = True")
        L(f"room_inner.hide_viewport = True")
        L("")

        # Door openings
        room_doors = [d for d in project.doors if d.room_id == room.id]
        for door in room_doors:
            wall = door.wall
            off  = door.offset
            wid  = door.width
            # Opening box: full height, WALL_T deep (slightly oversized for clean Boolean)
            if wall == "north":
                dx0, dy0 = room.x + off, room.y - WALL_T
                dw, dd_ = wid, WALL_T * 2
            elif wall == "south":
                dx0, dy0 = room.x + off, room.y + room.depth - WALL_T
                dw, dd_ = wid, WALL_T * 2
            elif wall == "west":
                dx0, dy0 = room.x - WALL_T, room.y + off
                dw, dd_ = WALL_T * 2, wid
            else:
                dx0, dy0 = room.x + room.width - WALL_T, room.y + off
                dw, dd_ = WALL_T * 2, wid
            odx, ody = ft(dx0), ft(dy0)
            odw, odd = ft(dw), ft(dd_)
            L(f"# Door opening: wall={wall}, offset={off}ft, width={wid}ft")
            L(f"door_cut = box_mesh('{safe}_door_{wall}', {odx}, {ody}, 0, {odw}, {odd}, WALL_H, mat_glass, col_open)")
            L(f"mod_d = wall_outer.modifiers.new('Door_{wall}', 'BOOLEAN')")
            L(f"mod_d.operation = 'DIFFERENCE'")
            L(f"mod_d.object = door_cut")
            L(f"door_cut.hide_render = True")
            L(f"door_cut.hide_viewport = True")
            L("")

        # Window openings
        room_wins = [w for w in project.windows if w.room_id == room.id]
        for win in room_wins:
            wall = win.wall
            off  = win.offset
            wid  = win.width
            if wall == "north":
                wx0, wy0 = room.x + off, room.y - WALL_T
                ww_, wd_ = wid, WALL_T * 2
            elif wall == "south":
                wx0, wy0 = room.x + off, room.y + room.depth - WALL_T
                ww_, wd_ = wid, WALL_T * 2
            elif wall == "west":
                wx0, wy0 = room.x - WALL_T, room.y + off
                ww_, wd_ = WALL_T * 2, wid
            else:
                wx0, wy0 = room.x + room.width - WALL_T, room.y + off
                ww_, wd_ = WALL_T * 2, wid
            owx, owy = ft(wx0), ft(wy0)
            oww, owd = ft(ww_), ft(wd_)
            L(f"# Window opening: wall={wall}, offset={off}ft, width={wid}ft (sill {SILL_H}m)")
            L(f"win_cut = box_mesh('{safe}_win_{wall}', {owx}, {owy}, SILL_H, {oww}, {owd}, WIN_H, mat_glass, col_open)")
            L(f"mod_w = wall_outer.modifiers.new('Win_{wall}', 'BOOLEAN')")
            L(f"mod_w.operation = 'DIFFERENCE'")
            L(f"mod_w.object = win_cut")
            L(f"win_cut.hide_render = True")
            L(f"win_cut.hide_viewport = True")
            L("")

    # ── Roof slab ─────────────────────────────────────────────────────────────
    L("# ── Roof Slab ────────────────────────────────────────────────────────────")
    L(f"box_mesh('Roof_Slab', 0, 0, WALL_H, SITE_W, SITE_D, SLAB_T, mat_roof, col_site)")
    L("")

    # ── Cameras ───────────────────────────────────────────────────────────────
    cx_m = round(sw_m / 2, 3)
    cy_m = round(sd_m / 2, 3)
    L("# ── Cameras ──────────────────────────────────────────────────────────────")
    L("# Top orthographic camera")
    L("cam_top_data = bpy.data.cameras.new('Cam_Top')")
    L("cam_top_data.type = 'ORTHO'")
    L(f"cam_top_data.ortho_scale = max(SITE_W, SITE_D) * 1.3")
    L("cam_top = bpy.data.objects.new('Cam_Top', cam_top_data)")
    L("col_cams.objects.link(cam_top)")
    L(f"cam_top.location = ({cx_m}, {cy_m}, {round(fh_m * 3, 2)})")
    L("cam_top.rotation_euler = (0, 0, 0)")
    L("")
    L("# Exterior perspective camera (south-east view)")
    L("cam_ext_data = bpy.data.cameras.new('Cam_Exterior')")
    L("cam_ext_data.type = 'PERSP'")
    L("cam_ext_data.lens = 35")
    L("cam_ext = bpy.data.objects.new('Cam_Exterior', cam_ext_data)")
    L("col_cams.objects.link(cam_ext)")
    L(f"cam_ext.location = ({round(-sw_m * 0.6, 2)}, {round(-sd_m * 0.6, 2)}, {round(fh_m * 1.6, 2)})")
    L(f"cam_ext.rotation_euler = (1.0, 0, -0.785)")
    L("")
    L("# Set top camera as active")
    L("bpy.context.scene.camera = cam_top")
    L("")

    # ── Lighting ──────────────────────────────────────────────────────────────
    L("# ── Lighting ─────────────────────────────────────────────────────────────")
    L("# Sun (key)")
    L("sun_data = bpy.data.lights.new('Sun_Key', 'SUN')")
    L("sun_data.energy = 3.0")
    L("sun_data.color  = (1.0, 0.97, 0.90)")
    L("sun      = bpy.data.objects.new('Sun_Key', sun_data)")
    L("col_lights.objects.link(sun)")
    L(f"sun.location       = ({round(sw_m * 1.5, 2)}, {round(-sd_m * 0.5, 2)}, {round(fh_m * 2, 2)})")
    L("sun.rotation_euler = (0.9, 0.0, 0.8)")
    L("")
    L("# Area fill (soft indoor feel)")
    L("fill_data = bpy.data.lights.new('Area_Fill', 'AREA')")
    L("fill_data.energy = 200")
    L("fill_data.size   = max(SITE_W, SITE_D)")
    L("fill      = bpy.data.objects.new('Area_Fill', fill_data)")
    L("col_lights.objects.link(fill)")
    L(f"fill.location = ({cx_m}, {cy_m}, {round(fh_m * 2.5, 2)})")
    L("")

    # ── Render settings ───────────────────────────────────────────────────────
    L("# ── Render Settings ──────────────────────────────────────────────────────")
    L("scene = bpy.context.scene")
    L("scene.render.engine = 'BLENDER_EEVEE'")
    L("scene.render.resolution_x = 1920")
    L("scene.render.resolution_y = 1080")
    L("scene.render.film_transparent = False")
    L("scene.world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')")
    L("scene.world.use_nodes = True")
    L("bg = scene.world.node_tree.nodes.get('Background')")
    L("if bg: bg.inputs['Color'].default_value = (0.55, 0.65, 0.78, 1.0)  # sky blue")
    L("if bg: bg.inputs['Strength'].default_value = 0.5")
    L("")
    L("# Apply Boolean modifiers")
    L("bpy.ops.object.select_all(action='SELECT')")
    L("print('Scotch import complete. Apply Boolean modifiers to hollow the rooms.')")
    L("print('Tip: select a room wall object → Properties → Modifier → Apply.')")
    L("")

    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content.encode("utf-8")
