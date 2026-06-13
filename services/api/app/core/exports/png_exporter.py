"""Stage 7.3 — PNG export.

Draws directly from ArchitectureProject geometry using Pillow.
Chosen route: Pillow ImageDraw (cross-platform, zero native DLL deps on Windows).
cairosvg requires cairo DLLs on Windows which are painful; this avoids that entirely.

Output is 2× SCALE (24 px/ft) for crisp text. Doors include the swing arc.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.models import ArchitectureProject, Door, Room, Window

# 2× for higher-res PNG
SCALE = 24  # px per ft (2× the SVG SCALE of 12)
WALL_T = 0.5  # ft
WALL_PX = max(2, round(WALL_T * SCALE))
MARGIN = 128  # px (2× the SVG margin)

# Colours as (R, G, B) or (R, G, B, A)
BG = (255, 255, 255)
C_SITE_FILL = (240, 240, 240)
C_SITE_STROKE = (136, 136, 136)
C_ROOM_FILL = (255, 255, 255)
C_ROOM_STROKE = (26, 26, 26)
C_DOOR_LEAF = (26, 26, 26)
C_DOOR_ARC = (136, 136, 136)
C_WIN_LINE = (26, 26, 26)
C_LABEL = (26, 26, 26)
C_MUTED = (102, 102, 102)
C_DIM = (136, 136, 136)


def _wall_frame(room: Room, wall: str):
    if wall == "north":
        return room.x, room.y, 1, 0, 0, 1
    if wall == "south":
        return room.x, room.y + room.depth, 1, 0, 0, -1
    if wall == "west":
        return room.x, room.y, 0, 1, 1, 0
    return room.x + room.width, room.y, 0, 1, -1, 0


def _pillow_arc_angles(
    jamb_dx: float, jamb_dy: float, leaf_dx: float, leaf_dy: float
) -> tuple[float, float]:
    """Return (start°, end°) for Pillow's CW arc between the two directions."""
    a_jamb = math.degrees(math.atan2(jamb_dy, jamb_dx)) % 360
    a_leaf = math.degrees(math.atan2(leaf_dy, leaf_dx)) % 360
    # Pick the short arc (≤180°): go CW from a_jamb to a_leaf
    diff = (a_leaf - a_jamb) % 360
    if diff > 180:
        # Swap so the CW arc is the short one
        a_jamb, a_leaf = a_leaf, a_jamb
        if a_leaf < a_jamb:
            a_leaf += 360
    else:
        if a_leaf < a_jamb:
            a_leaf += 360
    return a_jamb, a_leaf


def _draw_door(draw: ImageDraw.ImageDraw, door: Door, room: Room, ox: int, oy: int) -> None:
    sx, sy, ax, ay, nx, ny = _wall_frame(room, door.wall)
    w = door.width
    hx = ox + (sx + ax * door.offset) * SCALE
    hy = oy + (sy + ay * door.offset) * SCALE
    jx = hx + ax * w * SCALE
    jy = hy + ay * w * SCALE
    lx = hx + nx * w * SCALE
    ly = hy + ny * w * SCALE

    # Door-width gap: erase wall (draw white rectangle along the gap)
    gap_hw = (WALL_T * SCALE + 2) / 2
    if ax != 0:  # horizontal wall
        draw.rectangle([hx, hy - gap_hw, jx, hy + gap_hw], fill=C_ROOM_FILL)
    else:  # vertical wall
        draw.rectangle([hx - gap_hw, hy, hx + gap_hw, jy], fill=C_ROOM_FILL)

    # Door leaf
    draw.line([(hx, hy), (lx, ly)], fill=C_DOOR_LEAF, width=2)

    # Swing arc
    r = w * SCALE
    jamb_dx, jamb_dy = jx - hx, jy - hy
    leaf_dx, leaf_dy = lx - hx, ly - hy
    sa, ea = _pillow_arc_angles(jamb_dx, jamb_dy, leaf_dx, leaf_dy)
    bbox = [hx - r, hy - r, hx + r, hy + r]
    draw.arc(bbox, start=sa, end=ea, fill=C_DOOR_ARC, width=1)


def _draw_window(draw: ImageDraw.ImageDraw, win: Window, room: Room, ox: int, oy: int) -> None:
    sx, sy, ax, ay, nx, ny = _wall_frame(room, win.wall)
    wx0 = ox + (sx + ax * win.offset) * SCALE
    wy0 = oy + (sy + ay * win.offset) * SCALE
    wx1 = wx0 + ax * win.width * SCALE
    wy1 = wy0 + ay * win.width * SCALE
    half = (WALL_T / 2) * SCALE
    gap_hw = (WALL_T * SCALE + 2) / 2

    # Erase wall gap
    if ax != 0:
        draw.rectangle([wx0, wy0 - gap_hw, wx1, wy0 + gap_hw], fill=C_ROOM_FILL)
    else:
        draw.rectangle([wx0 - gap_hw, wy0, wx0 + gap_hw, wy1], fill=C_ROOM_FILL)

    # 3 parallel lines: sill, glazing, outer sill
    for d in (-half, 0, half):
        draw.line(
            [(wx0 + nx * d, wy0 + ny * d), (wx1 + nx * d, wy1 + ny * d)],
            fill=C_WIN_LINE,
            width=1,
        )


def _draw_dim_line(
    draw: ImageDraw.ImageDraw,
    x1: float, y1: float, x2: float, y2: float,
    label: str,
    vertical: bool = False,
) -> None:
    tick = 6
    draw.line([(x1, y1), (x2, y2)], fill=C_DIM, width=1)
    for px, py in ((x1, y1), (x2, y2)):
        draw.line([(px - tick, py + tick), (px + tick, py - tick)], fill=C_DIM, width=1)

    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except (IOError, OSError):
        font = ImageFont.load_default()

    offset = 14
    if vertical:
        # Approximate: just draw east of midpoint
        draw.text((mx + offset, my), label, fill=C_DIM, font=font, anchor="lm")
    else:
        draw.text((mx, my - offset), label, fill=C_DIM, font=font, anchor="ms")


def export_png(project: ArchitectureProject, output_path: Path) -> bytes:
    """Draw the floor plan with Pillow and write a PNG to output_path."""
    site = project.site
    sw = int(site.width * SCALE)
    sd = int(site.depth * SCALE)
    img_w = sw + MARGIN * 2
    img_h = sd + MARGIN * 2
    ox = MARGIN
    oy = MARGIN

    img = Image.new("RGB", (img_w, img_h), BG)
    draw = ImageDraw.Draw(img)

    # Site boundary
    draw.rectangle([ox, oy, ox + sw, oy + sd], fill=C_SITE_FILL)
    # Simulated dashed border: draw small segments
    dash, gap = 14, 7
    coords = [
        ((ox, oy), (ox + sw, oy), "h"),
        ((ox + sw, oy), (ox + sw, oy + sd), "v"),
        ((ox + sw, oy + sd), (ox, oy + sd), "h"),
        ((ox, oy + sd), (ox, oy), "v"),
    ]
    for (x0, y0), (x1, y1), orient in coords:
        length = abs(x1 - x0 + y1 - y0)
        dx = (x1 - x0) / length if length else 0
        dy = (y1 - y0) / length if length else 0
        pos = 0.0
        on = True
        while pos < length:
            seg = dash if on else gap
            ex = x0 + dx * min(pos + seg, length)
            ey = y0 + dy * min(pos + seg, length)
            if on:
                draw.line([(x0 + dx * pos, y0 + dy * pos), (ex, ey)],
                          fill=C_SITE_STROKE, width=1)
            pos += seg
            on = not on

    rooms_by_id = {r.id: r for r in project.rooms}

    # Rooms: fills + thick walls
    for room in project.rooms:
        rx = ox + int(room.x * SCALE)
        ry = oy + int(room.y * SCALE)
        rw = int(room.width * SCALE)
        rd = int(room.depth * SCALE)
        draw.rectangle([rx, ry, rx + rw, ry + rd],
                       fill=C_ROOM_FILL, outline=C_ROOM_STROKE, width=WALL_PX)

    # Doors
    for door in project.doors:
        room = rooms_by_id.get(door.room_id)
        if room:
            _draw_door(draw, door, room, ox, oy)

    # Windows
    for win in project.windows:
        room = rooms_by_id.get(win.room_id)
        if room:
            _draw_window(draw, win, room, ox, oy)

    # Labels
    try:
        font_name = ImageFont.truetype("arial.ttf", 20)
        font_sub = ImageFont.truetype("arial.ttf", 16)
    except (IOError, OSError):
        font_name = ImageFont.load_default()
        font_sub = font_name

    unit = "ft" if project.units == "feet" else "m"
    for room in project.rooms:
        cx = ox + (room.x + room.width / 2) * SCALE
        cy = oy + (room.y + room.depth / 2) * SCALE
        compact = min(room.width, room.depth) < 6
        area = round(room.width * room.depth)
        show_area = area >= 60 and not compact

        line_h = 22
        n_lines = 2 + (1 if show_area else 0)
        total_h = n_lines * line_h
        ty = cy - total_h / 2 + line_h / 2

        draw.text((cx, ty), room.name, fill=C_LABEL,
                  font=font_name if not compact else font_sub, anchor="ms")
        ty += line_h
        size_str = f"{room.width}' x {room.depth}'"
        draw.text((cx, ty), size_str, fill=C_MUTED, font=font_sub, anchor="ms")
        if show_area:
            ty += line_h
            draw.text((cx, ty), f"{area} {unit}²", fill=C_MUTED, font=font_sub, anchor="ms")

    # Site dimensions
    dim_offset = 40
    _draw_dim_line(draw, ox, oy + sd + dim_offset, ox + sw, oy + sd + dim_offset,
                   f"{site.width}'-0\"")
    _draw_dim_line(draw, ox - dim_offset, oy, ox - dim_offset, oy + sd,
                   f"{site.depth}'-0\"", vertical=True)

    # North arrow (simple text marker top-right)
    try:
        font_n = ImageFont.truetype("arial.ttf", 20)
    except (IOError, OSError):
        font_n = ImageFont.load_default()
    nx_pos = ox + sw + 30
    ny_pos = oy + 20
    draw.text((nx_pos, ny_pos), "N", fill=C_DIM, font=font_n, anchor="mm")
    draw.line([(nx_pos, ny_pos + 10), (nx_pos, ny_pos - 20)], fill=C_DIM, width=2)
    draw.polygon([(nx_pos - 5, ny_pos - 14), (nx_pos + 5, ny_pos - 14), (nx_pos, ny_pos - 26)],
                 fill=C_DIM)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG", optimize=True)
    return output_path.read_bytes()
