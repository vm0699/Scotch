"""Phase 12.3 — PDF Presentation Sheet Exporter.

Generates the same A3-landscape architectural presentation board as a PDF
using reportlab (pure Python, no system-level Cairo / GTK needed).

Layout mirrors sheet_svg_exporter.py exactly; all measurements are first
computed in millimetres then converted to reportlab points (1 mm = 2.8346 pt).

reportlab coordinate system: origin at BOTTOM-LEFT, y increases upward.
Helper _y(mm) flips from SVG-style (top-down mm) to reportlab (bottom-up pt).
"""

import io
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A3, A2, A1
from reportlab.pdfgen import canvas as rl_canvas

from app.core.models import ArchitectureProject, Door, Room, Window

# ── Units ────────────────────────────────────────────────────────────────────

MM = 2.8346  # reportlab points per mm

_PAGE_SIZES_MM = {
    "A3": (420.0, 297.0),
    "A2": (594.0, 420.0),
    "A1": (841.0, 594.0),
}

_RL_PAGE_SIZES = {
    "A3": (A3[1], A3[0]),   # landscape = swap
    "A2": (A2[1], A2[0]),
    "A1": (A1[1], A1[0]),
}

PageSize = Literal["A3", "A2", "A1"]

# ── Colours ───────────────────────────────────────────────────────────────────

def _hc(h: str) -> Color:
    return HexColor(h)

C_BG          = _hc("#ffffff")
C_BORDER      = _hc("#1a1a1a")
C_HEADER_BG   = _hc("#1c1c1e")
C_HEADER_TEXT = _hc("#ffffff")
C_HEADER_MUTED= _hc("#a0a0a0")
C_SECTION     = _hc("#1c1c1e")
C_BODY        = _hc("#2c2c2c")
C_MUTED       = _hc("#777777")
C_DIVIDER     = _hc("#e2e2e2")
C_FOOTER_BG   = _hc("#f5f5f5")
C_FOOTER_TEXT = _hc("#555555")
C_FOOTER_BDR  = _hc("#cccccc")
C_PLAN_SITE   = _hc("#f0f0ee")
C_PLAN_SITE_B = _hc("#aaaaaa")
C_PLAN_WALL   = _hc("#1a1a1a")
C_PLAN_DOOR   = _hc("#888888")
C_PLAN_WIN    = _hc("#444444")
C_PLAN_LABEL  = _hc("#1a1a1a")
C_PLAN_LABEL_S= _hc("#666666")
C_PLAN_DIM    = _hc("#999999")

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


# ── Coordinate helpers ────────────────────────────────────────────────────────

def _pt(mm: float) -> float:
    return mm * MM

def _y(mm: float, page_h_mm: float) -> float:
    """Convert top-down mm to reportlab bottom-up points."""
    return (page_h_mm - mm) * MM

def _wall_frame(room: Room, wall: str):
    if wall == "north":
        return room.x, room.y, 1, 0, 0, 1
    if wall == "south":
        return room.x, room.y + room.depth, 1, 0, 0, -1
    if wall == "west":
        return room.x, room.y, 0, 1, 1, 0
    return room.x + room.width, room.y, 0, 1, -1, 0

def _room_colour(room: Room) -> Color:
    t = room.type.lower().replace(" ", "_")
    return _hc(_ROOM_FILL.get(t, _ROOM_FILL_DEFAULT))


# ── Floor plan drawing (reportlab canvas) ─────────────────────────────────────

def _draw_plan(
    c: rl_canvas.Canvas,
    project: ArchitectureProject,
    ox_mm: float,     # plan draw origin x in mm (from left of page)
    oy_mm: float,     # plan draw origin y in mm (from top of page)
    S: float,         # mm per ft
    page_h: float,    # page height in mm
) -> None:
    """Draw the floor plan at origin (ox_mm, oy_mm) with scale S mm/ft."""
    site = project.site
    rooms_by_id = {r.id: r for r in project.rooms}

    def px(ft: float) -> float:  # ft → reportlab x absolute
        return _pt(ox_mm + ft * S)

    def py(ft: float) -> float:  # plan-y → reportlab y absolute (flip)
        return _y(oy_mm + ft * S, page_h)

    def pts(ft: float) -> float:  # ft → reportlab size
        return _pt(ft * S)

    # Site boundary
    c.setFillColor(C_PLAN_SITE)
    c.setStrokeColor(C_PLAN_SITE_B)
    c.setLineWidth(_pt(0.25))
    c.rect(px(0), py(site.depth), pts(site.width), pts(site.depth), fill=1, stroke=1)

    # Rooms
    for room in project.rooms:
        c.setFillColor(_room_colour(room))
        c.setStrokeColor(C_PLAN_WALL)
        c.setLineWidth(_pt(max(0.3, WALL_T * S)))
        c.rect(px(room.x), py(room.y + room.depth),
               pts(room.width), pts(room.depth), fill=1, stroke=1)

    # Doors
    for door in project.doors:
        room = rooms_by_id.get(door.room_id)
        if not room:
            continue
        sx, sy_, ax, ay, nx, ny = _wall_frame(room, door.wall)
        w = door.width
        hx = sx + ax * door.offset
        hy = sy_ + ay * door.offset
        jx = hx + ax * w
        jy = hy + ay * w
        lx = hx + nx * w
        ly = hy + ny * w
        # Door leaf
        c.setStrokeColor(C_PLAN_WALL)
        c.setLineWidth(_pt(0.4))
        c.line(px(hx), py(hy), px(lx), py(ly))
        # Swing arc (approximate using bezier / arc)
        # reportlab arc: (x1,y1,x2,y2) bounding box, startAng, extent
        r_pt = pts(w)
        # Angles: atan2 in standard math coords (y up), but plan is y-down
        # map plan (y-down) → math (y-up): flip y
        a_leaf = math.degrees(math.atan2(-(ly - hy), lx - hx)) % 360
        a_jamb = math.degrees(math.atan2(-(jy - hy), jx - hx)) % 360
        diff = (a_jamb - a_leaf) % 360
        if diff > 180:
            a_leaf, a_jamb = a_jamb, a_leaf
            diff = 360 - diff
        bx1 = px(hx) - r_pt
        by1 = py(hy) - r_pt
        c.setStrokeColor(C_PLAN_DOOR)
        c.setLineWidth(_pt(0.3))
        c.setDash([_pt(1), _pt(1)])
        c.arc(bx1, by1, bx1 + r_pt * 2, by1 + r_pt * 2,
              startAng=a_leaf, extent=diff)
        c.setDash([])

    # Windows
    for win in project.windows:
        room = rooms_by_id.get(win.room_id)
        if not room:
            continue
        sx, sy_, ax, ay, nx, ny = _wall_frame(room, win.wall)
        x0 = sx + ax * win.offset
        y0 = sy_ + ay * win.offset
        x1 = x0 + ax * win.width
        y1 = y0 + ay * win.width
        half = WALL_T / 2
        for d in (-half, 0, half):
            lw = _pt(0.5 if d == 0 else 0.3)
            c.setStrokeColor(C_PLAN_WIN)
            c.setLineWidth(lw)
            c.line(px(x0 + nx * d), py(y0 + ny * d),
                   px(x1 + nx * d), py(y1 + ny * d))

    # Labels
    c.setFillColor(C_PLAN_LABEL)
    for room in project.rooms:
        cx_mm = ox_mm + (room.x + room.width / 2) * S
        cy_mm = oy_mm + (room.y + room.depth / 2) * S
        compact = min(room.width, room.depth) < 6
        fs_name = _pt(2.6) if not compact else _pt(1.9)
        fs_sub  = _pt(2.0) if not compact else _pt(1.6)
        area    = round(room.width * room.depth)
        show_area = area >= 60 and not compact

        line_h = _pt(3.8)
        n_lines = 2 + (1 if show_area else 0)
        base_y = _y(cy_mm, page_h) + (n_lines - 1) * line_h / 2

        c.setFont("Helvetica-Bold", fs_name)
        c.setFillColor(C_PLAN_LABEL)
        c.drawCentredString(_pt(cx_mm), base_y, room.name)

        c.setFont("Helvetica", fs_sub)
        c.setFillColor(C_PLAN_LABEL_S)
        size_str = f"{room.width}' × {room.depth}'"
        c.drawCentredString(_pt(cx_mm), base_y - line_h, size_str)

        if show_area:
            unit = "ft²" if project.units == "feet" else "m²"
            c.drawCentredString(_pt(cx_mm), base_y - line_h * 2,
                                f"{area} {unit}")

    # Dimension lines
    c.setStrokeColor(C_PLAN_DIM)
    c.setFillColor(C_PLAN_DIM)
    c.setLineWidth(_pt(0.3))
    off_mm = S * 3
    tick = _pt(1.0)
    # Width dim (below)
    yd = _y(oy_mm + site.depth * S + off_mm, page_h)
    c.line(px(0), yd, px(site.width), yd)
    c.line(px(0), yd - tick, px(0), yd + tick)
    c.line(px(site.width), yd - tick, px(site.width), yd + tick)
    c.setFont("Helvetica", _pt(2.2))
    c.drawCentredString(px(site.width / 2), yd + _pt(0.8), f"{site.width}'-0\"")
    # Depth dim (left)
    xd = _pt(ox_mm - off_mm)
    c.line(xd, py(0), xd, py(site.depth))
    c.line(xd - tick, py(0), xd + tick, py(0))
    c.line(xd - tick, py(site.depth), xd + tick, py(site.depth))
    c.saveState()
    c.translate(xd - _pt(1.5), py(site.depth / 2))
    c.rotate(90)
    c.drawCentredString(0, 0, f"{site.depth}'-0\"")
    c.restoreState()


# ── Right-panel drawing ───────────────────────────────────────────────────────

def _section_head(c: rl_canvas.Canvas, x_mm: float, y_mm: float, w_mm: float,
                  label: str, page_h: float) -> float:
    """Draw a section heading, return new y_mm after the heading."""
    c.setFont("Helvetica-Bold", _pt(2.6))
    c.setFillColor(C_SECTION)
    c.drawString(_pt(x_mm), _y(y_mm + 3, page_h), label.upper())
    c.setStrokeColor(C_DIVIDER)
    c.setLineWidth(_pt(0.25))
    c.line(_pt(x_mm), _y(y_mm + 4, page_h),
           _pt(x_mm + w_mm), _y(y_mm + 4, page_h))
    return y_mm + 7


def _draw_schedule(c: rl_canvas.Canvas, project: ArchitectureProject,
                   x_mm: float, y_mm: float, w_mm: float,
                   page_h: float) -> float:
    row_h = 4.8
    unit  = "ft²" if project.units == "feet" else "m²"
    col1  = w_mm * 0.46
    col2  = w_mm * 0.30

    # Header row
    for lbl, cx in [("ROOM", x_mm + 1), ("SIZE", x_mm + col1 + 1),
                    ("AREA", x_mm + col1 + col2 + 1)]:
        c.setFont("Helvetica-Bold", _pt(2.2))
        c.setFillColor(C_MUTED)
        c.drawString(_pt(cx), _y(y_mm + 4.5, page_h), lbl)
    c.setStrokeColor(C_DIVIDER)
    c.setLineWidth(_pt(0.25))
    c.line(_pt(x_mm), _y(y_mm + 5.5, page_h),
           _pt(x_mm + w_mm), _y(y_mm + 5.5, page_h))
    y_mm += 5.5 + row_h

    for i, room in enumerate(project.rooms):
        area = round(room.width * room.depth)
        if i % 2 == 0:
            c.setFillColor(_hc("#f9f9f9"))
            c.rect(_pt(x_mm), _y(y_mm, page_h),
                   _pt(w_mm), _pt(row_h), fill=1, stroke=0)
        c.setFont("Helvetica", _pt(2.5))
        c.setFillColor(C_BODY)
        for txt, cx in [
            (room.name, x_mm + 1),
            (f"{room.width}' × {room.depth}'", x_mm + col1 + 1),
            (f"{area} {unit}", x_mm + col1 + col2 + 1),
        ]:
            c.drawString(_pt(cx), _y(y_mm, page_h), txt)
        y_mm += row_h

    # Total
    total = sum(round(r.width * r.depth) for r in project.rooms)
    c.setStrokeColor(C_DIVIDER)
    c.setLineWidth(_pt(0.4))
    c.line(_pt(x_mm), _y(y_mm - row_h + 1, page_h),
           _pt(x_mm + w_mm), _y(y_mm - row_h + 1, page_h))
    c.setFont("Helvetica-Bold", _pt(2.5))
    c.setFillColor(C_BODY)
    c.drawString(_pt(x_mm + 1), _y(y_mm, page_h), "Total built-up")
    c.drawString(_pt(x_mm + col1 + col2 + 1), _y(y_mm, page_h), f"{total} {unit}")
    return y_mm + 1


def _draw_legend(c: rl_canvas.Canvas, project: ArchitectureProject,
                 x_mm: float, y_mm: float, w_mm: float,
                 page_h: float) -> float:
    seen: list[str] = []
    for room in project.rooms:
        t = room.type.lower().replace(" ", "_")
        if t not in seen:
            seen.append(t)

    item_h = 4.0
    swatch = 3.0
    for t in seen:
        fill = _hc(_ROOM_FILL.get(t, _ROOM_FILL_DEFAULT))
        label = _ROOM_LEGEND_NAMES.get(t, t.replace("_", " ").title())
        c.setFillColor(fill)
        c.setStrokeColor(C_DIVIDER)
        c.setLineWidth(_pt(0.3))
        c.rect(_pt(x_mm), _y(y_mm + swatch, page_h),
               _pt(swatch), _pt(swatch), fill=1, stroke=1)
        c.setFont("Helvetica", _pt(2.5))
        c.setFillColor(C_BODY)
        c.drawString(_pt(x_mm + swatch + 1.5), _y(y_mm + swatch * 0.75, page_h), label)
        y_mm += item_h
    return y_mm


def _draw_notes(c: rl_canvas.Canvas, project: ArchitectureProject,
                x_mm: float, y_mm: float, w_mm: float,
                concept: str | None, page_h: float, max_y_mm: float) -> float:
    if concept:
        # Simple word wrap
        words = concept.split()
        chars = max(10, int(w_mm / (2.6 * 0.55)))
        lines: list[str] = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if len(test) <= chars:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        c.setFont("Helvetica", _pt(2.5))
        c.setFillColor(C_BODY)
        for line in lines[:6]:
            if y_mm + 4.5 > max_y_mm:
                break
            c.drawString(_pt(x_mm), _y(y_mm + 3.5, page_h), line)
            y_mm += 4.0
        y_mm += 2

    for note in project.notes[:8]:
        if y_mm + 4.5 > max_y_mm:
            break
        c.setFont("Helvetica", _pt(2.4))
        c.setFillColor(C_MUTED)
        c.drawString(_pt(x_mm), _y(y_mm + 3.5, page_h), "· " + note[:80])
        y_mm += 4.2
    return y_mm


# ── Main entry point ──────────────────────────────────────────────────────────

def export_sheet_pdf(
    project: ArchitectureProject,
    output_path: Path,
    *,
    page_size: PageSize = "A3",
    title: str | None = None,
    subtitle: str | None = None,
    architect: str = "Scotch",
    concept_text: str | None = None,
) -> bytes:
    """Render a presentation sheet as PDF and write to output_path."""
    W_mm, H_mm = _PAGE_SIZES_MM[page_size]
    rl_size = _RL_PAGE_SIZES[page_size]
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")

    title_str    = title    or project.name or "Untitled Project"
    subtitle_str = subtitle or f"{project.building.type.title()} · {project.building.style.title()}"
    unit_lbl     = "Feet" if project.units == "feet" else "Metres"

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=rl_size)
    c.setTitle(title_str)
    c.setAuthor(architect)
    c.setSubject("Architectural Presentation Sheet — Scotch")

    # ── Layout constants (mm) ─────────────────────────────────────────────────
    M      = 5.0
    BORDER = 2.0
    HDR_H  = 21.0
    FTR_H  = 12.0
    R_W    = 127.0
    GAP    = 4.0
    PAD    = 1.5

    inner_x1 = M + BORDER
    inner_y1 = M + BORDER
    inner_x2 = W_mm - M - BORDER
    inner_y2 = H_mm - M - BORDER

    hdr_y2 = inner_y1 + HDR_H
    ftr_y1 = inner_y2 - FTR_H
    body_y1 = hdr_y2
    body_y2 = ftr_y1
    body_h  = body_y2 - body_y1

    plan_x1 = inner_x1
    plan_x2 = inner_x2 - R_W - GAP
    plan_w  = plan_x2 - plan_x1

    rp_x1  = plan_x2 + GAP
    rp_x2  = inner_x2
    rp_w   = rp_x2 - rp_x1

    # Plan scale
    site = project.site
    PLAN_PAD = 8.0
    avail_w  = plan_w - PLAN_PAD * 2
    avail_h  = body_h - PLAN_PAD * 2
    S = min(avail_w / site.width, avail_h / site.depth) * 0.88
    plan_draw_w = site.width * S
    plan_draw_h = site.depth * S
    plan_ox = plan_x1 + (plan_w - plan_draw_w) / 2
    plan_oy = body_y1 + (body_h - plan_draw_h) / 2

    def _yf(mm: float) -> float:
        return _y(mm, H_mm)

    # ── Sheet background ──────────────────────────────────────────────────────
    c.setFillColor(C_BG)
    c.rect(0, 0, _pt(W_mm), _pt(H_mm), fill=1, stroke=0)

    # ── Sheet borders ─────────────────────────────────────────────────────────
    c.setFillColor(C_BG)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(_pt(0.5))
    c.rect(_pt(M), _yf(H_mm - M), _pt(W_mm - 2*M), _pt(H_mm - 2*M), fill=0, stroke=1)
    c.setLineWidth(_pt(0.25))
    c.rect(_pt(inner_x1), _yf(inner_y2), _pt(inner_x2 - inner_x1),
           _pt(inner_y2 - inner_y1), fill=0, stroke=1)

    # ── Header ────────────────────────────────────────────────────────────────
    c.setFillColor(C_HEADER_BG)
    c.rect(_pt(inner_x1), _yf(hdr_y2),
           _pt(inner_x2 - inner_x1), _pt(HDR_H), fill=1, stroke=0)

    c.setFillColor(C_HEADER_TEXT)
    c.setFont("Helvetica-Bold", _pt(9))
    c.drawString(_pt(inner_x1 + PAD*2), _yf(inner_y1 + 13), title_str)
    c.setFont("Helvetica", _pt(5.5))
    c.setFillColor(C_HEADER_MUTED)
    c.drawString(_pt(inner_x1 + PAD*2), _yf(inner_y1 + 20), subtitle_str)

    # North arrow (simple)
    n_cx_mm = inner_x2 - 14
    n_cy_mm = inner_y1 + HDR_H / 2
    c.setStrokeColor(C_HEADER_MUTED)
    c.setFillColor(C_HEADER_TEXT)
    c.setLineWidth(_pt(0.4))
    c.circle(_pt(n_cx_mm), _yf(n_cy_mm), _pt(7), fill=0, stroke=1)
    arrow_h = _pt(6)
    ax_pt   = _pt(n_cx_mm)
    ay_pt   = _yf(n_cy_mm)
    c.setFillColor(C_HEADER_TEXT)
    p = c.beginPath()
    p.moveTo(ax_pt, ay_pt + arrow_h * 0.85)
    p.lineTo(ax_pt + _pt(2.5), ay_pt - arrow_h * 0.25)
    p.lineTo(ax_pt, ay_pt - arrow_h * 0.1)
    p.lineTo(ax_pt - _pt(2.5), ay_pt - arrow_h * 0.25)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", _pt(2.5))
    c.setFillColor(C_HEADER_TEXT)
    c.drawCentredString(_pt(n_cx_mm), _yf(n_cy_mm + 7 + 2.5), "N")

    # Header bottom divider
    c.setStrokeColor(C_DIVIDER)
    c.setLineWidth(_pt(0.25))
    c.line(_pt(inner_x1), _yf(hdr_y2), _pt(inner_x2), _yf(hdr_y2))

    # ── Plan viewport ─────────────────────────────────────────────────────────
    c.saveState()
    clip_p = c.beginPath()
    clip_p.rect(_pt(plan_x1), _yf(body_y2), _pt(plan_w), _pt(body_h))
    c.clipPath(clip_p, stroke=0)
    _draw_plan(c, project, plan_ox, plan_oy, S, H_mm)
    c.restoreState()

    # Plan/right divider
    c.setStrokeColor(C_DIVIDER)
    c.setLineWidth(_pt(0.25))
    c.line(_pt(plan_x2), _yf(body_y1), _pt(plan_x2), _yf(body_y2))

    # ── Right panel ───────────────────────────────────────────────────────────
    cy = body_y1 + PAD * 2

    cy = _section_head(c, rp_x1 + PAD, cy, rp_w - PAD*2, "Room Schedule", H_mm)
    cy = _draw_schedule(c, project, rp_x1 + PAD, cy, rp_w - PAD*2, H_mm)
    cy += 5

    c.setStrokeColor(C_DIVIDER)
    c.setLineWidth(_pt(0.25))
    c.line(_pt(rp_x1), _yf(cy), _pt(rp_x2), _yf(cy))
    cy += 3

    cy = _section_head(c, rp_x1 + PAD, cy, rp_w - PAD*2, "Legend", H_mm)
    cy = _draw_legend(c, project, rp_x1 + PAD, cy, rp_w - PAD*2, H_mm)
    cy += 5

    if cy < body_y2 - 20:
        c.setStrokeColor(C_DIVIDER)
        c.setLineWidth(_pt(0.25))
        c.line(_pt(rp_x1), _yf(cy), _pt(rp_x2), _yf(cy))
        cy += 3
        cy = _section_head(c, rp_x1 + PAD, cy, rp_w - PAD*2, "Concept + Notes", H_mm)
        _concept = concept_text or (
            f"A {project.building.style} {project.building.type} design on a "
            f"{site.width}×{site.depth} ft site. "
            f"{len(project.rooms)} rooms across "
            f"{project.building.floors} floor(s)."
        )
        _draw_notes(c, project, rp_x1 + PAD, cy, rp_w - PAD*2,
                    _concept, H_mm, body_y2 - 2)

    # ── Footer ────────────────────────────────────────────────────────────────
    c.setFillColor(C_FOOTER_BG)
    c.rect(_pt(inner_x1), _yf(inner_y2),
           _pt(inner_x2 - inner_x1), _pt(FTR_H), fill=1, stroke=0)
    c.setStrokeColor(C_FOOTER_BDR)
    c.setLineWidth(_pt(0.3))
    c.line(_pt(inner_x1), _yf(ftr_y1), _pt(inner_x2), _yf(ftr_y1))

    ftr_cells = [
        ("PROJECT", title_str[:30]),
        ("DATE", stamp),
        ("SCALE", "NTS"),
        ("UNITS", unit_lbl),
        ("SHEET", "1 of 1"),
    ]
    cell_w = (inner_x2 - inner_x1) / len(ftr_cells)
    for i, (lbl, val) in enumerate(ftr_cells):
        cx_mm = inner_x1 + cell_w * i + PAD * 2
        if i > 0:
            c.setStrokeColor(C_FOOTER_BDR)
            c.setLineWidth(_pt(0.25))
            c.line(_pt(inner_x1 + cell_w*i), _yf(ftr_y1),
                   _pt(inner_x1 + cell_w*i), _yf(inner_y2))
        c.setFont("Helvetica-Bold", _pt(2.2))
        c.setFillColor(C_MUTED)
        c.drawString(_pt(cx_mm), _yf(ftr_y1 + 4), lbl)
        c.setFont("Helvetica", _pt(3.2))
        c.setFillColor(C_FOOTER_TEXT)
        c.drawString(_pt(cx_mm), _yf(ftr_y1 + 9), val)

    c.showPage()
    c.save()

    data = buf.getvalue()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return data
