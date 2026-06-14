"""Stage 16.1 + 16.2 — Rhino Python script exporter.

Generates a runnable RhinoPython (.py) file from an ArchitectureProject.

Approach:
  - Uses rhinoscriptsyntax (RS) — Rhino 7+ IronPython 2.7 / CPython 3.
  - Layers per category: Scotch::Site / Walls / Doors / Windows / Labels / Roof
  - Rooms: hollow wall boxes (outer − inner via BooleanDifference), named.
  - Door/window openings: void boxes cut from hollow walls via BooleanDifference.
  - Room text dots on Scotch::Labels layer.
  - Massing (16.2): walls extruded to floor_height, roof slab at WALL_H + SLAB_T.
  - Unit auto-detection at script runtime (mm / m / ft).

Coordinate mapping:
  Plan (x, y) in feet → Rhino (X, Y) in document units
  Height (z)  in feet → Rhino Z in document units
  Conversion factor FT set at runtime by querying rs.UnitSystem().
"""

from datetime import datetime, timezone
from pathlib import Path

from app.core.models import ArchitectureProject

WALL_T = 0.5   # wall thickness, ft
SLAB_T = 0.5   # slab thickness, ft
SILL_H = 2.5   # window sill height, ft
WIN_H  = 4.0   # window opening height, ft


def export_rhino(project: ArchitectureProject, output_path: Path) -> bytes:
    """Generate a RhinoPython (.py) script for *project* and write to *output_path*."""
    lines: list[str] = []
    L = lines.append

    stamp  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fh_ft  = project.building.floor_height if project.building else 10.0
    sw_ft  = project.site.width
    sd_ft  = project.site.depth
    n_rooms = len(project.rooms)

    # ── Header ────────────────────────────────────────────────────────────────
    L('"""')
    L("Scotch — Rhino Python Import Script")
    L(f"Project  : {project.name or 'Untitled'}")
    L(f"Generated: {stamp}")
    L("Rhino    : 7+ (RhinoPython / IronPython 2.7 or CPython 3)")
    L("Units    : Scotch values are in feet; script auto-detects Rhino document units.")
    L("")
    L("How to run:")
    L("  Option A: Tools menu → PythonScript → Edit → Open this file → Run Script.")
    L("  Option B: Type _RunPythonScript in the Rhino command line, select this file.")
    L("  Option C: Drag and drop this file onto the Rhino viewport.")
    L('"""')
    L("")
    L("import rhinoscriptsyntax as rs")
    L("")

    # ── Constants ────────────────────────────────────────────────────────────
    L("# Project constants (values in feet; converted to document units via FT)")
    L(f"WALL_H = {fh_ft}   # floor-to-ceiling height, ft")
    L(f"WALL_T = {WALL_T}   # wall thickness, ft")
    L(f"SLAB_T = {SLAB_T}   # slab/roof thickness, ft")
    L(f"SILL_H = {SILL_H}   # window sill height above floor, ft")
    L(f"WIN_H  = {WIN_H}    # window opening height, ft")
    L(f"SITE_W = {sw_ft}   # site width, ft")
    L(f"SITE_D = {sd_ft}   # site depth, ft")
    L("")

    # ── Unit auto-detection ──────────────────────────────────────────────────
    L("# Unit auto-detection: Rhino UnitSystem() → feet conversion factor")
    L("_unit = rs.UnitSystem()")
    L("if _unit == 2:       # metres")
    L("    FT = 0.3048")
    L("elif _unit == 8:     # feet (native — no conversion)")
    L("    FT = 1.0")
    L("else:                # millimetres (Rhino default template)")
    L("    FT = 304.8")
    L("")

    # ── Layer setup ───────────────────────────────────────────────────────────
    L("# Layers — create if they do not exist")
    L("_LAYERS = [")
    L('    "Scotch::Site",')
    L('    "Scotch::Walls",')
    L('    "Scotch::Doors",')
    L('    "Scotch::Windows",')
    L('    "Scotch::Labels",')
    L('    "Scotch::Roof",')
    L("]")
    L("for _lname in _LAYERS:")
    L("    if not rs.IsLayer(_lname):")
    L("        rs.AddLayer(_lname)")
    L("")

    # ── Helper: box primitive ─────────────────────────────────────────────────
    L("# _box: create a solid box from origin + dimensions (all in feet, converted at runtime)")
    L("def _box(x_ft, y_ft, z_ft, w_ft, d_ft, h_ft, layer):")
    L("    x, y, z = x_ft * FT, y_ft * FT, z_ft * FT")
    L("    w, d, h = w_ft * FT, d_ft * FT, h_ft * FT")
    L("    corners = [")
    L("        [x, y, z],         [x + w, y, z],         [x + w, y + d, z],         [x, y + d, z],")
    L("        [x, y, z + h],     [x + w, y, z + h],     [x + w, y + d, z + h],     [x, y + d, z + h],")
    L("    ]")
    L("    obj = rs.AddBox(corners)")
    L("    if obj:")
    L("        rs.ObjectLayer(obj, layer)")
    L("    return obj")
    L("")

    # ── Site boundary ─────────────────────────────────────────────────────────
    L("# Site boundary polyline")
    L("_site_pts = [")
    L("    [0, 0, 0], [SITE_W * FT, 0, 0],")
    L("    [SITE_W * FT, SITE_D * FT, 0], [0, SITE_D * FT, 0],")
    L("    [0, 0, 0],")
    L("]")
    L("_site_crv = rs.AddPolyline(_site_pts)")
    L("if _site_crv:")
    L('    rs.ObjectLayer(_site_crv, "Scotch::Site")')
    L('    rs.ObjectName(_site_crv, "Site Boundary")')
    L("")

    # ── Rooms ─────────────────────────────────────────────────────────────────
    L("# Rooms — hollow walls via BooleanDifference(outer_box, inner_void)")
    L("# Door/window openings also cut via BooleanDifference.")
    for i, room in enumerate(project.rooms):
        # Outer box (wall shell)
        ox = round(room.x - WALL_T / 2, 4)
        oy = round(room.y - WALL_T / 2, 4)
        ow = round(room.width  + WALL_T, 4)
        od = round(room.depth  + WALL_T, 4)
        # Inner void (interior cavity)
        rx = round(room.x + WALL_T / 2, 4)
        ry = round(room.y + WALL_T / 2, 4)
        rw = round(max(room.width  - WALL_T, 0.1), 4)
        rd = round(max(room.depth  - WALL_T, 0.1), 4)
        # Label centroid
        cx = round(room.x + room.width  / 2, 4)
        cy = round(room.y + room.depth  / 2, 4)
        area = round(room.width * room.depth, 1)
        s = f"r{i}"

        L(f"# --- {room.name} ---")
        L(f"_wall_{s} = _box({ox}, {oy}, 0.0, {ow}, {od}, WALL_H, 'Scotch::Walls')")
        L(f"_void_{s} = _box({rx}, {ry}, 0.0, {rw}, {rd}, WALL_H, 'Scotch::Walls')")
        L(f"_res = rs.BooleanDifference([_wall_{s}], [_void_{s}], delete_input=True)")
        L(f"_hollow_{s} = _res[0] if _res else _wall_{s}")
        L(f"if _hollow_{s}:")
        L(f"    rs.ObjectName(_hollow_{s}, {room.name!r})")
        L(f"    rs.ObjectLayer(_hollow_{s}, 'Scotch::Walls')")
        # Text dot label
        L(f"_dot_{s} = rs.AddTextDot({room.name!r} + ' ({area} sf)', [{cx} * FT, {cy} * FT, 0.5 * FT])")
        L(f"if _dot_{s}:")
        L(f"    rs.ObjectLayer(_dot_{s}, 'Scotch::Labels')")

        # Door openings
        room_doors = [d for d in project.doors if d.room_id == room.id]
        for j, door in enumerate(room_doors):
            wall = door.wall
            off  = door.offset
            wid  = door.width
            if wall == "north":
                dx0, dy0 = round(room.x + off, 4), round(room.y - WALL_T, 4)
                dw, dd   = round(wid, 4), round(WALL_T * 2, 4)
            elif wall == "south":
                dx0, dy0 = round(room.x + off, 4), round(room.y + room.depth - WALL_T, 4)
                dw, dd   = round(wid, 4), round(WALL_T * 2, 4)
            elif wall == "west":
                dx0, dy0 = round(room.x - WALL_T, 4), round(room.y + off, 4)
                dw, dd   = round(WALL_T * 2, 4), round(wid, 4)
            else:  # east
                dx0, dy0 = round(room.x + room.width - WALL_T, 4), round(room.y + off, 4)
                dw, dd   = round(WALL_T * 2, 4), round(wid, 4)
            L(f"# Door opening: wall={wall}, offset={off} ft, width={wid} ft")
            L(f"_dvoid_{s}_d{j} = _box({dx0}, {dy0}, 0.0, {dw}, {dd}, WALL_H, 'Scotch::Doors')")
            L(f"if _hollow_{s} and _dvoid_{s}_d{j}:")
            L(f"    _dres = rs.BooleanDifference([_hollow_{s}], [_dvoid_{s}_d{j}], delete_input=True)")
            L(f"    if _dres:")
            L(f"        _hollow_{s} = _dres[0]")
            L(f"        rs.ObjectLayer(_hollow_{s}, 'Scotch::Walls')")

        # Window openings
        room_wins = [w for w in project.windows if w.room_id == room.id]
        for k, win in enumerate(room_wins):
            wall = win.wall
            off  = win.offset
            wid  = win.width
            if wall == "north":
                wx0, wy0 = round(room.x + off, 4), round(room.y - WALL_T, 4)
                ww, wd   = round(wid, 4), round(WALL_T * 2, 4)
            elif wall == "south":
                wx0, wy0 = round(room.x + off, 4), round(room.y + room.depth - WALL_T, 4)
                ww, wd   = round(wid, 4), round(WALL_T * 2, 4)
            elif wall == "west":
                wx0, wy0 = round(room.x - WALL_T, 4), round(room.y + off, 4)
                ww, wd   = round(WALL_T * 2, 4), round(wid, 4)
            else:  # east
                wx0, wy0 = round(room.x + room.width - WALL_T, 4), round(room.y + off, 4)
                ww, wd   = round(WALL_T * 2, 4), round(wid, 4)
            L(f"# Window opening: wall={wall}, offset={off} ft, width={wid} ft (sill {SILL_H} ft)")
            L(f"_wvoid_{s}_w{k} = _box({wx0}, {wy0}, SILL_H, {ww}, {wd}, WIN_H, 'Scotch::Windows')")
            L(f"if _hollow_{s} and _wvoid_{s}_w{k}:")
            L(f"    _wres = rs.BooleanDifference([_hollow_{s}], [_wvoid_{s}_w{k}], delete_input=True)")
            L(f"    if _wres:")
            L(f"        _hollow_{s} = _wres[0]")
            L(f"        rs.ObjectLayer(_hollow_{s}, 'Scotch::Walls')")
        L("")

    # ── Roof slab (massing — 16.2) ────────────────────────────────────────────
    L("# Roof slab — massing cap at WALL_H (matches Scotch 3D viewer)")
    L(f"_roof = _box(0.0, 0.0, WALL_H, SITE_W, SITE_D, SLAB_T, 'Scotch::Roof')")
    L("if _roof:")
    L('    rs.ObjectName(_roof, "Roof Slab")')
    L("")

    # ── Footer ────────────────────────────────────────────────────────────────
    L("# Import summary")
    L(f"print('Scotch Rhino import complete.')")
    L(f"print('  Rooms   : {n_rooms}')")
    L(f"print('  Site    : {sw_ft} x {sd_ft} ft')")
    L(f"print('  Height  : ' + str(WALL_H) + ' ft')")
    L("print('Tip: if BooleanDifference failed on any room, select the affected')")
    L("print('     wall solid + void object and run BooleanDifference manually.')")

    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content.encode("utf-8")
