"""Phase 11.2 / 15.1 — SketchUp Ruby script exporter (hardened).

Generates a runnable SketchUp Ruby (.rb) file from an ArchitectureProject.

Phase 15.1 improvements over Phase 11:
  - Model units set to feet via UnitsOptions.
  - Room groups named "Name [room_id]" so each group is uniquely identifiable.
  - S-LABELS tag + 3D text labels at room centroids.
  - Real door voids: vertical faces drawn on the inner wall surface + pushpull
    through wall thickness instead of floor-level plan markers.
  - Window voids: same approach but elevated between SILL_H and SILL_H+WIN_H.
  - Balanced Ruby `def`/`end` blocks (smoke-parseable).

Coordinate mapping:
  Plan x  → SketchUp X (right)
  Plan y  → SketchUp Y (forward in top view)
  Height  → SketchUp Z (up)
  Unit: feet converted to inches (×12) for SketchUp internal units.
"""

from datetime import datetime, timezone
from pathlib import Path

from app.core.models import ArchitectureProject, Room

WALL_T = 0.5   # ft — total wall thickness (0.25 ft per side)
SLAB_T = 0.5   # ft — floor / roof slab thickness
SILL_H = 2.5   # ft — window sill height
WIN_H  = 4.0   # ft — window opening height

# Room-type → (R,G,B) material colour
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


def _door_void_pts(room: Room, wall: str, off: float, wid: float,
                   z_bot: float, z_top: float) -> list[tuple[float, float, float]] | None:
    """Return 4 (x,y,z) points in feet for a vertical opening face on *wall*.

    The winding order is chosen so that pushpull(WALL_T*FT) goes toward the
    exterior (i.e. cuts through the wall). Returns None for unknown wall names.

    North wall: inner face at y=room.y, normal −Y → pushpull cuts northward.
    South wall: inner face at y=room.y+room.depth, normal +Y → cuts southward.
    East  wall: inner face at x=room.x+room.width,  normal +X → cuts eastward.
    West  wall: inner face at x=room.x,              normal −X → cuts westward.
    """
    rx, ry = room.x, room.y
    rw, rd = room.width, room.depth
    if wall == "north":
        x0, x1 = rx + off, rx + off + wid
        y = ry
        return [(x0, y, z_bot), (x1, y, z_bot), (x1, y, z_top), (x0, y, z_top)]
    if wall == "south":
        x0, x1 = rx + off, rx + off + wid
        y = ry + rd
        return [(x0, y, z_bot), (x0, y, z_top), (x1, y, z_top), (x1, y, z_bot)]
    if wall == "east":
        y0, y1 = ry + off, ry + off + wid
        x = rx + rw
        return [(x, y0, z_bot), (x, y1, z_bot), (x, y1, z_top), (x, y0, z_top)]
    if wall == "west":
        y0, y1 = ry + off, ry + off + wid
        x = rx
        return [(x, y0, z_bot), (x, y0, z_top), (x, y1, z_top), (x, y1, z_bot)]
    return None


def export_sketchup(project: ArchitectureProject, output_path: Path) -> bytes:
    """Generate a SketchUp Ruby (.rb) script for *project* and write to *output_path*."""
    lines: list[str] = []
    L = lines.append

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fh = project.building.floor_height if project.building else 10.0
    unit = "ft" if project.units == "feet" else "m"

    # ── Header ────────────────────────────────────────────────────────────────
    L("# " + "=" * 77)
    L("# Scotch — SketchUp Ruby Import Script  (Phase 15.1 hardened)")
    L(f"# Project : {project.name or 'Untitled'}")
    L(f"# Generated: {stamp}")
    L(f"# Units    : {unit}  (converted to SketchUp inches: × 12)")
    L(f"# Floors   : {project.building.floors if project.building else 1}")
    L(f"# Site     : {project.site.width}{unit} × {project.site.depth}{unit}")
    L("#")
    L("# How to run:")
    L("#   Extensions > Ruby Console > paste this script and press Enter.")
    L("#   — OR — File > Import > scotch_extension (Phase 15.2).")
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

    # ── Set model units to feet ───────────────────────────────────────────────
    L("# Set model units to feet")
    L("opts = model.options['UnitsOptions']")
    L("opts['LengthUnit'] = 1 if opts  # 1 = feet in SketchUp")
    L("")

    # ── Constants ─────────────────────────────────────────────────────────────
    L("# Project constants (all in SketchUp inches)")
    L("FT     = 12.0")
    L(f"WALL_H = {fh} * FT   # floor-to-ceiling height")
    L(f"WALL_T = {WALL_T} * FT   # wall half-thickness per side")
    L(f"SLAB_T = {SLAB_T} * FT   # floor slab thickness")
    L(f"SILL_H = {SILL_H} * FT   # window sill height")
    L(f"WIN_H  = {WIN_H} * FT    # window opening height")
    L("")

    # ── Helper: material ──────────────────────────────────────────────────────
    L("def scotch_mat(mats, name, r, g, b, alpha = 255)")
    L("  m = mats[name] || mats.add(name)")
    L("  m.color = Sketchup::Color.new(r, g, b, alpha)")
    L("  m")
    L("end")
    L("")

    # ── Helper: tag (layer) ───────────────────────────────────────────────────
    L("def scotch_tag(model, name)")
    L("  model.layers[name] || model.layers.add(name)")
    L("end")
    L("")

    # ── Tags ──────────────────────────────────────────────────────────────────
    L("# Tags")
    L("tag_site   = scotch_tag(model, 'S-SITE')")
    L("tag_rooms  = scotch_tag(model, 'S-ROOMS')")
    L("tag_roof   = scotch_tag(model, 'S-ROOF')")
    L("tag_open   = scotch_tag(model, 'S-OPENINGS')")
    L("tag_labels = scotch_tag(model, 'S-LABELS')")
    L("")

    # ── Materials ─────────────────────────────────────────────────────────────
    L("# Base materials")
    L("mat_ground = scotch_mat(mats, 'Scotch_Ground',  210, 210, 200)")
    L("mat_wall   = scotch_mat(mats, 'Scotch_Wall',    245, 242, 238)")
    L("mat_roof   = scotch_mat(mats, 'Scotch_Roof',    175, 168, 158)")
    L("mat_glass  = scotch_mat(mats, 'Scotch_Glass',   180, 215, 245, 160)")
    L("")
    L("ROOM_MAT = {}")
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
    L("# Washer technique: outer boundary face + inner room face at Z=0.")
    L("# SketchUp treats the gap as a washer; pushpull creates hollow walls.")
    L("# Door/window voids: vertical faces on inner wall surface + pushpull.")
    L("")

    half = WALL_T / 2

    for idx, room in enumerate(project.rooms):
        ox = room.x - half
        oy = room.y - half
        ow = room.width + WALL_T
        od = room.depth + WALL_T
        t = room.type.lower().replace(" ", "_")
        mat_key = f"ROOM_MAT['{t}'] || mat_wall"

        L(f"# --- {room.name} [{room.id}] ---")
        L(f"rg = entities.add_group")
        L(f"rg.layer = tag_rooms")
        L(f"rg.name  = {repr(f'{room.name} [{room.id}]')}")
        L(f"re = rg.entities")
        L("")

        # Outer wall boundary face
        L(f"# Outer wall boundary")
        L(f"re.add_face([")
        L(f"  Geom::Point3d.new({ox} * FT,         {oy} * FT,         0),")
        L(f"  Geom::Point3d.new({ox + ow} * FT,    {oy} * FT,         0),")
        L(f"  Geom::Point3d.new({ox + ow} * FT,    {oy + od} * FT,    0),")
        L(f"  Geom::Point3d.new({ox} * FT,         {oy + od} * FT,    0),")
        L(f"])")
        L("")

        # Inner room floor face (creates washer with outer face)
        L(f"# Inner room floor — washer gap → hollow walls when pushpull'd")
        L(f"inner_face = re.add_face([")
        L(f"  Geom::Point3d.new({room.x} * FT,              {room.y} * FT,              0),")
        L(f"  Geom::Point3d.new({room.x + room.width} * FT,  {room.y} * FT,              0),")
        L(f"  Geom::Point3d.new({room.x + room.width} * FT,  {room.y + room.depth} * FT, 0),")
        L(f"  Geom::Point3d.new({room.x} * FT,              {room.y + room.depth} * FT,  0),")
        L(f"])")
        L(f"inner_face.material = {mat_key} if inner_face")
        L("")

        # Pushpull washer to wall height
        L(f"washer = re.select {{ |e| e.is_a?(Sketchup::Face) && e.area > inner_face.area * 1.5 rescue false }}.first")
        L(f"washer.pushpull(WALL_H) if washer")
        L("")

        # Door voids — vertical faces on inner wall surface + pushpull through
        room_doors = [d for d in project.doors if d.room_id == room.id]
        if room_doors:
            L(f"# Door voids — vertical opening faces on wall inner surface")
            for di, door in enumerate(room_doors, start=1):
                pts = _door_void_pts(room, door.wall, door.offset, door.width, 0, fh)
                if pts is None:
                    continue
                var = f"door_{idx}_{di}"
                L(f"# Door {di}: wall={door.wall}, offset={door.offset}ft, width={door.width}ft")
                L(f"{var}_pts = [")
                for px, py, pz in pts:
                    L(f"  Geom::Point3d.new({px} * FT, {py} * FT, {pz} * FT),")
                L(f"]")
                L(f"{var} = re.add_face({var}_pts) rescue nil")
                L(f"{var}.pushpull(WALL_T) rescue nil  # cuts through wall toward exterior")
                L("")

        # Window voids — same approach but between SILL_H and SILL_H+WIN_H
        room_wins = [w for w in project.windows if w.room_id == room.id]
        if room_wins:
            L(f"# Window voids — vertical opening faces at sill height")
            for wi, win in enumerate(room_wins, start=1):
                pts = _door_void_pts(room, win.wall, win.offset, win.width, SILL_H, SILL_H + WIN_H)
                if pts is None:
                    continue
                var = f"win_{idx}_{wi}"
                L(f"# Window {wi}: wall={win.wall}, offset={win.offset}ft, width={win.width}ft")
                L(f"{var}_pts = [")
                for px, py, pz in pts:
                    L(f"  Geom::Point3d.new({px} * FT, {py} * FT, {pz} * FT),")
                L(f"]")
                L(f"{var} = re.add_face({var}_pts) rescue nil")
                L(f"{var}.pushpull(WALL_T) rescue nil")
                L(f"{var}.material = mat_glass rescue nil  # glass pane")
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

    # ── Room labels ───────────────────────────────────────────────────────────
    L("# ── Room Labels (S-LABELS tag) ───────────────────────────────────────────")
    L("lbl_grp       = entities.add_group")
    L("lbl_grp.layer = tag_labels")
    L("lbl_grp.name  = 'Room Labels'")
    L("le = lbl_grp.entities")
    for room in project.rooms:
        cx = room.x + room.width / 2
        cy = room.y + room.depth / 2
        area_str = f"{room.width * room.depth:.0f} ft²"
        label = f"{room.name}\\n{area_str}"
        L(f"le.add_text({repr(label)}, Geom::Point3d.new({cx} * FT, {cy} * FT, 0.1 * FT)) rescue nil")
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
      "Tips:\\n• Room groups are named <Room Name> [id] in the Outliner.\\n" +
      "• Toggle S-LABELS tag to show/hide room text labels.\\n" +
      "• Use Extensions > Scotch Importer for future imports (Phase 15.2).')")
    L("")

    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content.encode("utf-8")
