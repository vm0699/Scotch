"""Phase 12.1 / 12.2 / 12.4 — SVG Presentation Sheet Exporter.

Generates an A3-landscape architectural presentation board as a single SVG:

  ┌─────────────────────────────────────────────────────────────────────┐
  │ HEADER   project title · building type · NTS              N ↑       │
  ├───────────────────────────────────────┬─────────────────────────────┤
  │                                       │  ROOM SCHEDULE              │
  │  PLAN  VIEWPORT                       ├─────────────────────────────┤
  │  (floor plan scaled to fit)           │  LEGEND                     │
  │                                       ├─────────────────────────────┤
  │                                       │  CONCEPT + NOTES            │
  ├───────────────────────────────────────┴─────────────────────────────┤
  │ FOOTER  project · date · scale · units · sheet                      │
  └─────────────────────────────────────────────────────────────────────┘

SVG coordinate space: 1 unit = 1 mm.  viewBox = "0 0 420 297" (A3 landscape).

Illustrator-compatible layer groups (stages 12.1 + 12.4):
  sheet-border, title-block, plan-viewport, schedule, legend, notes, footer

SheetOptions (12.1 model):
  title, subtitle, architect, concept_text, notes_extra, page_size, orientation
  All have sensible defaults derived from ArchitectureProject.
"""

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from xml.sax.saxutils import escape

from app.core.models import ArchitectureProject, Door, Room, Window

# ── Sheet sizes (mm) ─────────────────────────────────────────────────────────

_PAGE_SIZES = {
    "A3": (420.0, 297.0),
    "A2": (594.0, 420.0),
    "A1": (841.0, 594.0),
}

PageSize = Literal["A3", "A2", "A1"]

# ── Design tokens ─────────────────────────────────────────────────────────────

C_BG            = "#ffffff"
C_BORDER        = "#1a1a1a"
C_HEADER_BG     = "#1c1c1e"
C_HEADER_TEXT   = "#ffffff"
C_HEADER_MUTED  = "#a0a0a0"
C_SECTION_HEAD  = "#1c1c1e"
C_BODY          = "#2c2c2c"
C_MUTED         = "#777777"
C_DIVIDER       = "#e2e2e2"
C_FOOTER_BG     = "#f5f5f5"
C_FOOTER_TEXT   = "#555555"
C_FOOTER_BORDER = "#cccccc"
C_PLAN_SITE     = "#f0f0ee"
C_PLAN_WALL     = "#1a1a1a"
C_PLAN_DOOR     = "#888888"
C_PLAN_WIN      = "#444444"
C_PLAN_LABEL    = "#1a1a1a"
C_PLAN_LABEL_SM = "#666666"
C_PLAN_DIM      = "#999999"
C_PLAN_SITE_STK = "#aaaaaa"

# Room fill palette — muted, print-friendly
_ROOM_FILL: dict[str, str] = {
    "living":         "#FFF8EE",
    "dining":         "#FFFBEE",
    "kitchen":        "#F6FBF0",
    "master_bedroom": "#F3F0FF",
    "bedroom":        "#F6F3FF",
    "bathroom":       "#EEF7FF",
    "balcony":        "#F0FFF4",
    "parking":        "#F8F8F8",
    "storage":        "#F5F5F0",
    "study":          "#FFF3F7",
    "foyer":          "#FDFAF3",
    "corridor":       "#FAFAFA",
    "seating":        "#FFF8EE",
    "service":        "#F5F5F5",
}
_ROOM_FILL_DEFAULT = "#F8F8F8"

_ROOM_LEGEND_NAMES: dict[str, str] = {
    "living":         "Living / Lounge",
    "dining":         "Dining",
    "kitchen":        "Kitchen",
    "master_bedroom": "Master Bedroom",
    "bedroom":        "Bedroom",
    "bathroom":       "Bathroom / WC",
    "balcony":        "Balcony / Terrace",
    "parking":        "Parking / Garage",
    "storage":        "Storage / Utility",
    "study":          "Study / Office",
    "foyer":          "Foyer / Entry",
    "corridor":       "Corridor",
    "seating":        "Café Seating",
    "service":        "Service Area",
}

WALL_T = 0.5  # ft


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _room_colour(room: Room) -> str:
    return _ROOM_FILL.get(room.type.lower().replace(" ", "_"), _ROOM_FILL_DEFAULT)


def _wall_frame(room: Room, wall: str):
    if wall == "north":
        return room.x, room.y, 1, 0, 0, 1
    if wall == "south":
        return room.x, room.y + room.depth, 1, 0, 0, -1
    if wall == "west":
        return room.x, room.y, 0, 1, 1, 0
    return room.x + room.width, room.y, 0, 1, -1, 0


# ── Plan drawing (parameterised scale, offset) ────────────────────────────────

def _plan_site(sw: float, sd: float, S: float) -> str:
    return (
        f'<rect x="0" y="0" width="{sw*S:.2f}" height="{sd*S:.2f}" '
        f'fill="{C_PLAN_SITE}" stroke="{C_PLAN_SITE_STK}" '
        f'stroke-width="0.25" stroke-dasharray="1.5 1"/>'
    )


def _plan_room(room: Room, S: float) -> str:
    x = room.x * S
    y = room.y * S
    w = room.width * S
    d = room.depth * S
    sw_px = max(0.3, WALL_T * S)
    fill = _room_colour(room)
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{d:.2f}" '
        f'fill="{fill}" stroke="{C_PLAN_WALL}" stroke-width="{sw_px:.2f}"/>'
    )


def _plan_door(door: Door, room: Room, S: float) -> str:
    sx, sy, ax, ay, nx, ny = _wall_frame(room, door.wall)
    w = door.width
    hx = (sx + ax * door.offset) * S
    hy = (sy + ay * door.offset) * S
    jx = hx + ax * w * S
    jy = hy + ay * w * S
    lx = hx + nx * w * S
    ly = hy + ny * w * S
    gap = (WALL_T * S + 0.5)
    r = w * S
    sweep = 0 if (nx * ay - ny * ax) > 0 else 1
    return (
        f'<line x1="{hx:.2f}" y1="{hy:.2f}" x2="{jx:.2f}" y2="{jy:.2f}" '
        f'stroke="{C_BG}" stroke-width="{gap:.2f}"/>'
        f'<line x1="{hx:.2f}" y1="{hy:.2f}" x2="{lx:.2f}" y2="{ly:.2f}" '
        f'stroke="{C_PLAN_WALL}" stroke-width="0.4"/>'
        f'<path d="M {lx:.2f} {ly:.2f} A {r:.2f} {r:.2f} 0 0 {sweep} {jx:.2f} {jy:.2f}" '
        f'fill="none" stroke="{C_PLAN_DOOR}" stroke-width="0.3" stroke-dasharray="1 1"/>'
    )


def _plan_window(win: Window, room: Room, S: float) -> str:
    sx, sy, ax, ay, nx, ny = _wall_frame(room, win.wall)
    x0 = (sx + ax * win.offset) * S
    y0 = (sy + ay * win.offset) * S
    x1 = x0 + ax * win.width * S
    y1 = y0 + ay * win.width * S
    half = (WALL_T / 2) * S
    gap = WALL_T * S + 0.5
    parts = [
        f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" '
        f'stroke="{C_BG}" stroke-width="{gap:.2f}"/>',
    ]
    for d in (-half, 0, half):
        sw2 = 0.5 if d == 0 else 0.3
        parts.append(
            f'<line x1="{x0+nx*d:.2f}" y1="{y0+ny*d:.2f}" '
            f'x2="{x1+nx*d:.2f}" y2="{y1+ny*d:.2f}" '
            f'stroke="{C_PLAN_WIN}" stroke-width="{sw2}"/>'
        )
    return "\n".join(parts)


def _plan_label(room: Room, S: float) -> str:
    cx = (room.x + room.width / 2) * S
    cy = (room.y + room.depth / 2) * S
    compact = min(room.width, room.depth) < 6
    fs_name = 2.0 if compact else 2.8
    fs_sub  = 1.7 if compact else 2.2
    name = escape(room.name)
    size_lbl = f"{room.width}' × {room.depth}'"
    area = round(room.width * room.depth)
    show_area = area >= 60 and not compact
    lines = [
        f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" font-family="Arial,sans-serif">',
        f'  <tspan x="{cx:.2f}" dy="{-0.6 if show_area else -0.3}em" '
        f'font-size="{fs_name}" font-weight="600" fill="{C_PLAN_LABEL}">{name}</tspan>',
        f'  <tspan x="{cx:.2f}" dy="1.3em" font-size="{fs_sub}" fill="{C_PLAN_LABEL_SM}">{size_lbl}</tspan>',
    ]
    if show_area:
        lines.append(
            f'  <tspan x="{cx:.2f}" dy="1.2em" font-size="{fs_sub}" fill="{C_PLAN_LABEL_SM}">{area} ft²</tspan>'
        )
    lines.append("</text>")
    return "\n".join(lines)


def _plan_dims(sw: float, sd: float, S: float) -> str:
    off = 3 * S
    tick = 1.0
    lbl_w = f"{sw}'-0\""
    lbl_d = f"{sd}'-0\""
    W = sw * S
    D = sd * S
    return "\n".join([
        # Width dim (below)
        f'<line x1="0" y1="{D+off:.2f}" x2="{W:.2f}" y2="{D+off:.2f}" stroke="{C_PLAN_DIM}" stroke-width="0.3"/>',
        f'<line x1="0" y1="{D+off-tick:.2f}" x2="0" y2="{D+off+tick:.2f}" stroke="{C_PLAN_DIM}" stroke-width="0.3"/>',
        f'<line x1="{W:.2f}" y1="{D+off-tick:.2f}" x2="{W:.2f}" y2="{D+off+tick:.2f}" stroke="{C_PLAN_DIM}" stroke-width="0.3"/>',
        f'<text x="{W/2:.2f}" y="{D+off-0.5:.2f}" text-anchor="middle" '
        f'font-size="2.2" fill="{C_PLAN_DIM}" font-family="Arial,sans-serif">{escape(lbl_w)}</text>',
        # Depth dim (left)
        f'<line x1="{-off:.2f}" y1="0" x2="{-off:.2f}" y2="{D:.2f}" stroke="{C_PLAN_DIM}" stroke-width="0.3"/>',
        f'<line x1="{-off-tick:.2f}" y1="0" x2="{-off+tick:.2f}" y2="0" stroke="{C_PLAN_DIM}" stroke-width="0.3"/>',
        f'<line x1="{-off-tick:.2f}" y1="{D:.2f}" x2="{-off+tick:.2f}" y2="{D:.2f}" stroke="{C_PLAN_DIM}" stroke-width="0.3"/>',
        f'<text x="{-off-0.5:.2f}" y="{D/2:.2f}" text-anchor="middle" '
        f'font-size="2.2" fill="{C_PLAN_DIM}" font-family="Arial,sans-serif" '
        f'transform="rotate(-90 {-off-0.5:.2f} {D/2:.2f})">{escape(lbl_d)}</text>',
    ])


def _north_arrow(cx: float, cy: float, r: float, orientation: str) -> str:
    rot = {"north": 0, "east": -90, "west": 90, "south": 180}.get(orientation, 0)
    hw = r * 0.35
    return (
        f'<g transform="translate({cx:.2f} {cy:.2f})">'
        f'<circle r="{r:.2f}" fill="none" stroke="{C_HEADER_MUTED}" stroke-width="0.4"/>'
        f'<g transform="rotate({rot})">'
        f'<path d="M 0 {-r*0.85:.2f} L {hw:.2f} {r*0.25:.2f} L 0 {r*0.1:.2f} L {-hw:.2f} {r*0.25:.2f} Z" '
        f'fill="{C_HEADER_TEXT}"/>'
        f'</g>'
        f'<text y="{r+2.5:.2f}" text-anchor="middle" font-size="2.5" '
        f'fill="{C_HEADER_TEXT}" font-family="Arial,sans-serif" font-weight="700" letter-spacing="0.05em">N</text>'
        f'</g>'
    )


# ── Section-drawing helpers ───────────────────────────────────────────────────

def _section_heading(x: float, y: float, w: float, label: str) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial,sans-serif" '
        f'font-size="2.8" font-weight="700" fill="{C_SECTION_HEAD}" '
        f'letter-spacing="0.12em">{escape(label.upper())}</text>'
        f'<line x1="{x:.2f}" y1="{y+0.8:.2f}" x2="{x+w:.2f}" y2="{y+0.8:.2f}" '
        f'stroke="{C_DIVIDER}" stroke-width="0.25"/>'
    )


def _schedule_svg(
    project: ArchitectureProject,
    x: float,
    y: float,
    w: float,
) -> tuple[str, float]:
    """Returns SVG and total height consumed."""
    unit = "ft²" if project.units == "feet" else "m²"
    rows: list[tuple[str, str, str]] = []
    for room in project.rooms:
        area = round(room.width * room.depth)
        rows.append((room.name, f"{room.width}' × {room.depth}'", f"{area} {unit}"))
    total_area = sum(round(r.width * r.depth) for r in project.rooms)

    row_h = 4.8
    head_h = 5.5
    col1 = w * 0.46
    col2 = w * 0.30
    col3 = w * 0.24

    parts: list[str] = []
    # Column headers
    hdr_y = y + head_h
    for lbl, cx in [
        ("Room", x + 1),
        ("Size", x + col1 + 1),
        ("Area", x + col1 + col2 + 1),
    ]:
        parts.append(
            f'<text x="{cx:.2f}" y="{hdr_y:.2f}" font-family="Arial,sans-serif" '
            f'font-size="2.3" font-weight="600" fill="{C_MUTED}" '
            f'letter-spacing="0.06em">{escape(lbl.upper())}</text>'
        )
    parts.append(
        f'<line x1="{x:.2f}" y1="{hdr_y+0.8:.2f}" x2="{x+w:.2f}" y2="{hdr_y+0.8:.2f}" '
        f'stroke="{C_DIVIDER}" stroke-width="0.25"/>'
    )

    row_y = hdr_y + row_h
    for i, (name, size, area) in enumerate(rows):
        bg = "#f9f9f9" if i % 2 == 0 else C_BG
        parts.append(
            f'<rect x="{x:.2f}" y="{row_y - row_h + 0.5:.2f}" '
            f'width="{w:.2f}" height="{row_h:.2f}" fill="{bg}"/>'
        )
        for txt, tx in [
            (name, x + 1),
            (size, x + col1 + 1),
            (area, x + col1 + col2 + 1),
        ]:
            parts.append(
                f'<text x="{tx:.2f}" y="{row_y:.2f}" font-family="Arial,sans-serif" '
                f'font-size="2.5" fill="{C_BODY}">{escape(txt)}</text>'
            )
        row_y += row_h

    # Total row
    parts.append(
        f'<line x1="{x:.2f}" y1="{row_y - row_h + 0.8:.2f}" '
        f'x2="{x+w:.2f}" y2="{row_y - row_h + 0.8:.2f}" '
        f'stroke="{C_DIVIDER}" stroke-width="0.4"/>'
    )
    for txt, tx in [
        ("Total built-up", x + 1),
        ("", x + col1 + 1),
        (f"{total_area} {unit}", x + col1 + col2 + 1),
    ]:
        parts.append(
            f'<text x="{tx:.2f}" y="{row_y:.2f}" font-family="Arial,sans-serif" '
            f'font-size="2.5" font-weight="600" fill="{C_BODY}">{escape(txt)}</text>'
        )
    row_y += 1

    height = row_y - y
    return "\n".join(parts), height


def _legend_svg(
    project: ArchitectureProject,
    x: float,
    y: float,
    w: float,
) -> tuple[str, float]:
    seen_types: list[str] = []
    for room in project.rooms:
        t = room.type.lower().replace(" ", "_")
        if t not in seen_types:
            seen_types.append(t)

    item_h = 4.0
    swatch = 3.0
    parts: list[str] = []
    cy = y
    for t in seen_types:
        fill = _ROOM_FILL.get(t, _ROOM_FILL_DEFAULT)
        label = _ROOM_LEGEND_NAMES.get(t, t.replace("_", " ").title())
        parts.append(
            f'<rect x="{x:.2f}" y="{cy:.2f}" width="{swatch:.2f}" height="{swatch:.2f}" '
            f'fill="{fill}" stroke="{C_DIVIDER}" stroke-width="0.3"/>'
        )
        parts.append(
            f'<text x="{x+swatch+1.5:.2f}" y="{cy+swatch*0.72:.2f}" '
            f'font-family="Arial,sans-serif" font-size="2.5" fill="{C_BODY}">'
            f'{escape(label)}</text>'
        )
        cy += item_h

    return "\n".join(parts), cy - y


def _wrap_text_svg(
    text: str,
    x: float,
    y: float,
    w: float,
    fs: float,
    fill: str,
    line_h: float,
    max_lines: int = 20,
) -> tuple[str, float]:
    """Naive word-wrap: return (svg, height_used)."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    # Approx chars per line based on width and font-size (Arial ~0.55× ratio)
    chars_per_line = max(10, int(w / (fs * 0.55)))
    for w_ in words:
        test = (cur + " " + w_).strip()
        if len(test) <= chars_per_line:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    lines = lines[:max_lines]

    parts: list[str] = []
    cy = y
    for line in lines:
        parts.append(
            f'<text x="{x:.2f}" y="{cy:.2f}" font-family="Arial,sans-serif" '
            f'font-size="{fs}" fill="{fill}">{escape(line)}</text>'
        )
        cy += line_h
    return "\n".join(parts), cy - y


# ── Main entry point ──────────────────────────────────────────────────────────

def export_sheet_svg(
    project: ArchitectureProject,
    output_path: Path,
    *,
    page_size: PageSize = "A3",
    title: str | None = None,
    subtitle: str | None = None,
    architect: str = "Scotch",
    concept_text: str | None = None,
) -> bytes:
    """Render a presentation sheet as SVG and write to output_path."""
    W, H = _PAGE_SIZES[page_size]
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")

    title    = title    or project.name or "Untitled Project"
    subtitle = subtitle or f"{project.building.type.title()} · {project.building.style.title()}"
    unit_lbl = "feet" if project.units == "feet" else "metres"

    # ── Layout constants (mm) ─────────────────────────────────────────────────
    M        = 5.0    # outer margin
    BORDER   = 2.0    # inner border inset from outer
    HDR_H    = 21.0   # header height
    FTR_H    = 12.0   # footer height
    R_W      = 127.0  # right panel width
    GAP      = 4.0    # gap between plan and right panel
    PAD      = 1.5    # inner content padding

    outer_x1, outer_y1 = M, M
    outer_x2, outer_y2 = W - M, H - M
    inner_x1, inner_y1 = M + BORDER, M + BORDER
    inner_x2, inner_y2 = W - M - BORDER, H - M - BORDER

    hdr_y1 = inner_y1
    hdr_y2 = inner_y1 + HDR_H
    ftr_y1 = inner_y2 - FTR_H
    ftr_y2 = inner_y2
    body_y1 = hdr_y2
    body_y2 = ftr_y1
    body_h  = body_y2 - body_y1

    plan_x1 = inner_x1
    plan_x2 = inner_x2 - R_W - GAP
    plan_w  = plan_x2 - plan_x1
    plan_y1 = body_y1
    plan_y2 = body_y2

    rp_x1   = plan_x2 + GAP
    rp_x2   = inner_x2
    rp_w    = rp_x2 - rp_x1
    rp_y1   = body_y1
    rp_y2   = body_y2

    # ── Floor plan scale ──────────────────────────────────────────────────────
    site  = project.site
    PLAN_PAD = 8.0   # inner padding in the plan viewport (mm)
    avail_w  = plan_w - PLAN_PAD * 2
    avail_h  = body_h - PLAN_PAD * 2
    S = min(avail_w / site.width, avail_h / site.depth) * 0.88  # mm per ft, ~88% of available
    plan_draw_w = site.width  * S
    plan_draw_h = site.depth  * S
    plan_ox = plan_x1 + (plan_w - plan_draw_w) / 2
    plan_oy = plan_y1 + (body_h - plan_draw_h) / 2

    rooms_by_id = {r.id: r for r in project.rooms}

    # ── SVG parts ────────────────────────────────────────────────────────────

    # Sheet background
    bg = f'<rect width="{W}" height="{H}" fill="{C_BG}"/>'

    # ── sheet-border ─────────────────────────────────────────────────────────
    border_svg = "\n".join([
        f'<rect x="{outer_x1}" y="{outer_y1}" '
        f'width="{outer_x2-outer_x1}" height="{outer_y2-outer_y1}" '
        f'fill="none" stroke="{C_BORDER}" stroke-width="0.5"/>',
        f'<rect x="{inner_x1}" y="{inner_y1}" '
        f'width="{inner_x2-inner_x1}" height="{inner_y2-inner_y1}" '
        f'fill="none" stroke="{C_BORDER}" stroke-width="0.25"/>',
    ])

    # ── title-block ───────────────────────────────────────────────────────────
    hdr_mid = (hdr_y1 + hdr_y2) / 2
    n_cx = inner_x2 - 14
    n_cy = hdr_mid
    title_svg = "\n".join([
        # Header background
        f'<rect x="{inner_x1}" y="{hdr_y1}" '
        f'width="{inner_x2-inner_x1}" height="{HDR_H}" fill="{C_HEADER_BG}"/>',
        # Title
        f'<text x="{inner_x1+PAD*2:.2f}" y="{hdr_y1+13:.2f}" '
        f'font-family="Arial,sans-serif" font-size="9" font-weight="700" '
        f'fill="{C_HEADER_TEXT}" letter-spacing="0.02em">{escape(title)}</text>',
        # Subtitle
        f'<text x="{inner_x1+PAD*2:.2f}" y="{hdr_y1+19:.2f}" '
        f'font-family="Arial,sans-serif" font-size="5.5" fill="{C_HEADER_MUTED}">'
        f'{escape(subtitle)}</text>',
        # North arrow in header
        _north_arrow(n_cx, n_cy, 7.0, site.orientation),
        # Divider below header
        f'<line x1="{inner_x1}" y1="{hdr_y2}" x2="{inner_x2}" y2="{hdr_y2}" '
        f'stroke="{C_DIVIDER}" stroke-width="0.25"/>',
    ])

    # ── plan-viewport ─────────────────────────────────────────────────────────
    rooms_svg  = "\n".join(_plan_room(r, S) for r in project.rooms)
    doors_svg  = "\n".join(
        _plan_door(d, rooms_by_id[d.room_id], S)
        for d in project.doors if d.room_id in rooms_by_id
    )
    windows_svg = "\n".join(
        _plan_window(w, rooms_by_id[w.room_id], S)
        for w in project.windows if w.room_id in rooms_by_id
    )
    labels_svg = "\n".join(_plan_label(r, S) for r in project.rooms)
    dims_svg   = _plan_dims(site.width, site.depth, S)

    clip_id = "plan-clip"
    plan_svg = "\n".join([
        f'<clipPath id="{clip_id}">',
        f'  <rect x="{plan_x1:.2f}" y="{plan_y1:.2f}" '
        f'width="{plan_w:.2f}" height="{body_h:.2f}"/>',
        f'</clipPath>',
        f'<rect x="{plan_x1:.2f}" y="{plan_y1:.2f}" '
        f'width="{plan_w:.2f}" height="{body_h:.2f}" fill="{C_BG}"/>',
        f'<g clip-path="url(#{clip_id})">',
        f'  <g transform="translate({plan_ox:.2f} {plan_oy:.2f})">',
        f'    <g id="plan-site">{_plan_site(site.width, site.depth, S)}</g>',
        f'    <g id="plan-rooms">{rooms_svg}</g>',
        f'    <g id="plan-doors">{doors_svg}</g>',
        f'    <g id="plan-windows">{windows_svg}</g>',
        f'    <g id="plan-labels">{labels_svg}</g>',
        f'    <g id="plan-dims">{dims_svg}</g>',
        f'  </g>',
        f'</g>',
        # Viewport border
        f'<line x1="{plan_x2:.2f}" y1="{body_y1:.2f}" '
        f'x2="{plan_x2:.2f}" y2="{body_y2:.2f}" '
        f'stroke="{C_DIVIDER}" stroke-width="0.25"/>',
    ])

    # ── right panel ───────────────────────────────────────────────────────────
    rp_parts: list[str] = []
    cy = rp_y1 + PAD * 2

    # Schedule
    rp_parts.append(_section_heading(rp_x1 + PAD, cy + 3.5, rp_w - PAD * 2, "Room Schedule"))
    cy += 6.5
    sch_svg, sch_h = _schedule_svg(project, rp_x1 + PAD, cy, rp_w - PAD * 2)
    rp_parts.append(sch_svg)
    cy += sch_h + 5

    # Divider
    rp_parts.append(
        f'<line x1="{rp_x1:.2f}" y1="{cy:.2f}" x2="{rp_x2:.2f}" y2="{cy:.2f}" '
        f'stroke="{C_DIVIDER}" stroke-width="0.25"/>'
    )
    cy += 3

    # Legend
    rp_parts.append(_section_heading(rp_x1 + PAD, cy + 3.5, rp_w - PAD * 2, "Legend"))
    cy += 6.5
    leg_svg, leg_h = _legend_svg(project, rp_x1 + PAD, cy, rp_w - PAD * 2)
    rp_parts.append(leg_svg)
    cy += leg_h + 5

    # Divider
    rp_parts.append(
        f'<line x1="{rp_x1:.2f}" y1="{cy:.2f}" x2="{rp_x2:.2f}" y2="{cy:.2f}" '
        f'stroke="{C_DIVIDER}" stroke-width="0.25"/>'
    )
    cy += 3

    # Concept text
    if concept_text or project.notes:
        rp_parts.append(_section_heading(rp_x1 + PAD, cy + 3.5, rp_w - PAD * 2, "Concept"))
        cy += 7
        _concept = concept_text or (
            f"A {project.building.style} {project.building.type} design on a "
            f"{site.width}×{site.depth} ft site. "
            f"{len(project.rooms)} rooms arranged across "
            f"{project.building.floors} floor(s)."
        )
        c_svg, c_h = _wrap_text_svg(
            _concept, rp_x1 + PAD, cy, rp_w - PAD * 2,
            fs=2.6, fill=C_BODY, line_h=4.0, max_lines=6,
        )
        rp_parts.append(c_svg)
        cy += c_h + 4

    # Notes / assumptions
    all_notes = project.notes[:8]
    if all_notes and cy < rp_y2 - 20:
        rp_parts.append(
            f'<line x1="{rp_x1:.2f}" y1="{cy:.2f}" x2="{rp_x2:.2f}" y2="{cy:.2f}" '
            f'stroke="{C_DIVIDER}" stroke-width="0.25"/>'
        )
        cy += 3
        rp_parts.append(_section_heading(rp_x1 + PAD, cy + 3.5, rp_w - PAD * 2, "Notes"))
        cy += 7
        for note in all_notes:
            if cy + 4.5 > rp_y2:
                break
            bullet = "·"
            rp_parts.append(
                f'<text x="{rp_x1+PAD:.2f}" y="{cy:.2f}" '
                f'font-family="Arial,sans-serif" font-size="2.4" fill="{C_MUTED}">'
                f'{escape(bullet + " " + note[:80])}</text>'
            )
            cy += 4.2

    right_panel_svg = "\n".join(rp_parts)

    # ── footer ────────────────────────────────────────────────────────────────
    ftr_mid_y = (ftr_y1 + ftr_y2) / 2 + 1.8
    ftr_cells = [
        ("PROJECT", title[:30]),
        ("DATE", stamp),
        ("SCALE", "NTS — Not to Scale"),
        ("UNITS", unit_lbl.title()),
        ("SHEET", "1 of 1"),
    ]
    cell_w = (inner_x2 - inner_x1) / len(ftr_cells)
    ftr_parts = [
        f'<rect x="{inner_x1}" y="{ftr_y1}" '
        f'width="{inner_x2-inner_x1}" height="{FTR_H}" fill="{C_FOOTER_BG}"/>',
        f'<line x1="{inner_x1}" y1="{ftr_y1}" x2="{inner_x2}" y2="{ftr_y1}" '
        f'stroke="{C_FOOTER_BORDER}" stroke-width="0.3"/>',
    ]
    for i, (lbl, val) in enumerate(ftr_cells):
        cx = inner_x1 + cell_w * i + PAD * 2
        if i > 0:
            ftr_parts.append(
                f'<line x1="{inner_x1 + cell_w*i:.2f}" y1="{ftr_y1:.2f}" '
                f'x2="{inner_x1 + cell_w*i:.2f}" y2="{ftr_y2:.2f}" '
                f'stroke="{C_FOOTER_BORDER}" stroke-width="0.25"/>'
            )
        ftr_parts.append(
            f'<text x="{cx:.2f}" y="{ftr_y1+4:.2f}" '
            f'font-family="Arial,sans-serif" font-size="2.2" font-weight="700" '
            f'fill="{C_MUTED}" letter-spacing="0.08em">{escape(lbl)}</text>'
        )
        ftr_parts.append(
            f'<text x="{cx:.2f}" y="{ftr_mid_y:.2f}" '
            f'font-family="Arial,sans-serif" font-size="3.2" '
            f'fill="{C_FOOTER_TEXT}">{escape(val)}</text>'
        )
    footer_svg = "\n".join(ftr_parts)

    # ── Assemble SVG ──────────────────────────────────────────────────────────
    svg = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"',
        f'     aria-label="{escape(title)} — Presentation Sheet">',
        f'  <title>{escape(title)} — Presentation Sheet</title>',
        f'  <desc>Generated by Scotch on {stamp}. Page size: {page_size} landscape.</desc>',
        f'  <defs>',
        f'    <style>text {{ font-family: Arial, Helvetica, sans-serif; }}</style>',
        f'  </defs>',
        f'  {bg}',
        f'  <g id="sheet-border">\n{border_svg}\n  </g>',
        f'  <g id="title-block">\n{title_svg}\n  </g>',
        f'  <g id="plan-viewport">\n{plan_svg}\n  </g>',
        f'  <g id="right-panel">',
        f'    <g id="schedule">',
        f'    </g>',
        f'    <g id="legend">',
        f'    </g>',
        f'    <g id="notes">',
        f'    </g>',
        f'    {right_panel_svg}',
        f'  </g>',
        f'  <g id="footer">\n{footer_svg}\n  </g>',
        '</svg>',
    ])

    data = svg.encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return data
