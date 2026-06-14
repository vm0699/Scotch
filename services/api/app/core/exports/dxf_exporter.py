"""Stage 11.1 — DXF export (deepened) using ezdxf.

Layers:
    A-SITE      site boundary LWPOLYLINE
    A-WALL      room outer-wall LWPOLYLINE (poché boundary)
    A-HATCH     wall area ANSI31 hatching (poché fill)
    A-DOOR      door leaf LINE + swing ARC
    A-WINDOW    window triple-LINE symbol
    A-ROOM-TEXT room MTEXT (name + size)
    A-DIMS      site + room DIMLINEAR entities
    A-ANNO      door/window call-out tags
    A-TITLE     title block

Coordinate system:
    Plan space: x right, y down (y=0 = entrance edge).
    DXF WCS:    x right, y UP (standard CAD).
    Transform:  dxf_y = site_depth - plan_y.
"""

import math
from datetime import datetime, timezone
from pathlib import Path

import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment

from app.core.models import ArchitectureProject, Door, Room, Window

WALL_T = 0.5  # ft

LAYERS = [
    ("A-SITE",      3,  0.18),
    ("A-WALL",      7,  0.35),
    ("A-HATCH",     8,  0.18),
    ("A-DOOR",      1,  0.18),
    ("A-WINDOW",    4,  0.18),
    ("A-ROOM-TEXT", 7,  0.18),
    ("A-DIMS",      8,  0.18),
    ("A-ANNO",      6,  0.13),
    ("A-TITLE",     7,  0.25),
]

DIM_TEXT_H = 1.2   # dimension text height (ft)
ANNO_TEXT_H = 1.0  # annotation text height (ft)
TITLE_TEXT_H = 1.8
SUBTITLE_TEXT_H = 1.2
DIM_GAP = 2.5      # ft between room edge and room dimension line


# ── Coordinate helpers ────────────────────────────────────────────────────────

def _fy(plan_y: float, depth: float) -> float:
    return depth - plan_y


def _wall_frame_dxf(room: Room, wall: str, depth: float):
    if wall == "north":
        sx, sy, ax, ay, nx, ny = room.x, room.y, 1, 0, 0, 1
    elif wall == "south":
        sx, sy, ax, ay, nx, ny = room.x, room.y + room.depth, 1, 0, 0, -1
    elif wall == "west":
        sx, sy, ax, ay, nx, ny = room.x, room.y, 0, 1, 1, 0
    else:
        sx, sy, ax, ay, nx, ny = room.x + room.width, room.y, 0, 1, -1, 0
    return sx, _fy(sy, depth), ax, -ay, nx, -ny


# ── Entity builders ───────────────────────────────────────────────────────────

def _add_door(msp, door: Door, room: Room, depth: float) -> None:
    sx, sy, ax, ay, nx, ny = _wall_frame_dxf(room, door.wall, depth)
    w = door.width
    hx = sx + ax * door.offset
    hy = sy + ay * door.offset
    jx = hx + ax * w
    jy = hy + ay * w
    lx = hx + nx * w
    ly = hy + ny * w

    msp.add_line((hx, hy), (lx, ly), dxfattribs={"layer": "A-DOOR"})

    a_leaf = math.degrees(math.atan2(ly - hy, lx - hx)) % 360
    a_jamb = math.degrees(math.atan2(jy - hy, jx - hx)) % 360
    diff = (a_jamb - a_leaf) % 360
    if diff > 180:
        a_leaf, a_jamb = a_jamb, a_leaf

    msp.add_arc(
        center=(hx, hy),
        radius=w,
        start_angle=a_leaf,
        end_angle=a_jamb,
        dxfattribs={"layer": "A-DOOR"},
    )


def _add_window(msp, win: Window, room: Room, depth: float) -> None:
    sx, sy, ax, ay, nx, ny = _wall_frame_dxf(room, win.wall, depth)
    x0 = sx + ax * win.offset
    y0 = sy + ay * win.offset
    x1 = x0 + ax * win.width
    y1 = y0 + ay * win.width
    half = WALL_T / 2
    for d in (-half, 0, half):
        msp.add_line(
            (x0 + nx * d, y0 + ny * d),
            (x1 + nx * d, y1 + ny * d),
            dxfattribs={"layer": "A-WINDOW"},
        )


def _add_room_wall(msp, room: Room, depth: float) -> None:
    half = WALL_T / 2
    lx = room.x - half
    ly = _fy(room.y - half, depth)
    rx = room.x + room.width + half
    ry = _fy(room.y + room.depth + half, depth)
    pts = [(lx, ry), (rx, ry), (rx, ly), (lx, ly)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-WALL"})


def _add_room_hatch(msp, room: Room, depth: float) -> None:
    """ANSI31 hatch for the wall-thickness zone (poché fill)."""
    half = WALL_T / 2
    # Outer corners (DXF y-up)
    olx = room.x - half
    ory = _fy(room.y - half, depth)      # top in DXF = smaller plan y
    orx = room.x + room.width + half
    oly = _fy(room.y + room.depth + half, depth)  # bottom in DXF
    # Inner corners (room interior)
    ilx = room.x
    iry = _fy(room.y, depth)
    irx = room.x + room.width
    ily = _fy(room.y + room.depth, depth)

    hatch = msp.add_hatch(color=8, dxfattribs={"layer": "A-HATCH"})
    hatch.set_pattern_fill("ANSI31", scale=0.08)

    # Outer boundary CCW (external)
    outer = [(olx, oly), (orx, oly), (orx, ory), (olx, ory)]
    hatch.paths.add_polyline_path(outer, is_closed=True, flags=1)  # 1=EXTERNAL

    # Inner boundary CW (hole)
    inner = [(ilx, iry), (irx, iry), (irx, ily), (ilx, ily)]
    hatch.paths.add_polyline_path(inner, is_closed=True, flags=0)  # 0=hole


def _add_room_text(msp, room: Room, depth: float, unit: str) -> None:
    cx = room.x + room.width / 2
    cy = _fy(room.y + room.depth / 2, depth)
    area = round(room.width * room.depth)
    content = f"{room.name}\\P{room.width}' × {room.depth}'"
    if area >= 60:
        content += f"\\P{area} {unit}²"
    msp.add_mtext(
        content,
        dxfattribs={
            "layer": "A-ROOM-TEXT",
            "insert": (cx, cy),
            "char_height": 1.5,
            "attachment_point": 5,
        },
    )


def _add_room_dims(msp, room: Room, depth: float) -> None:
    """DIMLINEAR entities for room width and depth."""
    top_y = _fy(room.y, depth)
    bot_y = _fy(room.y + room.depth, depth)
    lx = room.x
    rx = room.x + room.width

    # Width dimension — above the room (higher DXF y)
    base_y_w = top_y + DIM_GAP
    try:
        dim_w = msp.add_linear_dim(
            base=(lx + room.width / 2, base_y_w),
            p1=(lx, top_y),
            p2=(rx, top_y),
            angle=0,
            dxfattribs={"layer": "A-DIMS"},
        )
        dim_w.set_text(f"{room.width}'")
        dim_w.render()
    except Exception:
        pass  # ezdxf version variance

    # Depth dimension — left of the room (lower DXF x)
    base_x_d = lx - DIM_GAP
    try:
        dim_d = msp.add_linear_dim(
            base=(base_x_d, bot_y + room.depth / 2),
            p1=(lx, top_y),
            p2=(lx, bot_y),
            angle=90,
            dxfattribs={"layer": "A-DIMS"},
        )
        dim_d.set_text(f"{room.depth}'")
        dim_d.render()
    except Exception:
        pass


def _add_opening_tags(msp, doors, windows, rooms_by_id, depth: float) -> None:
    """Small call-out tags: D1, D2 … for doors; W1, W2 … for windows."""
    for i, door in enumerate(doors, start=1):
        room = rooms_by_id.get(door.room_id)
        if not room:
            continue
        sx, sy, ax, ay, nx, ny = _wall_frame_dxf(room, door.wall, depth)
        cx = sx + ax * (door.offset + door.width / 2) + nx * (WALL_T * 0.5)
        cy = sy + ay * (door.offset + door.width / 2) + ny * (WALL_T * 0.5)
        msp.add_text(
            f"D{i}",
            dxfattribs={
                "layer": "A-ANNO",
                "insert": (cx, cy),
                "height": ANNO_TEXT_H,
                "halign": 4,
            },
        )
    for i, win in enumerate(windows, start=1):
        room = rooms_by_id.get(win.room_id)
        if not room:
            continue
        sx, sy, ax, ay, nx, ny = _wall_frame_dxf(room, win.wall, depth)
        cx = sx + ax * (win.offset + win.width / 2) + nx * (WALL_T * 0.5)
        cy = sy + ay * (win.offset + win.width / 2) + ny * (WALL_T * 0.5)
        msp.add_text(
            f"W{i}",
            dxfattribs={
                "layer": "A-ANNO",
                "insert": (cx, cy),
                "height": ANNO_TEXT_H,
                "halign": 4,
            },
        )


def _add_north_arrow(msp, site_width: float, site_depth: float) -> None:
    """Simple north arrow — top-right of site."""
    cx = site_width + 4.5
    cy = site_depth + 4.5
    r = 1.5
    # Circle
    msp.add_circle((cx, cy), r, dxfattribs={"layer": "A-ANNO"})
    # Shaft (south → north = ↑ in DXF)
    msp.add_line((cx, cy - r * 0.9), (cx, cy + r * 0.9), dxfattribs={"layer": "A-ANNO"})
    # Arrow head (filled triangle approximation — two lines)
    hw = r * 0.3
    msp.add_line((cx, cy + r * 0.9), (cx - hw, cy + r * 0.3), dxfattribs={"layer": "A-ANNO"})
    msp.add_line((cx, cy + r * 0.9), (cx + hw, cy + r * 0.3), dxfattribs={"layer": "A-ANNO"})
    # "N" text
    msp.add_text(
        "N",
        dxfattribs={
            "layer": "A-ANNO",
            "insert": (cx, cy + r + 0.6),
            "height": 1.4,
            "halign": 4,
        },
    )


def _add_title_block(
    msp,
    project: ArchitectureProject,
    site_width: float,
    site_depth: float,
) -> None:
    """Minimal title block at top-right, outside the site boundary."""
    tx = site_width + 1
    ty = site_depth  # top of site
    bw, bh = 22, 14  # block width / height in ft

    # Outer border
    pts = [(tx, ty - bh), (tx + bw, ty - bh), (tx + bw, ty), (tx, ty)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-TITLE"})
    # Divider lines
    msp.add_line((tx, ty - 4), (tx + bw, ty - 4), dxfattribs={"layer": "A-TITLE"})
    msp.add_line((tx, ty - 8), (tx + bw, ty - 8), dxfattribs={"layer": "A-TITLE"})

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    unit_label = "ft" if project.units == "feet" else "m"

    rows = [
        (TITLE_TEXT_H, project.name or "Untitled"),
        (SUBTITLE_TEXT_H, f"Floor Plan · {project.site.width}{unit_label} × {project.site.depth}{unit_label}"),
        (SUBTITLE_TEXT_H, f"Scotch · {stamp}"),
        (SUBTITLE_TEXT_H, f"Scale: NTS  |  Units: {project.units.capitalize()}"),
    ]
    y_pos = ty - 1.5
    for h, text in rows:
        msp.add_text(
            text,
            dxfattribs={
                "layer": "A-TITLE",
                "insert": (tx + 1, y_pos),
                "height": h,
            },
        )
        y_pos -= (h + 1.5)


def _add_site_dims(msp, site_width: float, depth: float) -> None:
    """Site-level dimension lines (plain lines + text, always available)."""
    dim_offset = 3
    y_dim = -dim_offset
    msp.add_line((0, y_dim), (site_width, y_dim), dxfattribs={"layer": "A-DIMS"})
    msp.add_line((0, y_dim - 0.5), (0, y_dim + 0.5), dxfattribs={"layer": "A-DIMS"})
    msp.add_line((site_width, y_dim - 0.5), (site_width, y_dim + 0.5), dxfattribs={"layer": "A-DIMS"})
    msp.add_text(
        f"{site_width}'-0\"",
        dxfattribs={
            "layer": "A-DIMS",
            "insert": (site_width / 2, y_dim - 1.5),
            "height": 1.5,
            "halign": 4,
        },
    )
    x_dim = -dim_offset
    msp.add_line((x_dim, 0), (x_dim, depth), dxfattribs={"layer": "A-DIMS"})
    msp.add_line((x_dim - 0.5, 0), (x_dim + 0.5, 0), dxfattribs={"layer": "A-DIMS"})
    msp.add_line((x_dim - 0.5, depth), (x_dim + 0.5, depth), dxfattribs={"layer": "A-DIMS"})
    msp.add_text(
        f"{depth}'-0\"",
        dxfattribs={
            "layer": "A-DIMS",
            "insert": (x_dim - 1.5, depth / 2),
            "height": 1.5,
            "rotation": 90,
            "halign": 4,
        },
    )


# ── Public entry point ────────────────────────────────────────────────────────

def export_dxf(project: ArchitectureProject, output_path: Path) -> bytes:
    """Build and write a deepened DXF floor plan for the project."""
    doc = ezdxf.new(dxfversion="R2010")
    doc.units = units.FT

    for name, color, lw in LAYERS:
        layer = doc.layers.new(name)
        layer.color = color
        layer.lineweight = round(lw * 100)

    msp = doc.modelspace()
    site = project.site
    depth = site.depth
    unit = "ft" if project.units == "feet" else "m"
    rooms_by_id = {r.id: r for r in project.rooms}

    # Site boundary
    pts_site = [(0, 0), (site.width, 0), (site.width, depth), (0, depth)]
    msp.add_lwpolyline(pts_site, close=True, dxfattribs={"layer": "A-SITE"})

    # Rooms: hatch → wall boundary → label → dims
    for room in project.rooms:
        _add_room_hatch(msp, room, depth)
        _add_room_wall(msp, room, depth)
        _add_room_text(msp, room, depth, unit)
        _add_room_dims(msp, room, depth)

    # Doors and windows
    for door in project.doors:
        room = rooms_by_id.get(door.room_id)
        if room:
            _add_door(msp, door, room, depth)
    for win in project.windows:
        room = rooms_by_id.get(win.room_id)
        if room:
            _add_window(msp, win, room, depth)

    # Call-out tags
    _add_opening_tags(msp, project.doors, project.windows, rooms_by_id, depth)

    # Site dimensions
    _add_site_dims(msp, site.width, depth)

    # North arrow + title block
    _add_north_arrow(msp, site.width, depth)
    _add_title_block(msp, project, site.width, depth)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(output_path))
    return output_path.read_bytes()
