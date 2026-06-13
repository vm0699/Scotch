"""Stage 7.4 — DXF export using ezdxf.

Layers:
    A-SITE      site boundary rectangle
    A-WALL      room outer-wall LWPOLYLINE rectangles (poché boundaries)
    A-DOOR      door leaf LINE + swing ARC
    A-WINDOW    window triple-LINE symbol
    A-ROOM-TEXT room name/size MTEXT
    A-DIMS      site dimension lines and text

Coordinate system:
    Plan space: x right, y down (y=0 = entrance edge, top of plan).
    DXF WCS:    x right, y UP (standard CAD). Transform: dxf_y = site_depth - plan_y.
    Direction vectors: (ax, -ay) and (nx, -ny) after the flip.
"""

import math
from pathlib import Path

import ezdxf
from ezdxf import units

from app.core.models import ArchitectureProject, Door, Room, Window

WALL_T = 0.5  # ft — same as plan model

# Layer definitions: (name, color_index, lineweight_mm)
LAYERS = [
    ("A-SITE", 3, 0.18),       # green
    ("A-WALL", 7, 0.35),       # white/black
    ("A-DOOR", 1, 0.18),       # red
    ("A-WINDOW", 4, 0.18),     # cyan
    ("A-ROOM-TEXT", 7, 0.18),
    ("A-DIMS", 8, 0.18),       # gray
]


def _fy(plan_y: float, depth: float) -> float:
    """Flip plan y → DXF y."""
    return depth - plan_y


def _wall_frame_dxf(room: Room, wall: str, depth: float):
    """Returns (sx, sy, ax, ay, nx, ny) in DXF coordinates."""
    if wall == "north":
        sx, sy, ax, ay, nx, ny = room.x, room.y, 1, 0, 0, 1
    elif wall == "south":
        sx, sy, ax, ay, nx, ny = room.x, room.y + room.depth, 1, 0, 0, -1
    elif wall == "west":
        sx, sy, ax, ay, nx, ny = room.x, room.y, 0, 1, 1, 0
    else:  # east
        sx, sy, ax, ay, nx, ny = room.x + room.width, room.y, 0, 1, -1, 0
    return sx, _fy(sy, depth), ax, -ay, nx, -ny


def _add_door(msp, door: Door, room: Room, depth: float) -> None:
    sx, sy, ax, ay, nx, ny = _wall_frame_dxf(room, door.wall, depth)
    w = door.width
    hx = sx + ax * door.offset
    hy = sy + ay * door.offset
    jx = hx + ax * w       # far jamb
    jy = hy + ay * w
    lx = hx + nx * w       # leaf end
    ly = hy + ny * w

    msp.add_line((hx, hy), (lx, ly), dxfattribs={"layer": "A-DOOR"})

    # Swing arc: CCW from leaf to jamb (correct for DXF y-up)
    a_leaf = math.degrees(math.atan2(ly - hy, lx - hx)) % 360
    a_jamb = math.degrees(math.atan2(jy - hy, jx - hx)) % 360

    # SVG sweep tells us direction; replicate for DXF CCW convention
    plan_nx = nx if ay == 0 else -ny  # original plan nx before flip
    plan_ny = -ny if ax == 0 else nx  # crude but correct for rectangular rooms
    svg_sweep = 0 if (plan_nx * (0) - plan_ny * (0)) > 0 else 1  # simplified: always use leaf→jamb CCW
    # Use CCW from a_leaf to a_jamb (short arc)
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
    """Outer-wall boundary LWPOLYLINE (poché) for the room."""
    half = WALL_T / 2
    # Outer corners in DXF coords (expand by half wall-thickness)
    lx = room.x - half
    ly = _fy(room.y - half, depth)  # note: in DXF y-up, expanding "north" means +y
    rx = room.x + room.width + half
    ry = _fy(room.y + room.depth + half, depth)

    # ezdxf LWPOLYLINE: list of (x, y) for a closed rectangle
    pts = [(lx, ry), (rx, ry), (rx, ly), (lx, ly)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-WALL"})


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
            "attachment_point": 5,  # middle-center
        },
    )


def export_dxf(project: ArchitectureProject, output_path: Path) -> bytes:
    """Build and write a DXF floor plan for the project."""
    doc = ezdxf.new(dxfversion="R2010")
    doc.units = units.FT

    # Layers
    for name, color, lw in LAYERS:
        layer = doc.layers.new(name)
        layer.color = color
        layer.lineweight = round(lw * 100)  # ezdxf uses 1/100 mm integers

    msp = doc.modelspace()
    site = project.site
    depth = site.depth
    unit = "ft" if project.units == "feet" else "m"
    rooms_by_id = {r.id: r for r in project.rooms}

    # Site boundary (A-SITE)
    pts_site = [
        (0, 0),
        (site.width, 0),
        (site.width, depth),
        (0, depth),
    ]
    msp.add_lwpolyline(pts_site, close=True, dxfattribs={"layer": "A-SITE"})

    # Rooms (A-WALL) and labels (A-ROOM-TEXT)
    for room in project.rooms:
        _add_room_wall(msp, room, depth)
        _add_room_text(msp, room, depth, unit)

    # Doors (A-DOOR)
    for door in project.doors:
        room = rooms_by_id.get(door.room_id)
        if room:
            _add_door(msp, door, room, depth)

    # Windows (A-WINDOW)
    for win in project.windows:
        room = rooms_by_id.get(win.room_id)
        if room:
            _add_window(msp, win, room, depth)

    # Site dimensions (A-DIMS)
    dim_offset = 3  # ft below/left of site
    # Width dimension (bottom)
    y_dim = -dim_offset
    msp.add_line((0, y_dim), (site.width, y_dim), dxfattribs={"layer": "A-DIMS"})
    msp.add_line((0, y_dim - 0.5), (0, y_dim + 0.5), dxfattribs={"layer": "A-DIMS"})
    msp.add_line((site.width, y_dim - 0.5), (site.width, y_dim + 0.5),
                 dxfattribs={"layer": "A-DIMS"})
    msp.add_text(
        f"{site.width}'-0\"",
        dxfattribs={
            "layer": "A-DIMS",
            "insert": (site.width / 2, y_dim - 1.5),
            "height": 1.5,
            "halign": 4,  # center
        },
    )
    # Depth dimension (left)
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(output_path))
    return output_path.read_bytes()
