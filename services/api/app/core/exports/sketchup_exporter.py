"""Stage 11.2 — SketchUp Ruby script exporter.

Generates a runnable SketchUp Ruby (.rb) file from an ArchitectureProject.

Approach:
  - Each room → a SketchUp group containing two faces at Z=0 (outer wall
    boundary + inner room boundary). SketchUp treats the gap as a "washer"
    face which, when pushpull'd to wall height, creates hollow walls.
  - Floor slab: outer wall boundary face at Z=−SLAB_T pushed to +SLAB_T.
  - Materials keyed by room type.
  - Tags (layers): S-SITE, S-ROOMS, S-ROOF.
  - Doors/windows: floor-level swing/sill markers + comment dimensions.

Coordinate mapping:
  Plan x  → SketchUp X (right)
  Plan y  → SketchUp Y (Y in SketchUp is the "forward" axis from top view)
  Height  → SketchUp Z (up)
  Unit: feet converted to inches (×12) for SketchUp internal units.
"""

from datetime import datetime, timezone
from pathlib import Path

from app.core.models import ArchitectureProject, Room

WALL_T = 0.5   # ft — wall half-thickness on each side
SLAB_T = 0.5   # ft — floor slab thickness (below z=0)
SILL_H = 2.5   # ft — window sill height
WIN_H  = 4.0   # ft — window opening height

# Room-type to (R,G,B) material colour
_ROOM_COLOURS: dict[str, tuple[int, int, int]] = {
    "living":         (235, 225, 205),
    "dining":         (235, 228, 210),
    "kitchen":        (235, 230, 215),
    "master_bedroom": (220, 205, 200),
    "bedroom":        (230, 215, 210),
    "bathroom":       (215, 230, 235),
    "balcony":        (220, 225, 215),
    "parking":        (200, 200, 200),
    "storage":        (215, 215, 210),
    "study":          (230, 225, 215),
    "foyer":          (225, 220, 210),
    "corridor":       (230, 228, 220),
    "seating":        (235, 225, 205),
    "service":        (215, 215, 215),
}
_DEFAULT_COLOUR = (240, 238, 235)


def _mat_name(room_type: str) -> str:
    return f"Scotch_{room_type.replace(' ', '_').title()}"


def _room_colour(room: Room) -> tuple[int, int, int]:
    t = room.type.lower().replace(" ", "_")
    return _ROOM_COLOURS.get(t, _DEFAULT_COLOUR)


def export_sketchup(project: ArchitectureProject, output_path: Path) -> bytes:
    """Generate a SketchUp Ruby (.rb) script for *project* and write to *output_path*."""
    lines: list[str] = []
    L = lines.append

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fh = project.building.floor_height if project.building else 10.0
    unit = "ft" if project.units == "feet" else "m"

    # ── Header ────────────────────────────────────────────────────────────────
    L("# " + "=" * 77)
    L(f"# Scotch — SketchUp Ruby Import Script")
    L(f"# Project : {project.name or 'Untitled'}")
    L(f"# Generated: {stamp}")
    L(f"# Units    : {unit}  (converted to SketchUp inches: × 12)")
    L(f"# Floors   : {project.building.floors if project.building else 1}")
    L(f"# Site     : {project.site.width}{unit} × {project.site.depth}{unit}")
    L("#")
    L("# How to run:")
    L("#   Extensions > Ruby Console > paste this script and press Enter.")
    L("#   — OR — save as a .rb file and run: Extensions > Script Editor > Open.")
    L("# " + "=" * 77)
    L("")
    L("require 'sketchup'")
    L("require 'extensions'")
    L("")
    L("model    = Sketchup.active_model")
    L("entities = model.entities")
    L("mats     = model.materials")
    L("layers   = model.layers")
    L("")
    L("model.start_operation('Scotch Import', true)")
    L("")

    # ── Constants ────────────────────────────────────────────────────────────
    L("# Project constants (all in SketchUp inches)")
    L(f"FT     = 12.0")
    L(f"WALL_H = {fh} * FT   # floor-to-ceiling height")
    L(f"WALL_T = {WALL_T} * FT   # wall half-thickness per side")
    L(f"SLAB_T = {SLAB_T} * FT   # floor slab thickness")
    L(f"SILL_H = {SILL_H} * FT   # window sill height")
    L(f"WIN_H  = {WIN_H} * FT    # window opening height")
    L("")

    # ── Helper: material ────────────────────────────────────────────────────
    L("# Helper: ensure a material exists with given RGB")
    L("def scotch_mat(mats, name, r, g, b, alpha = 255)")
    L("  m = mats[name] || mats.add(name)")
    L("  m.color = Sketchup::Color.new(r, g, b, alpha)")
    L("  m")
    L("end")
    L("")

    # ── Helper: tag (layer) ──────────────────────────────────────────────────
    L("# Helper: ensure a tag (layer) exists")
    L("def scotch_tag(model, name)")
    L("  model.layers[name] || model.layers.add(name)")
    L("end")
    L("")

    # ── Tags ─────────────────────────────────────────────────────────────────
    L("# Tags")
    L("tag_site  = scotch_tag(model, 'S-SITE')")
    L("tag_rooms = scotch_tag(model, 'S-ROOMS')")
    L("tag_roof  = scotch_tag(model, 'S-ROOF')")
    L("tag_open  = scotch_tag(model, 'S-OPENINGS')")
    L("")

    # ── Materials ─────────────────────────────────────────────────────────────
    L("# Materials")
    L("mat_ground = scotch_mat(mats, 'Scotch_Ground',  210, 210, 200)")
    L("mat_wall   = scotch_mat(mats, 'Scotch_Wall',    245, 242, 238)")
    L("mat_roof   = scotch_mat(mats, 'Scotch_Roof',    175, 168, 158)")
    L("mat_glass  = scotch_mat(mats, 'Scotch_Glass',   180, 215, 245, 160)")
    L("")
    L("ROOM_MAT = {}")

    # Collect unique room types
    seen: set[str] = set()
    for room in project.rooms:
        t = room.type.lower().replace(" ", "_")
        if t in seen:
            continue
        seen.add(t)
        r, g, b = _room_colour(room)
        name = _mat_name(t)
        L(f"ROOM_MAT['{t}'] = scotch_mat(mats, '{name}', {r}, {g}, {b})")
    L("")

    # ── Ground slab ───────────────────────────────────────────────────────────
    sw = project.site.width
    sd = project.site.depth
    L("# ── Ground Slab ──────────────────────────────────────────────────────────")
    L("site_grp       = entities.add_group")
    L("site_grp.layer = tag_site")
    L("site_grp.name  = 'Ground Slab'")
    L("sg = site_grp.entities")
    L("slab_pts = [")
    L(f"  Geom::Point3d.new(0,          0,          -SLAB_T),")
    L(f"  Geom::Point3d.new({sw} * FT,  0,          -SLAB_T),")
    L(f"  Geom::Point3d.new({sw} * FT,  {sd} * FT,  -SLAB_T),")
    L(f"  Geom::Point3d.new(0,          {sd} * FT,  -SLAB_T),")
    L("]")
    L("slab_face = sg.add_face(slab_pts)")
    L("slab_face.material = mat_ground")
    L("slab_face.pushpull(SLAB_T)")
    L("")

    # ── Rooms ─────────────────────────────────────────────────────────────────
    L("# ── Rooms ────────────────────────────────────────────────────────────────")
    L("# Each room group contains an outer wall-boundary face and an inner")
    L("# room-interior face at Z=0. SketchUp turns the gap into a 'washer'")
    L("# (face with hole). Pushpulling the washer creates hollow walls.")
    L("# The floor face (inner boundary) receives the room material.")
    L("")

    rooms_by_id = {r.id: r for r in project.rooms}

    for idx, room in enumerate(project.rooms):
        half = WALL_T / 2
        ox = room.x - half
        oy = room.y - half
        ow = room.width + WALL_T
        od = room.depth + WALL_T
        t = room.type.lower().replace(" ", "_")
        mat_key = f"ROOM_MAT['{t}'] || mat_wall"

        L(f"# --- {room.name} ---")
        L(f"rg = entities.add_group")
        L(f"rg.layer = tag_rooms")
        L(f"rg.name  = {repr(room.name)}")
        L(f"re = rg.entities")
        L("")
        # Outer face (wall boundary)
        L(f"# Outer wall boundary (includes {WALL_T}ft wall thickness each side)")
        L(f"re.add_face([")
        L(f"  Geom::Point3d.new({ox} * FT,  {oy} * FT,  0),")
        L(f"  Geom::Point3d.new({ox + ow} * FT,  {oy} * FT,  0),")
        L(f"  Geom::Point3d.new({ox + ow} * FT,  {oy + od} * FT,  0),")
        L(f"  Geom::Point3d.new({ox} * FT,        {oy + od} * FT,  0),")
        L(f"])")
        L("")
        # Inner face (room interior — creates washer with outer face)
        L(f"# Inner room interior (adds hole in outer face → washer shape)")
        L(f"inner_face = re.add_face([")
        L(f"  Geom::Point3d.new({room.x} * FT,              {room.y} * FT,              0),")
        L(f"  Geom::Point3d.new({room.x + room.width} * FT,  {room.y} * FT,              0),")
        L(f"  Geom::Point3d.new({room.x + room.width} * FT,  {room.y + room.depth} * FT,  0),")
        L(f"  Geom::Point3d.new({room.x} * FT,              {room.y + room.depth} * FT,  0),")
        L(f"])")
        L(f"inner_face.material = {mat_key}  # room-type colour")
        L("")
        L(f"# Find the washer face (the larger face containing the hole) and extrude")
        L(f"washer = re.select {{ |e| e.is_a?(Sketchup::Face) && e.area > inner_face.area * 1.5 rescue false }}.first")
        L(f"washer.pushpull(WALL_H) if washer")
        L("")

        # Door opening markers
        room_doors = [d for d in project.doors if d.room_id == room.id]
        room_wins  = [w for w in project.windows if w.room_id == room.id]

        if room_doors:
            L(f"  # Door openings — draw floor markers and pushpull to cut walls manually")
            for di, door in enumerate(room_doors, start=1):
                wall = door.wall
                off  = door.offset
                wid  = door.width
                # Compute door face corners in plan space → SketchUp (flat at Z=0)
                if wall == "north":
                    x0, y0 = room.x + off, room.y - half
                    x1, y1 = room.x + off + wid, room.y + half
                elif wall == "south":
                    x0, y0 = room.x + off, room.y + room.depth - half
                    x1, y1 = room.x + off + wid, room.y + room.depth + half
                elif wall == "west":
                    x0, y0 = room.x - half, room.y + off
                    x1, y1 = room.x + half, room.y + off + wid
                else:  # east
                    x0, y0 = room.x + room.width - half, room.y + off
                    x1, y1 = room.x + room.width + half, room.y + off + wid

                L(f"  # Door {di}: wall={wall}, offset={off}ft, width={wid}ft")
                L(f"  # Pushpull this face through the wall to cut a full-height opening:")
                L(f"  door_pts_{idx}_{di} = [")
                L(f"    Geom::Point3d.new({x0} * FT, {y0} * FT, 0),")
                L(f"    Geom::Point3d.new({x1} * FT, {y0} * FT, 0),")
                L(f"    Geom::Point3d.new({x1} * FT, {y1} * FT, 0),")
                L(f"    Geom::Point3d.new({x0} * FT, {y1} * FT, 0),")
                L(f"  ]")
                L(f"  door_face_{idx}_{di} = re.add_face(door_pts_{idx}_{di}) rescue nil")
                L(f"  door_face_{idx}_{di}.material = mat_glass if door_face_{idx}_{di}")
                L("")

        if room_wins:
            L(f"  # Window openings (sill {SILL_H}ft, height {WIN_H}ft)")
            for wi, win in enumerate(room_wins, start=1):
                L(f"  # Window {wi}: wall={win.wall}, offset={win.offset}ft, width={win.width}ft")
            L("")

    # ── Roof slab ─────────────────────────────────────────────────────────────
    L("# ── Roof Slab ────────────────────────────────────────────────────────────")
    L("roof_grp       = entities.add_group")
    L("roof_grp.layer = tag_roof")
    L("roof_grp.name  = 'Roof Slab'")
    L("rg_ents = roof_grp.entities")
    L("roof_pts = [")
    L(f"  Geom::Point3d.new(0,          0,          WALL_H),")
    L(f"  Geom::Point3d.new({sw} * FT,  0,          WALL_H),")
    L(f"  Geom::Point3d.new({sw} * FT,  {sd} * FT,  WALL_H),")
    L(f"  Geom::Point3d.new(0,          {sd} * FT,  WALL_H),")
    L("]")
    L("roof_face = rg_ents.add_face(roof_pts)")
    L("roof_face.material = mat_roof")
    L("roof_face.pushpull(SLAB_T)")
    L("")

    # ── Finish ────────────────────────────────────────────────────────────────
    L("model.commit_operation")
    L("")
    L("# Set camera to isometric view")
    L("camera = model.active_view.camera")
    L("camera.set(")
    L(f"  Geom::Point3d.new({sw * 0.5} * FT, {-sd * 0.8} * FT, {fh * 1.8} * FT),")
    L(f"  Geom::Point3d.new({sw * 0.5} * FT, {sd * 0.5} * FT, 0),")
    L("  Geom::Vector3d.new(0, 0, 1)")
    L(")")
    L("model.active_view.zoom_extents")
    L("")
    L("UI.messagebox('Scotch floor plan imported successfully!\\n\\n" +
      "Tips:\\n• Use the Paint Bucket tool to adjust room materials.\\n" +
      "• Cut door openings: draw a rectangle on the wall face and pushpull through.\\n" +
      "• Run Extensions > Solid Inspector to fix any geometry issues.')")
    L("")

    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content.encode("utf-8")
