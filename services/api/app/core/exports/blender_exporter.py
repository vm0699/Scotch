"""Stage 11.4 / 17.1 / 17.4 — Blender Python script exporter (render-ready).

Generates a runnable Blender Python (.py) file from an ArchitectureProject.

Phase 17 improvements:
  - Object/collection naming follows the Scotch render-ready hierarchy:
      Collections: Scotch_Site, Scotch_Walls, Scotch_Floors, Scotch_Roof,
                   Scotch_Glass, Scotch_Lighting, Scotch_Cameras
      Objects:     Scotch_Wall_{room}, Scotch_Floor_{room}, Scotch_Roof,
                   Scotch_Ground, Scotch_Glass_{room}_{Door|Win}_{wall}
    Render engines can map materials by object-name prefix.
  - 5 camera presets derived from site + room geometry (stage 17.3 cameras).
  - Headless --background render note with output path example.
  - Cycles render preset included as an alternative to EEVEE.
  - Material records from project.materials flow into Blender material creation.

Coordinate mapping:
  Plan x  → Blender X (right)
  Plan y  → Blender Y (forward/into model; y=0 = entrance side)
  Height  → Blender Z (up)
  Unit: feet converted to metres (× 0.3048) for Blender SI units.
"""

from datetime import datetime, timezone
from pathlib import Path

from app.core.architecture.cameras import derive_cameras
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
    "kitchenette":    (0.92, 0.90, 0.84),  # same tone as kitchen — same function, smaller room
    "master_bedroom": (0.86, 0.80, 0.78),
    "bedroom":        (0.90, 0.84, 0.82),
    "bathroom":       (0.84, 0.90, 0.92),
    "restroom":       (0.84, 0.90, 0.92),  # same tone as bathroom — WC+basin without the tub
    "balcony":        (0.86, 0.88, 0.84),
    "parking":        (0.78, 0.78, 0.78),
    "storage":        (0.84, 0.84, 0.82),
    "study":          (0.90, 0.88, 0.84),
    "office":         (0.90, 0.88, 0.84),  # same tone as study — both are workspace rooms
    "foyer":          (0.88, 0.86, 0.82),
    "corridor":       (0.90, 0.89, 0.86),
    "seating":        (0.92, 0.88, 0.80),
    "cafe_seating":   (0.92, 0.88, 0.80),  # same tone as seating/living — a café's public seating
    "cafe_counter":   (0.92, 0.90, 0.84),  # same tone as kitchen — service/prep function
    "service":        (0.84, 0.84, 0.84),
}
_DEFAULT_COLOUR = (0.94, 0.93, 0.92)

_WALL_COLOUR   = (0.96, 0.95, 0.93)
_GROUND_COLOUR = (0.82, 0.82, 0.79)
_ROOF_COLOUR   = (0.69, 0.66, 0.62)
_GLASS_COLOUR  = (0.70, 0.84, 0.96)


def _room_colour(room: Room) -> tuple[float, float, float]:
    t = room.type.lower().replace(" ", "_")
    return _ROOM_COLOURS.get(t, _DEFAULT_COLOUR)


def _mat_name(room_type: str) -> str:
    return f"Scotch_{room_type.replace(' ', '_').title()}"


def _safe(name: str) -> str:
    return name.replace(" ", "_").replace("'", "").replace("-", "_")


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
    L("Scotch — Blender Python Import Script  (render-ready, Phase 17)")
    L(f"Project : {project.name or 'Untitled'}")
    L(f"Generated: {stamp}")
    L(f"Blender  : 3.6+ (LTS) / 4.x — tested with bpy 3.6 / 4.x")
    L(f"Units    : metres (feet × {FT_TO_M})")
    L("")
    L("How to run (interactive):")
    L("  Open Blender → Scripting workspace → Open this file → Run Script.")
    L("  The scene is cleared and rebuilt from scratch each run.")
    L("")
    L("How to render headless (Blender --background):")
    L("  blender --background --python floor_plan_blender.py -- --render-anim")
    L("  Output is written to /tmp/scotch_render/ by default (see render settings).")
    L('"""')
    L("")
    L("import bpy")
    L("import bmesh")
    L("from mathutils import Vector, Matrix, Euler")
    L("import math")
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
    L("# ── Clear existing objects ───────────────────────────────────────────────")
    L("bpy.ops.object.select_all(action='SELECT')")
    L("bpy.ops.object.delete()")
    L("for c in list(bpy.data.collections):")
    L("    bpy.data.collections.remove(c)")
    L("")

    # ── Helper functions ─────────────────────────────────────────────────────
    L("# ── Helpers ──────────────────────────────────────────────────────────────")
    L("")
    L("def ensure_collection(name, parent=None):")
    L("    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)")
    L("    root = parent or bpy.context.scene.collection")
    L("    if name not in [ch.name for ch in root.children]:")
    L("        root.children.link(c)")
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

    # ── Collections (render-ready hierarchy) ─────────────────────────────────
    L("# ── Collections — render-ready Scotch hierarchy ──────────────────────────")
    L("# Render engines can map materials by collection or object-name prefix.")
    L("col_site   = ensure_collection('Scotch_Site')")
    L("col_walls  = ensure_collection('Scotch_Walls')")
    L("col_floors = ensure_collection('Scotch_Floors')")
    L("col_roof   = ensure_collection('Scotch_Roof')")
    L("col_glass  = ensure_collection('Scotch_Glass')")
    L("col_lights = ensure_collection('Scotch_Lighting')")
    L("col_cams   = ensure_collection('Scotch_Cameras')")
    L("")

    # ── Materials ─────────────────────────────────────────────────────────────
    L("# ── Materials ────────────────────────────────────────────────────────────")

    # Use material hints from project.materials if available; fall back to defaults
    mat_hints: dict[str, tuple] = {}
    for m in (project.materials or []):
        # Convert hex to float RGB
        hx = m.base_color.lstrip("#")
        if len(hx) == 6:
            r = int(hx[0:2], 16) / 255
            g = int(hx[2:4], 16) / 255
            b = int(hx[4:6], 16) / 255
            mat_hints[m.target] = (r, g, b, m.roughness, m.metallic)

    def _rgb(target: str, default_rgb: tuple, default_r: float = 0.5) -> str:
        if target in mat_hints:
            r, g, b, ro, me = mat_hints[target]
            return f"{r:.3f}, {g:.3f}, {b:.3f}, roughness={ro}, metallic={me}"
        r, g, b = default_rgb
        return f"{r}, {g}, {b}, roughness={default_r}"

    wr, wg, wb = _WALL_COLOUR
    gr, gg, gb = _GROUND_COLOUR
    rr, rg_, rb = _ROOF_COLOUR
    glr, glg, glb = _GLASS_COLOUR

    L(f"mat_wall   = scotch_mat('Scotch_Wall',   {_rgb('wall',   _WALL_COLOUR,   0.70)})")
    L(f"mat_ground = scotch_mat('Scotch_Ground', {_rgb('ground', _GROUND_COLOUR, 0.90)})")
    L(f"mat_roof   = scotch_mat('Scotch_Roof',   {_rgb('roof',   _ROOF_COLOUR,   0.85)})")
    L(f"mat_glass  = scotch_mat('Scotch_Glass',  {glr}, {glg}, {glb}, alpha=0.35, roughness=0.05, metallic=0.15)")
    L("")

    seen: set[str] = set()
    L("ROOM_MAT = {}")
    for room in project.rooms:
        t = room.type.lower().replace(" ", "_")
        if t in seen:
            continue
        seen.add(t)
        target_key = f"room:{t}"
        if target_key in mat_hints:
            r, g, b, ro, me = mat_hints[target_key]
            name = _mat_name(t)
            L(f"ROOM_MAT['{t}'] = scotch_mat('{name}', {r:.3f}, {g:.3f}, {b:.3f}, roughness={ro})")
        else:
            r, g, b = _room_colour(room)
            name = _mat_name(t)
            L(f"ROOM_MAT['{t}'] = scotch_mat('{name}', {r}, {g}, {b})")
    L("")

    # ── Ground slab ───────────────────────────────────────────────────────────
    L("# ── Scotch_Ground ────────────────────────────────────────────────────────")
    L(f"box_mesh('Scotch_Ground', 0, 0, -SLAB_T, SITE_W, SITE_D, SLAB_T, mat_ground, col_site)")
    L("")

    # ── Rooms ─────────────────────────────────────────────────────────────────
    L("# ── Scotch_Walls / Scotch_Floors / Scotch_Glass ─────────────────────────")
    L("# Object names: Scotch_Wall_<room>, Scotch_Floor_<room>, Scotch_Glass_<room>_*")
    L("# Render engines assign materials by object-name prefix automatically.")
    L("")

    for room in project.rooms:
        t   = room.type.lower().replace(" ", "_")
        mat_expr = f"ROOM_MAT.get('{t}', mat_wall)"
        ox  = ft(room.x - WALL_T / 2)
        oy  = ft(room.y - WALL_T / 2)
        ow  = ft(room.width  + WALL_T)
        od  = ft(room.depth  + WALL_T)
        rx  = ft(room.x)
        ry  = ft(room.y)
        rw  = ft(room.width)
        rd  = ft(room.depth)
        safe_name = _safe(room.name)

        L(f"# {room.name}")
        L(f"wall_outer = box_mesh('Scotch_Wall_{safe_name}',  {ox}, {oy}, 0, {ow}, {od}, WALL_H, mat_wall,    col_walls)")
        L(f"room_inner = box_mesh('Scotch_Floor_{safe_name}', {rx}, {ry}, 0, {rw}, {rd}, WALL_H, {mat_expr}, col_floors)")
        L(f"# Boolean Difference: Scotch_Wall − Scotch_Floor → hollow room walls")
        L(f"mod = wall_outer.modifiers.new('Hollow', 'BOOLEAN')")
        L(f"mod.operation = 'DIFFERENCE'")
        L(f"mod.object = room_inner")
        L(f"room_inner.hide_render   = True")
        L(f"room_inner.hide_viewport = True")
        L("")

        # Door openings
        room_doors = [d for d in project.doors if d.room_id == room.id]
        for door in room_doors:
            wall = door.wall
            off  = door.offset
            wid  = door.width
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
            L(f"door_cut = box_mesh('Scotch_Glass_{safe_name}_Door_{wall.title()}', {odx}, {ody}, 0, {odw}, {odd}, WALL_H, mat_glass, col_glass)")
            L(f"mod_d = wall_outer.modifiers.new('Door_{wall}', 'BOOLEAN')")
            L(f"mod_d.operation = 'DIFFERENCE'")
            L(f"mod_d.object = door_cut")
            L(f"door_cut.hide_render   = True")
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
            L(f"win_cut = box_mesh('Scotch_Glass_{safe_name}_Win_{wall.title()}', {owx}, {owy}, SILL_H, {oww}, {owd}, WIN_H, mat_glass, col_glass)")
            L(f"mod_w = wall_outer.modifiers.new('Win_{wall}', 'BOOLEAN')")
            L(f"mod_w.operation = 'DIFFERENCE'")
            L(f"mod_w.object = win_cut")
            L(f"win_cut.hide_render   = True")
            L(f"win_cut.hide_viewport = True")
            L("")

    # ── Furniture ─────────────────────────────────────────────────────────────
    if project.furniture:
        L("# ── Scotch_Furniture ─────────────────────────────────────────────────────")
        L("col_furn = ensure_collection('Scotch_Furniture')")
        L("mat_furn = scotch_mat('Scotch_Furniture', 0.70, 0.63, 0.51, roughness=0.75)")
        L("")
        for item in project.furniture:
            safe_lbl  = _safe(item.label or item.type)
            safe_id   = item.id[:6]
            room = next((r for r in project.rooms if r.id == item.room_id), None)
            base_z_ft = (room.level * project.building.floor_height) if room else 0.0
            ix  = ft(item.x)
            iy  = ft(item.y)
            iz  = ft(base_z_ft)
            iw  = ft(item.width)
            id_ = ft(item.depth)
            ih  = ft(item.height)
            L(f"box_mesh('Scotch_Furniture_{safe_lbl}_{safe_id}', {ix}, {iy}, {iz}, {iw}, {id_}, {ih}, mat_furn, col_furn)")
        L("")

    # ── Phase 35: Floor tile overlays from material_plan ─────────────────────
    if project.material_plan.generated and project.material_plan.room_finishes:
        _TILE_MATS: dict[str, tuple] = {
            "marble":    (0.96, 0.94, 0.92),
            "vitrified": (0.94, 0.92, 0.88),
            "ceramic":   (0.92, 0.90, 0.86),
            "granite":   (0.55, 0.50, 0.46),
            "timber":    (0.62, 0.46, 0.30),
            "concrete":  (0.70, 0.70, 0.70),
            "terrazzo":  (0.88, 0.85, 0.82),
            "hardwood":  (0.55, 0.38, 0.24),
            "stone":     (0.65, 0.62, 0.58),
        }
        L("")
        L("# ── Phase 35: Floor tile overlays from material plan ─────────────────────")
        L("col_tiles = ensure_collection('Scotch_Tiles')")
        L("")
        for finish in project.material_plan.room_finishes:
            room = next((r for r in project.rooms if r.id == finish.room_id), None)
            if not room:
                continue
            mat_lower = finish.floor_material.lower()
            rgb = next((v for k, v in _TILE_MATS.items() if k in mat_lower), None)
            if not rgb:
                continue
            rr2, rg2, rb2 = rgb
            roughness = 0.25 if "marble" in mat_lower else 0.60
            metallic  = 0.04 if "marble" in mat_lower else 0.0
            safe_n = _safe(room.name)
            inset_ft = WALL_T / 2
            rx = ft(room.x + inset_ft)
            ry = ft(room.y + inset_ft)
            rw = ft(max(0.5, room.width  - inset_ft * 2))
            rd = ft(max(0.5, room.depth - inset_ft * 2))
            lvl_z = ft(room.level * (project.building.floor_height or 10.0))
            L(f"# {room.name} — {finish.floor_material}")
            L(f"scotch_mat('Scotch_Tile_{safe_n}', {rr2}, {rg2}, {rb2}, roughness={roughness}, metallic={metallic})")
            L(f"box_mesh('Scotch_Tile_{safe_n}', {rx}, {ry}, {lvl_z}, {rw}, {rd}, 0.02, bpy.data.materials['Scotch_Tile_{safe_n}'], col_tiles)")
        L("")

    # ── Phase 35: Kitchen counter geometry ───────────────────────────────────
    KITCHEN_TYPES = {"kitchen", "kitchenette", "pantry"}
    kitchen_rooms = [r for r in project.rooms if r.type.lower().replace(" ", "_") in KITCHEN_TYPES]
    if kitchen_rooms:
        L("")
        L("# ── Phase 35: Kitchen counters ───────────────────────────────────────────")
        L("col_counters = ensure_collection('Scotch_Counters')")
        L("mat_counter  = scotch_mat('Scotch_Counter', 0.67, 0.60, 0.52, roughness=0.55, metallic=0.05)")
        L("")
        for room in kitchen_rooms:
            safe_n = _safe(room.name)
            inset_ft = WALL_T + 0.05
            counter_depth = 2.0   # ft
            counter_h     = 3.0   # ft
            counter_len   = max(2.0, room.width - inset_ft * 2 - 1.0)
            cx = ft(room.x + inset_ft)
            cy = ft(room.y + inset_ft)
            cw = ft(counter_len)
            cd = ft(counter_depth)
            ch = ft(counter_h)
            lvl_z = ft(room.level * (project.building.floor_height or 10.0))
            L(f"# {room.name} — main worktop counter along north wall")
            L(f"box_mesh('Scotch_Counter_{safe_n}_Main', {cx}, {cy}, {lvl_z}, {cw}, {cd}, {ch}, mat_counter, col_counters)")
            if room.depth > 8:
                ret_len = min(room.depth / 2, 4)
                ret_x = ft(room.x + room.width - inset_ft - counter_depth)
                ret_w = ft(counter_depth)
                ret_d = ft(ret_len)
                L(f"box_mesh('Scotch_Counter_{safe_n}_Return', {ret_x}, {cy}, {lvl_z}, {ret_w}, {ret_d}, {ch}, mat_counter, col_counters)")
        L("")

    # ── Phase 35: MEP 3D blocks ───────────────────────────────────────────────
    if project.mep_plan.generated:
        _MEP_SIZES_BL = {
            "wc":     (ft(1.4), ft(2.0), ft(1.5)),
            "toilet": (ft(1.4), ft(2.0), ft(1.5)),
            "basin":  (ft(1.0), ft(1.5), ft(0.75)),
            "shower": (ft(2.5), ft(3.0), ft(0.15)),
            "bath":   (ft(2.5), ft(5.0), ft(1.8)),
            "ac":     (ft(3.0), ft(1.0), ft(0.7)),
        }
        all_pts = (
            list(project.mep_plan.plumbing.points or [])
            + list(project.mep_plan.ac.points or [])
        )
        if all_pts:
            L("")
            L("# ── Phase 35: MEP service-point blocks ───────────────────────────────────")
            L("col_mep = ensure_collection('Scotch_MEP')")
            L("mat_mep = scotch_mat('Scotch_MEP', 0.73, 0.82, 0.87, roughness=0.45, metallic=0.1)")
            L("")
            for pt in all_pts:
                kind_key = pt.kind.lower().replace(" ", "").replace("-", "")
                mep_sz = _MEP_SIZES_BL.get(kind_key)
                if not mep_sz:
                    continue
                mw, md, mh = mep_sz
                room = next((r for r in project.rooms if r.id == pt.room_id), None)
                base_z = room.level * (project.building.floor_height or 10.0) if room else 0.0
                is_wall = pt.mount_height > 1.0
                z_offset = ft(base_z + (pt.mount_height if is_wall else 0.0))
                px_b = ft(pt.x)
                py_b = ft(pt.y)
                safe_pid = pt.id[:6]
                L(f"box_mesh('Scotch_MEP_{pt.kind}_{safe_pid}', {px_b}, {py_b}, {z_offset}, {mw}, {md}, {mh}, mat_mep, col_mep)")
            L("")

    # ── Roof slab ─────────────────────────────────────────────────────────────
    L("# ── Scotch_Roof ──────────────────────────────────────────────────────────")
    L(f"box_mesh('Scotch_Roof', 0, 0, WALL_H, SITE_W, SITE_D, SLAB_T, mat_roof, col_roof)")
    L("")

    # ── Lighting ──────────────────────────────────────────────────────────────
    L("# ── Scotch_Lighting ─────────────────────────────────────────────────────")
    L("# Sun key light")
    L("sun_data = bpy.data.lights.new('Scotch_Sun_Key', 'SUN')")
    L("sun_data.energy = 3.0")
    L("sun_data.color  = (1.0, 0.97, 0.90)")
    L("sun_data.angle  = math.radians(3.5)   # slight softness")
    L("sun = bpy.data.objects.new('Scotch_Sun_Key', sun_data)")
    L("col_lights.objects.link(sun)")
    L(f"sun.location       = ({round(sw_m * 1.5, 2)}, {round(-sd_m * 0.5, 2)}, {round(fh_m * 2, 2)})")
    L("sun.rotation_euler = Euler((0.9, 0.0, 0.8), 'XYZ')")
    L("")
    L("# Area fill (soft ambient-interior feel)")
    L("fill_data = bpy.data.lights.new('Scotch_Area_Fill', 'AREA')")
    L("fill_data.energy = 200.0")
    L(f"fill_data.size   = max(SITE_W, SITE_D)")
    L("fill = bpy.data.objects.new('Scotch_Area_Fill', fill_data)")
    L("col_lights.objects.link(fill)")
    cx_m = round(sw_m / 2, 3)
    cy_m = round(sd_m / 2, 3)
    L(f"fill.location = ({cx_m}, {cy_m}, {round(fh_m * 2.5, 2)})")
    L("")
    L("# Rim light (back-light from opposite side to sun)")
    L("rim_data = bpy.data.lights.new('Scotch_Sun_Rim', 'SUN')")
    L("rim_data.energy = 0.6")
    L("rim_data.color  = (0.88, 0.95, 1.0)   # cool blue rim")
    L("rim = bpy.data.objects.new('Scotch_Sun_Rim', rim_data)")
    L("col_lights.objects.link(rim)")
    L(f"rim.location       = ({round(-sw_m * 0.8, 2)}, {round(sd_m * 1.2, 2)}, {round(fh_m * 1.5, 2)})")
    L("rim.rotation_euler = Euler((-0.6, 0.0, 2.5), 'XYZ')")
    L("")

    # ── Cameras (derived from project geometry) ───────────────────────────────
    L("# ── Scotch_Cameras — 5 render presets ───────────────────────────────────")

    cameras = derive_cameras(project)
    for i, cam in enumerate(cameras):
        # position[0]=plan_x → Blender X
        # position[2]=plan_y → Blender Y
        # position[1]=height → Blender Z
        px = round(cam.position[0] * FT_TO_M, 3)
        py = round(cam.position[2] * FT_TO_M, 3)
        pz = round(cam.position[1] * FT_TO_M, 3)
        tx = round(cam.target[0] * FT_TO_M, 3)
        ty = round(cam.target[2] * FT_TO_M, 3)
        tz = round(cam.target[1] * FT_TO_M, 3)
        cam_safe = cam.name
        c_type = "'ORTHO'" if cam.type == "orthographic" else "'PERSP'"
        L(f"# {cam.description}")
        L(f"cam_{cam_safe}_data = bpy.data.cameras.new('Scotch_Cam_{cam_safe.title()}')")
        L(f"cam_{cam_safe}_data.type = {c_type}")
        if cam.type == "orthographic":
            L(f"cam_{cam_safe}_data.ortho_scale = max(SITE_W, SITE_D) * 1.3")
        else:
            L(f"cam_{cam_safe}_data.lens = {round(50 / (2 * __import__('math').tan(__import__('math').radians(cam.fov / 2))), 1) if cam.fov > 0 else 35}  # {cam.fov}° fov approx")
        L(f"cam_{cam_safe} = bpy.data.objects.new('Scotch_Cam_{cam_safe.title()}', cam_{cam_safe}_data)")
        L(f"col_cams.objects.link(cam_{cam_safe})")
        L(f"cam_{cam_safe}.location = ({px}, {py}, {pz})")
        # Aim using 'Track to' constraint toward target
        L(f"con = cam_{cam_safe}.constraints.new('TRACK_TO')")
        L(f"empty_{cam_safe} = bpy.data.objects.new('Target_{cam_safe}', None)")
        L(f"col_cams.objects.link(empty_{cam_safe})")
        L(f"empty_{cam_safe}.location = ({tx}, {ty}, {tz})")
        L(f"con.target = empty_{cam_safe}")
        L(f"con.track_axis = 'TRACK_NEGATIVE_Z'")
        L(f"con.up_axis = 'UP_Y'")
        if i == 0:
            L(f"bpy.context.scene.camera = cam_{cam_safe}   # default active camera")
        L("")

    # ── Render settings ───────────────────────────────────────────────────────
    L("# ── Render Settings ──────────────────────────────────────────────────────")
    L("scene = bpy.context.scene")
    L("scene.render.engine           = 'BLENDER_EEVEE'  # change to 'CYCLES' for path tracing")
    L("scene.render.resolution_x     = 1920")
    L("scene.render.resolution_y     = 1080")
    L("scene.render.film_transparent = False")
    L("scene.render.filepath         = '/tmp/scotch_render/'")
    L("scene.render.image_settings.file_format = 'PNG'")
    L("")
    L("# Cycles settings (uncomment to use Cycles instead of EEVEE)")
    L("# scene.render.engine = 'CYCLES'")
    L("# scene.cycles.samples = 256")
    L("# scene.cycles.use_denoising = True")
    L("")
    L("# World background (sky blue)")
    L("scene.world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')")
    L("scene.world.use_nodes = True")
    L("bg = scene.world.node_tree.nodes.get('Background')")
    L("if bg: bg.inputs['Color'].default_value    = (0.55, 0.65, 0.78, 1.0)")
    L("if bg: bg.inputs['Strength'].default_value = 0.6")
    L("")
    L("print('Scotch import complete. Object hierarchy:')")
    L("print('  Scotch_Site    → ground slab')")
    L("print('  Scotch_Walls   → room wall boxes (Scotch_Wall_<room>)')")
    L("print('  Scotch_Floors  → room interior volumes (for Boolean; hidden)')")
    L("print('  Scotch_Roof    → roof slab')")
    L("print('  Scotch_Glass   → door/window glass openings')")
    L("print('  Scotch_Lighting → Sun Key + Area Fill + Rim')")
    L(f"print('  Scotch_Cameras  → {len(cameras)} presets')")
    L("print()")
    L("print('Tip: Apply Boolean modifiers to hollow the rooms.')")
    L("print('     Select Scotch_Wall_<room> → Properties → Modifier → Apply.')")
    L("print()")
    L("print('Headless render example:')")
    L("print('  blender --background --python floor_plan_blender.py')")
    L("print('  Output: /tmp/scotch_render/0001.png')")
    L("")

    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content.encode("utf-8")
