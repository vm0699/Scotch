"""Detail Drawing SVG exporter (Phase 30.7).

Renders a DetailDrawing to an SVG. Each primitive type maps to an SVG element.
Scale: 40 px per foot for detail drawings (larger than floor plan's 12px/ft).

Layers emitted as <g id="..."> groups:
  outline    — room/object outlines (black)
  fixture    — fixture and appliance boxes (dark blue)
  appliance  — appliances (steel blue)
  annotation — labels, advisory lines (grey)
  dim        — dimension lines and labels (blue)
  hatch      — hatch fills (light grey)
"""

from __future__ import annotations

import math
from pathlib import Path

from app.core.models.project import (
    ArcPrimitive,
    DetailDrawing,
    DimPrimitive,
    HatchPrimitive,
    LinePrimitive,
    TextPrimitive,
)

PX_PER_FT = 40
MARGIN = 48  # px

_LAYER_COLORS: dict[str, str] = {
    "outline": "#1a1a1a",
    "fixture": "#1a3a6b",
    "appliance": "#4472c4",
    "annotation": "#555555",
    "dim": "#2563eb",
    "hatch": "#d0d0d0",
}

_LAYER_WIDTHS: dict[str, float] = {
    "outline": 2.0,
    "fixture": 1.5,
    "appliance": 1.2,
    "annotation": 0.8,
    "dim": 0.8,
    "hatch": 0.5,
}


def _px(v: float) -> float:
    return round(v * PX_PER_FT, 2)


def _y_flip(y: float, canvas_h: float) -> float:
    """Flip y so that y=0 (plan origin) is at the bottom of the SVG."""
    return round((canvas_h - y) * PX_PER_FT, 2)


def _color(layer: str) -> str:
    return _LAYER_COLORS.get(layer, "#333333")


def _width(layer: str, weight: float = 1.0) -> float:
    base = _LAYER_WIDTHS.get(layer, 1.0)
    return round(base * weight, 2)


def _line_svg(p: LinePrimitive, canvas_h: float) -> str:
    x1, y1 = _px(p.p1[0]) + MARGIN, _y_flip(p.p1[1], canvas_h) + MARGIN
    x2, y2 = _px(p.p2[0]) + MARGIN, _y_flip(p.p2[1], canvas_h) + MARGIN
    dash = 'stroke-dasharray="6,4"' if p.style == "dashed" else (
        'stroke-dasharray="2,3"' if p.style == "dotted" else ""
    )
    color = _color(p.layer)
    w = _width(p.layer, p.weight)
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" {dash}/>'


def _arc_svg(p: ArcPrimitive, canvas_h: float) -> str:
    cx = _px(p.center[0]) + MARGIN
    cy = _y_flip(p.center[1], canvas_h) + MARGIN
    r = _px(p.radius)
    # Convert angles: SVG angles are from x-axis clockwise; plan angles counter-clockwise
    start = math.radians(p.start_angle)
    end = math.radians(p.end_angle)
    if abs(p.end_angle - p.start_angle) >= 360:
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{_color(p.layer)}" stroke-width="1" fill="none"/>'
    sx = round(cx + r * math.cos(start), 2)
    sy = round(cy - r * math.sin(start), 2)  # y-flip in SVG
    ex = round(cx + r * math.cos(end), 2)
    ey = round(cy - r * math.sin(end), 2)
    large = 1 if (p.end_angle - p.start_angle) > 180 else 0
    return (
        f'<path d="M {sx} {sy} A {r} {r} 0 {large} 0 {ex} {ey}" '
        f'stroke="{_color(p.layer)}" stroke-width="1" fill="none"/>'
    )


def _text_svg(p: TextPrimitive, canvas_h: float) -> str:
    x = _px(p.pos[0]) + MARGIN
    y = _y_flip(p.pos[1], canvas_h) + MARGIN
    size = max(8, round(_px(p.height)))
    anchor_map = {"left": "start", "center": "middle", "right": "end"}
    anchor = anchor_map.get(p.anchor, "middle")
    color = _color(p.layer)
    safe_text = p.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" '
        f'font-size="{size}" fill="{color}" text-anchor="{anchor}">{safe_text}</text>'
    )


def _dim_svg(p: DimPrimitive, canvas_h: float) -> str:
    x1 = _px(p.p1[0]) + MARGIN
    y1 = _y_flip(p.p1[1], canvas_h) + MARGIN
    x2 = _px(p.p2[0]) + MARGIN
    y2 = _y_flip(p.p2[1], canvas_h) + MARGIN
    color = _color("dim")
    mid_x = round((x1 + x2) / 2, 2)
    mid_y = round((y1 + y2) / 2 - 6, 2)
    safe_label = p.label.replace("&", "&amp;")
    tick = 6
    # Perpendicular tick direction
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 0.01:
        return ""
    nx, ny = -dy / length * tick, dx / length * tick
    lines = (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="0.8"/>'
        f'<line x1="{x1+nx}" y1="{y1+ny}" x2="{x1-nx}" y2="{y1-ny}" stroke="{color}" stroke-width="0.8"/>'
        f'<line x1="{x2+nx}" y1="{y2+ny}" x2="{x2-nx}" y2="{y2-ny}" stroke="{color}" stroke-width="0.8"/>'
        f'<text x="{mid_x}" y="{mid_y}" font-family="Inter,Arial,sans-serif" font-size="10" '
        f'fill="{color}" text-anchor="middle">{safe_label}</text>'
    )
    return lines


def _hatch_svg(p: HatchPrimitive, canvas_h: float) -> str:
    pts = " ".join(f"{_px(c[0]) + MARGIN},{_y_flip(c[1], canvas_h) + MARGIN}" for c in p.boundary)
    # Simple fill — full hatch pattern rendering is complex; use light grey with opacity
    return f'<polygon points="{pts}" fill="#e8e8e8" stroke="#888" stroke-width="0.5" opacity="0.6"/>'


def export_detail_svg(drawing: DetailDrawing) -> bytes:
    """Render a DetailDrawing to SVG bytes."""
    cw = drawing.canvas_width
    ch = drawing.canvas_height

    svg_w = round(_px(cw) + MARGIN * 2)
    svg_h = round(_px(ch) + MARGIN * 2)

    # Group elements by layer
    layer_elems: dict[str, list[str]] = {}

    for prim in drawing.primitives:
        if isinstance(prim, LinePrimitive):
            layer_elems.setdefault(prim.layer, []).append(_line_svg(prim, ch))
        elif isinstance(prim, ArcPrimitive):
            layer_elems.setdefault(prim.layer, []).append(_arc_svg(prim, ch))
        elif isinstance(prim, TextPrimitive):
            layer_elems.setdefault(prim.layer, []).append(_text_svg(prim, ch))
        elif isinstance(prim, DimPrimitive):
            layer_elems.setdefault("dim", []).append(_dim_svg(prim, ch))
        elif isinstance(prim, HatchPrimitive):
            layer_elems.setdefault("hatch", []).append(_hatch_svg(prim, ch))

    # Title block
    safe_name = drawing.name.replace("&", "&amp;").replace("<", "&lt;")
    title_block = (
        f'<text x="{svg_w // 2}" y="20" font-family="Inter,Arial,sans-serif" '
        f'font-size="13" font-weight="bold" fill="#111" text-anchor="middle">{safe_name}</text>'
        f'<text x="{svg_w // 2}" y="34" font-family="Inter,Arial,sans-serif" '
        f'font-size="9" fill="#666" text-anchor="middle">'
        f'Scale {drawing.scale} — {drawing.view.capitalize()} — Advisory: verify on site</text>'
    )

    # Advisory watermark if needs_review
    watermark = ""
    if drawing.needs_review:
        watermark = (
            f'<text x="{svg_w - 8}" y="{svg_h - 8}" font-family="Inter,Arial,sans-serif" '
            f'font-size="8" fill="#ef4444" text-anchor="end" opacity="0.7">FOR REVIEW — NOT CONSTRUCTION DRAWINGS</text>'
        )

    layer_order = ["hatch", "outline", "fixture", "appliance", "annotation", "dim"]
    layer_groups = ""
    for layer_id in layer_order:
        elems = layer_elems.get(layer_id, [])
        if elems:
            layer_groups += f'\n  <g id="{layer_id}">\n    ' + "\n    ".join(elems) + "\n  </g>"

    # Remaining unknown layers
    for lid, elems in layer_elems.items():
        if lid not in layer_order and elems:
            layer_groups += f'\n  <g id="{lid}">\n    ' + "\n    ".join(elems) + "\n  </g>"

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">'
        f'\n  <rect width="{svg_w}" height="{svg_h}" fill="white"/>'
        f'\n  <g id="title-block">{title_block}</g>'
        f'{layer_groups}'
        f'\n  <g id="watermark">{watermark}</g>'
        f'\n</svg>'
    )
    return svg.encode("utf-8")


def export_detail_svg_to_file(drawing: DetailDrawing, output_path: Path) -> bytes:
    """Write detail SVG to file and return bytes."""
    data = export_detail_svg(drawing)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return data
