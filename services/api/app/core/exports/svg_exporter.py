"""Stage 7.2 — Layered SVG export.

Python port of apps/web/src/features/plan/floor-plan-svg.tsx.

Geometry: x across site width, y along depth, y=0 at entrance (top).
Scale: 12 px/ft, MARGIN 64 px.
Colors: hardcoded print-friendly values (no CSS variables).

Named layer groups: site | rooms | doors | windows | labels | dimensions.
"""

import math
from pathlib import Path
from xml.sax.saxutils import escape

from app.core.models import ArchitectureProject, Door, Room, Window

SCALE = 12  # px per ft — matches frontend SCALE
WALL_T = 0.5  # ft
MARGIN = 64  # px

# Print-friendly colour palette
C_SITE_FILL = "#f0f0f0"
C_SITE_STROKE = "#888888"
C_ROOM_FILL = "#ffffff"
C_ROOM_STROKE = "#1a1a1a"
C_DOOR_GAP = "#ffffff"  # erases wall at opening
C_DOOR_LEAF = "#1a1a1a"
C_DOOR_ARC = "#888888"
C_WIN_GAP = "#ffffff"
C_WIN_LINE = "#1a1a1a"
C_LABEL = "#1a1a1a"
C_MUTED = "#666666"
C_DIM = "#888888"


# ── geometry helpers ─────────────────────────────────────────────────────────


def _wall_frame(room: Room, wall: str) -> tuple[float, float, float, float, float, float]:
    """Returns (sx, sy, along_x, along_y, into_room_x, into_room_y) in plan ft."""
    if wall == "north":
        return room.x, room.y, 1, 0, 0, 1
    if wall == "south":
        return room.x, room.y + room.depth, 1, 0, 0, -1
    if wall == "west":
        return room.x, room.y, 0, 1, 1, 0
    # east
    return room.x + room.width, room.y, 0, 1, -1, 0


# ── per-element SVG fragments ─────────────────────────────────────────────────


def _room_svg(room: Room) -> str:
    x = room.x * SCALE
    y = room.y * SCALE
    w = room.width * SCALE
    d = room.depth * SCALE
    sw = WALL_T * SCALE
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{d:.2f}" '
        f'fill="{C_ROOM_FILL}" stroke="{C_ROOM_STROKE}" stroke-width="{sw}"/>'
    )


def _door_svg(door: Door, room: Room) -> str:
    sx, sy, ax, ay, nx, ny = _wall_frame(room, door.wall)
    w = door.width
    hx = (sx + ax * door.offset) * SCALE
    hy = (sy + ay * door.offset) * SCALE
    jx = hx + ax * w * SCALE  # far jamb
    jy = hy + ay * w * SCALE
    lx = hx + nx * w * SCALE  # leaf end
    ly = hy + ny * w * SCALE
    gap = WALL_T * SCALE + 1
    sweep = 0 if (nx * ay - ny * ax) > 0 else 1
    r = w * SCALE

    return (
        f'<line x1="{hx:.2f}" y1="{hy:.2f}" x2="{jx:.2f}" y2="{jy:.2f}" '
        f'stroke="{C_DOOR_GAP}" stroke-width="{gap:.2f}"/>'
        f'<line x1="{hx:.2f}" y1="{hy:.2f}" x2="{lx:.2f}" y2="{ly:.2f}" '
        f'stroke="{C_DOOR_LEAF}" stroke-width="1.2"/>'
        f'<path d="M {lx:.2f} {ly:.2f} A {r:.2f} {r:.2f} 0 0 {sweep} {jx:.2f} {jy:.2f}" '
        f'fill="none" stroke="{C_DOOR_ARC}" stroke-width="0.8" stroke-dasharray="2.5 2.5"/>'
    )


def _window_svg(win: Window, room: Room) -> str:
    sx, sy, ax, ay, nx, ny = _wall_frame(room, win.wall)
    start_x = (sx + ax * win.offset) * SCALE
    start_y = (sy + ay * win.offset) * SCALE
    end_x = start_x + ax * win.width * SCALE
    end_y = start_y + ay * win.width * SCALE
    half = (WALL_T / 2) * SCALE
    gap = WALL_T * SCALE + 1

    parts = [
        f'<line x1="{start_x:.2f}" y1="{start_y:.2f}" '
        f'x2="{end_x:.2f}" y2="{end_y:.2f}" '
        f'stroke="{C_WIN_GAP}" stroke-width="{gap:.2f}"/>',
    ]
    for i, d in enumerate([-half, 0, half]):
        sx2 = start_x + nx * d
        sy2 = start_y + ny * d
        ex2 = end_x + nx * d
        ey2 = end_y + ny * d
        sw = 1.0 if i == 1 else 0.7
        parts.append(
            f'<line x1="{sx2:.2f}" y1="{sy2:.2f}" x2="{ex2:.2f}" y2="{ey2:.2f}" '
            f'stroke="{C_WIN_LINE}" stroke-width="{sw}"/>'
        )
    return "\n".join(parts)


def _label_svg(room: Room, unit: str) -> str:
    cx = (room.x + room.width / 2) * SCALE
    cy = (room.y + room.depth / 2) * SCALE
    compact = min(room.width, room.depth) < 6
    area = round(room.width * room.depth)
    show_area = area >= 60 and not compact
    name_size = 8.5 if compact else 11
    sub_size = 7.5 if compact else 9
    dy_name = -0.1 if not show_area else -0.7
    name = escape(room.name)
    size_label = f"{room.width}' × {room.depth}'"

    parts = [
        f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" '
        f'font-family="sans-serif" fill="{C_LABEL}">',
        f'  <tspan x="{cx:.2f}" dy="{dy_name}em" '
        f'font-size="{name_size}" font-weight="500">{name}</tspan>',
        f'  <tspan x="{cx:.2f}" dy="1.25em" '
        f'font-size="{sub_size}" fill="{C_MUTED}">{size_label}</tspan>',
    ]
    if show_area:
        parts.append(
            f'  <tspan x="{cx:.2f}" dy="1.25em" '
            f'font-size="9" fill="{C_MUTED}">{area} {unit}²</tspan>'
        )
    parts.append("</text>")
    return "\n".join(parts)


def _dim_line_svg(
    x1: float, y1: float, x2: float, y2: float, label: str, vertical: bool = False
) -> str:
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    tick = 4
    dy_em = "-0.5em" if vertical else "-0.55em"
    transform = f' transform="rotate(-90 {mx:.2f} {my:.2f})"' if vertical else ""

    return (
        f'<g stroke="{C_DIM}" stroke-width="0.8">'
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"/>'
        f'<line x1="{x1 - tick:.2f}" y1="{y1 + tick:.2f}" '
        f'x2="{x1 + tick:.2f}" y2="{y1 - tick:.2f}" stroke-width="1"/>'
        f'<line x1="{x2 - tick:.2f}" y1="{y2 + tick:.2f}" '
        f'x2="{x2 + tick:.2f}" y2="{y2 - tick:.2f}" stroke-width="1"/>'
        f'<text x="{mx:.2f}" y="{my:.2f}" dy="{dy_em}" text-anchor="middle" '
        f'fill="{C_DIM}" stroke="none" font-size="9.5" font-family="sans-serif"'
        f'{transform}>{escape(label)}</text>'
        f"</g>"
    )


def _north_arrow_svg(cx: float, cy: float, top_direction: str) -> str:
    rotation = {"north": 0, "east": -90, "west": 90, "south": 180}.get(top_direction, 0)
    return (
        f'<g transform="translate({cx:.2f} {cy:.2f})">'
        f'<circle r="15" fill="{C_ROOM_FILL}" stroke="{C_DIM}" stroke-width="0.8"/>'
        f'<g transform="rotate({rotation})">'
        f'<path d="M 0 -10 L 4 6 L 0 3.5 L -4 6 Z" fill="{C_ROOM_STROKE}"/>'
        f"</g>"
        f'<text y="28" text-anchor="middle" fill="{C_DIM}" '
        f'font-size="8.5" font-family="sans-serif" letter-spacing="0.08em">N</text>'
        f"</g>"
    )


# ── main entry ────────────────────────────────────────────────────────────────


def export_svg(project: ArchitectureProject, output_path: Path) -> bytes:
    """Render a layered architectural SVG and write it to output_path."""
    site = project.site
    sw = site.width * SCALE
    sd = site.depth * SCALE
    vw = sw + MARGIN * 2
    vh = sd + MARGIN * 2
    unit = "ft" if project.units == "feet" else "m"
    rooms_by_id = {r.id: r for r in project.rooms}
    dim_offset = 26

    # ── layer groups ──────────────────────────────────────────────────

    site_g = (
        f'<rect x="0" y="0" width="{sw:.2f}" height="{sd:.2f}" '
        f'fill="{C_SITE_FILL}" stroke="{C_SITE_STROKE}" '
        f'stroke-width="1" stroke-dasharray="6 3"/>'
    )

    rooms_g = "\n".join(_room_svg(r) for r in project.rooms)

    doors_g = "\n".join(
        _door_svg(door, rooms_by_id[door.room_id])
        for door in project.doors
        if door.room_id in rooms_by_id
    )

    windows_g = "\n".join(
        _window_svg(win, rooms_by_id[win.room_id])
        for win in project.windows
        if win.room_id in rooms_by_id
    )

    labels_g = "\n".join(_label_svg(r, unit) for r in project.rooms)

    dims_g = "\n".join([
        _dim_line_svg(0, sd + dim_offset, sw, sd + dim_offset, f"{site.width}'-0\""),
        _dim_line_svg(-dim_offset, sd, -dim_offset, 0, f"{site.depth}'-0\"", vertical=True),
        _north_arrow_svg(sw + 34, 4, site.orientation),
    ])

    svg = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg viewBox="0 0 {vw:.2f} {vh:.2f}" xmlns="http://www.w3.org/2000/svg"'
        f' aria-label="{escape(project.name)} — floor plan">',
        f'  <g transform="translate({MARGIN} {MARGIN})">',
        f'    <g id="site">\n{site_g}\n    </g>',
        f'    <g id="rooms">\n{rooms_g}\n    </g>',
        f'    <g id="doors">\n{doors_g}\n    </g>',
        f'    <g id="windows">\n{windows_g}\n    </g>',
        f'    <g id="labels">\n{labels_g}\n    </g>',
        f'    <g id="dimensions">\n{dims_g}\n    </g>',
        "  </g>",
        "</svg>",
    ])

    data = svg.encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return data
