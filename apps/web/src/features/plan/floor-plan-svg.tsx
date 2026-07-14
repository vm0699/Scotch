"use client";

import { useRef, useState } from "react";

import type {
  ArchitectureProject,
  Door,
  FurnitureItem,
  MEPSystem,
  Room,
  ServicePoint,
  WallSide,
  WindowOpening,
} from "@/features/project/types";
import { roomArea } from "@/features/project/types";

/**
 * Architectural 2D floor plan renderer. Pure SVG from an ArchitectureProject:
 * site boundary, poché walls, door swings, window symbols, room labels with
 * sizes/areas, site dimension lines, and a north arrow.
 *
 * Plan space: x across site width, y along site depth, y = 0 at the entrance
 * edge (drawn at the top). All coordinates are in project units (feet),
 * scaled by SCALE into px.
 */

export const SCALE = 12; // px per ft
const WALL_T = 0.5; // wall thickness in ft
const MARGIN = 64; // px around the site for dimensions + north arrow
const DRAG_SNAP_FT = 0.25; // Stage 43.17 — grid snap while dragging furniture

/** Screen client coords -> plan-space feet, via the SVG's own CTM (accounts
 *  for CSS zoom/scale automatically) minus the constant MARGIN offset of the
 *  root <g transform="translate(MARGIN MARGIN)">. */
function clientToFeet(svg: SVGSVGElement, clientX: number, clientY: number): { x: number; y: number } {
  const ctm = svg.getScreenCTM();
  if (!ctm) return { x: 0, y: 0 };
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const local = pt.matrixTransform(ctm.inverse());
  return { x: (local.x - MARGIN) / SCALE, y: (local.y - MARGIN) / SCALE };
}

function snapFt(v: number): number {
  return Math.round(v / DRAG_SNAP_FT) * DRAG_SNAP_FT;
}

export function planPixelSize(project: ArchitectureProject): {
  width: number;
  height: number;
} {
  return {
    width: project.site.width * SCALE + MARGIN * 2,
    height: project.site.depth * SCALE + MARGIN * 2,
  };
}

/** Start corner, along-wall axis and into-room normal for a room wall. */
function wallFrame(room: Room, wall: WallSide) {
  switch (wall) {
    case "north":
      return { sx: room.x, sy: room.y, ax: 1, ay: 0, nx: 0, ny: 1 };
    case "south":
      return { sx: room.x, sy: room.y + room.depth, ax: 1, ay: 0, nx: 0, ny: -1 };
    case "west":
      return { sx: room.x, sy: room.y, ax: 0, ay: 1, nx: 1, ny: 0 };
    case "east":
      return { sx: room.x + room.width, sy: room.y, ax: 0, ay: 1, nx: -1, ny: 0 };
  }
}

function DoorSymbol({ door, room }: { door: Door; room: Room }) {
  const f = wallFrame(room, door.wall);
  const w = door.width;
  // Hinge at the offset start of the opening.
  const hx = (f.sx + f.ax * door.offset) * SCALE;
  const hy = (f.sy + f.ay * door.offset) * SCALE;
  const jx = hx + f.ax * w * SCALE; // far jamb
  const jy = hy + f.ay * w * SCALE;
  const lx = hx + f.nx * w * SCALE; // leaf end (door open into the room)
  const ly = hy + f.ny * w * SCALE;
  const gap = WALL_T * SCALE + 1;
  // Sweep direction so the arc bows from leaf end to far jamb.
  const sweep = f.nx * f.ay - f.ny * f.ax > 0 ? 0 : 1;

  return (
    <g>
      <line
        x1={hx}
        y1={hy}
        x2={jx}
        y2={jy}
        className="stroke-card"
        strokeWidth={gap}
      />
      <line
        x1={hx}
        y1={hy}
        x2={lx}
        y2={ly}
        className="stroke-foreground"
        strokeWidth={1.2}
      />
      <path
        d={`M ${lx} ${ly} A ${w * SCALE} ${w * SCALE} 0 0 ${sweep} ${jx} ${jy}`}
        fill="none"
        className="stroke-muted-foreground"
        strokeWidth={0.8}
        strokeDasharray="2.5 2.5"
      />
    </g>
  );
}

function WindowSymbol({
  window: win,
  room,
}: {
  window: WindowOpening;
  room: Room;
}) {
  const f = wallFrame(room, win.wall);
  const sx = (f.sx + f.ax * win.offset) * SCALE;
  const sy = (f.sy + f.ay * win.offset) * SCALE;
  const ex = sx + f.ax * win.width * SCALE;
  const ey = sy + f.ay * win.width * SCALE;
  const half = (WALL_T / 2) * SCALE;
  const gap = WALL_T * SCALE + 1;

  return (
    <g>
      <line
        x1={sx}
        y1={sy}
        x2={ex}
        y2={ey}
        className="stroke-card"
        strokeWidth={gap}
      />
      {/* sill, glazing and outer lines */}
      {[-half, 0, half].map((d, i) => (
        <line
          key={i}
          x1={sx + f.nx * d}
          y1={sy + f.ny * d}
          x2={ex + f.nx * d}
          y2={ey + f.ny * d}
          className="stroke-foreground"
          strokeWidth={i === 1 ? 1 : 0.7}
        />
      ))}
    </g>
  );
}

function RoomShape({
  room,
  selected,
  interactive,
}: {
  room: Room;
  selected: boolean;
  interactive: boolean;
}) {
  return (
    <g>
      <rect
        data-room-id={room.id}
        x={room.x * SCALE}
        y={room.y * SCALE}
        width={room.width * SCALE}
        height={room.depth * SCALE}
        className={
          (selected ? "fill-sky-50 " : "fill-card ") +
          "stroke-foreground transition-colors" +
          (interactive ? " cursor-pointer hover:fill-muted/70" : "")
        }
        strokeWidth={WALL_T * SCALE}
      />
      {selected && (
        <rect
          x={room.x * SCALE + 2}
          y={room.y * SCALE + 2}
          width={room.width * SCALE - 4}
          height={room.depth * SCALE - 4}
          className="pointer-events-none fill-none stroke-sky-500"
          strokeWidth={1.5}
        />
      )}
    </g>
  );
}

function RoomLabel({ room, unit }: { room: Room; unit: string }) {
  const cx = (room.x + room.width / 2) * SCALE;
  const cy = (room.y + room.depth / 2) * SCALE;
  const compact = Math.min(room.width, room.depth) < 6;
  const showArea = roomArea(room) >= 60 && !compact;

  return (
    <text
      x={cx}
      y={cy}
      textAnchor="middle"
      className="select-none fill-foreground"
      style={{ fontSize: compact ? 8.5 : 11 }}
    >
      <tspan x={cx} dy={showArea ? "-0.7em" : "-0.1em"} fontWeight={500}>
        {room.name}
      </tspan>
      <tspan
        x={cx}
        dy="1.25em"
        className="fill-muted-foreground"
        style={{ fontSize: compact ? 7.5 : 9 }}
      >
        {room.width}′ × {room.depth}′
      </tspan>
      {showArea && (
        <tspan
          x={cx}
          dy="1.25em"
          className="fill-muted-foreground"
          style={{ fontSize: 9 }}
        >
          {roomArea(room)} {unit}²
        </tspan>
      )}
    </text>
  );
}

/** Dimension line with architectural slash ticks. */
function DimensionLine({
  x1,
  y1,
  x2,
  y2,
  label,
  vertical = false,
}: {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  label: string;
  vertical?: boolean;
}) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const tick = 4;

  return (
    <g className="stroke-muted-foreground" strokeWidth={0.8}>
      <line x1={x1} y1={y1} x2={x2} y2={y2} />
      {[{ x: x1, y: y1 }, { x: x2, y: y2 }].map((p, i) => (
        <line
          key={i}
          x1={p.x - tick}
          y1={p.y + tick}
          x2={p.x + tick}
          y2={p.y - tick}
          strokeWidth={1}
        />
      ))}
      <text
        x={mx}
        y={my}
        dy={vertical ? "-0.5em" : "-0.55em"}
        textAnchor="middle"
        className="fill-muted-foreground"
        stroke="none"
        style={{ fontSize: 9.5 }}
        transform={vertical ? `rotate(-90 ${mx} ${my})` : undefined}
      >
        {label}
      </text>
    </g>
  );
}

function NorthArrow({
  cx,
  cy,
  topDirection,
}: {
  cx: number;
  cy: number;
  topDirection: string;
}) {
  const rotation =
    { north: 0, east: -90, west: 90, south: 180 }[topDirection] ?? 0;
  return (
    <g transform={`translate(${cx} ${cy})`}>
      <circle
        r={15}
        className="fill-card stroke-muted-foreground"
        strokeWidth={0.8}
      />
      <g transform={`rotate(${rotation})`}>
        <path d="M 0 -10 L 4 6 L 0 3.5 L -4 6 Z" className="fill-foreground" />
      </g>
      <text
        y={28}
        textAnchor="middle"
        className="fill-muted-foreground"
        style={{ fontSize: 8.5, letterSpacing: "0.08em" }}
      >
        N
      </text>
    </g>
  );
}

// ── Furniture symbols ─────────────────────────────────────────────────────────

/**
 * Renders one architectural plan symbol for a FurnitureItem.
 * All coordinates are in pixels; the outer <g> handles plan-to-px translation
 * and symbol rotation around the item centroid.
 *
 * Symbol coordinate system: (0,0) = top-left of item bounding box.
 * w / h are item width / depth in pixels.
 */
function FurnitureSymbol({
  item,
  selected,
  onSelect,
  draggable,
  onMove,
}: {
  item: FurnitureItem;
  selected?: boolean;
  onSelect?: (id: string) => void;
  /** Stage 43.17 — freehand drag-with-snap. Self-contained: this component
   *  owns its own live drag position and only reports the FINAL x/y once,
   *  on release — the parent doesn't need to know a drag is in progress. */
  draggable?: boolean;
  onMove?: (id: string, x: number, y: number) => void;
}) {
  const [dragPos, setDragPos] = useState<{ x: number; y: number } | null>(null);
  const dragRef = useRef<{ grabDX: number; grabDY: number; moved: boolean; lastX: number; lastY: number } | null>(null);

  const ix = dragPos?.x ?? item.x;
  const iy = dragPos?.y ?? item.y;
  const px = ix * SCALE;
  const py = iy * SCALE;
  const pw = item.width * SCALE;
  const ph = item.depth * SCALE;
  const cx = px + pw / 2;
  const cy = py + ph / 2;

  const baseClass =
    "fill-none stroke-muted-foreground/70";
  const fillClass = "fill-muted/30 stroke-muted-foreground/70";
  const sw = 0.7; // default stroke-width

  const type = item.type;

  function symbol() {
    // ── Beds ──────────────────────────────────────────────────────────────
    if (type === "double_bed" || type === "king_bed" || type === "single_bed") {
      const headH = ph * 0.14;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} rx={2} className={fillClass} strokeWidth={sw} />
          {/* headboard */}
          <rect x={px} y={py} width={pw} height={headH} rx={1} className="fill-muted-foreground/20 stroke-muted-foreground/70" strokeWidth={sw} />
          {/* pillows */}
          {[0.22, 0.62].map((t) => (
            <ellipse key={t} cx={px + pw * t} cy={py + headH + ph * 0.12} rx={pw * 0.14} ry={ph * 0.07}
              className="fill-card stroke-muted-foreground/50" strokeWidth={0.6} />
          ))}
        </g>
      );
    }

    // ── Wardrobe ──────────────────────────────────────────────────────────
    if (type === "wardrobe" || type === "wardrobe_2") {
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          {/* cross hatching — two X lines for double-door wardrobe */}
          <line x1={px} y1={py} x2={px + pw / 2} y2={py + ph} className={baseClass} strokeWidth={sw} />
          <line x1={px + pw / 2} y1={py} x2={px} y2={py + ph} className={baseClass} strokeWidth={sw} />
          <line x1={px + pw / 2} y1={py} x2={px + pw} y2={py + ph} className={baseClass} strokeWidth={sw} />
          <line x1={px + pw} y1={py} x2={px + pw / 2} y2={py + ph} className={baseClass} strokeWidth={sw} />
          {/* centre divider */}
          <line x1={px + pw / 2} y1={py} x2={px + pw / 2} y2={py + ph} className={baseClass} strokeWidth={sw} />
        </g>
      );
    }

    // ── Dresser / dressing table ───────────────────────────────────────────
    if (type === "dresser" || type === "dressing_table") {
      const drawH = ph * 0.3;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          {[0, 1, 2].map((i) => (
            <rect key={i} x={px + 3} y={py + drawH * i + 3} width={pw - 6} height={drawH - 3}
              rx={1} className={baseClass} strokeWidth={0.5} />
          ))}
        </g>
      );
    }

    // ── Sofa ──────────────────────────────────────────────────────────────
    if (type === "sofa") {
      const backH = ph * 0.28;
      const armW = pw * 0.1;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} rx={3} className={fillClass} strokeWidth={sw} />
          {/* back */}
          <rect x={px} y={py} width={pw} height={backH} rx={2} className="fill-muted-foreground/15 stroke-muted-foreground/70" strokeWidth={sw} />
          {/* arms */}
          <rect x={px} y={py + backH} width={armW} height={ph - backH} rx={2} className="fill-muted-foreground/15 stroke-muted-foreground/70" strokeWidth={sw} />
          <rect x={px + pw - armW} y={py + backH} width={armW} height={ph - backH} rx={2} className="fill-muted-foreground/15 stroke-muted-foreground/70" strokeWidth={sw} />
          {/* seat cushion dividers */}
          <line x1={px + pw / 3} y1={py + backH + 2} x2={px + pw / 3} y2={py + ph - 2} className={baseClass} strokeWidth={0.6} />
          <line x1={px + 2 * pw / 3} y1={py + backH + 2} x2={px + 2 * pw / 3} y2={py + ph - 2} className={baseClass} strokeWidth={0.6} />
        </g>
      );
    }

    // ── Armchair ──────────────────────────────────────────────────────────
    if (type === "armchair_l" || type === "armchair_r" || type === "armchair") {
      const backH = ph * 0.28;
      const armW = pw * 0.14;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} rx={3} className={fillClass} strokeWidth={sw} />
          <rect x={px} y={py} width={pw} height={backH} rx={2} className="fill-muted-foreground/15 stroke-muted-foreground/70" strokeWidth={sw} />
          <rect x={px} y={py + backH} width={armW} height={ph - backH} rx={2} className="fill-muted-foreground/15 stroke-muted-foreground/70" strokeWidth={sw} />
          <rect x={px + pw - armW} y={py + backH} width={armW} height={ph - backH} rx={2} className="fill-muted-foreground/15 stroke-muted-foreground/70" strokeWidth={sw} />
        </g>
      );
    }

    // ── Coffee table ──────────────────────────────────────────────────────
    if (type === "coffee_table") {
      return (
        <g>
          <rect x={px + 2} y={py + 2} width={pw - 4} height={ph - 4} className={fillClass} strokeWidth={sw} />
        </g>
      );
    }

    // ── Side table ────────────────────────────────────────────────────────
    if (type === "side_table") {
      return <rect x={px + 1} y={py + 1} width={pw - 2} height={ph - 2} className={fillClass} strokeWidth={sw} />;
    }

    // ── TV unit ───────────────────────────────────────────────────────────
    if (type === "tv_unit") {
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          {/* screen suggestion */}
          <rect x={px + pw * 0.15} y={py + ph * 0.15} width={pw * 0.7} height={ph * 0.55}
            className={baseClass} strokeWidth={0.6} strokeDasharray="2 1.5" />
        </g>
      );
    }

    // ── Dining table (also office/café meeting tables — same shape) ────────
    if (type === "dining_table" || type === "meeting_table") {
      return (
        <rect x={px} y={py} width={pw} height={ph} rx={4} className={fillClass} strokeWidth={sw} />
      );
    }

    // ── Dining chairs (generic) ───────────────────────────────────────────
    if (type.startsWith("chair_") || type.startsWith("outdoor_chair")) {
      const backH = ph * 0.3;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} rx={2} className={fillClass} strokeWidth={sw} />
          <rect x={px} y={py} width={pw} height={backH} rx={1} className="fill-muted-foreground/20 stroke-muted-foreground/60" strokeWidth={0.6} />
        </g>
      );
    }

    // ── Sideboard ─────────────────────────────────────────────────────────
    if (type === "sideboard") {
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          <line x1={cx} y1={py} x2={cx} y2={py + ph} className={baseClass} strokeWidth={0.5} />
        </g>
      );
    }

    // ── Desk ──────────────────────────────────────────────────────────────
    if (type.startsWith("desk")) {
      const returnW = pw * 0.35;
      const returnH = ph * 0.45;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph * 0.55} className={fillClass} strokeWidth={sw} />
          <rect x={px} y={py + ph * 0.55 - returnH} width={returnW} height={returnH} className={fillClass} strokeWidth={sw} />
        </g>
      );
    }

    // ── Office chair ──────────────────────────────────────────────────────
    if (type === "office_chair") {
      return (
        <g>
          <circle cx={cx} cy={cy} r={Math.min(pw, ph) / 2 - 1} className={fillClass} strokeWidth={sw} />
          {/* back arc */}
          <path d={`M ${px + 2} ${py + ph * 0.4} A ${pw / 2} ${ph / 2} 0 0 1 ${px + pw - 2} ${py + ph * 0.4}`}
            className={baseClass} strokeWidth={sw} />
        </g>
      );
    }

    // ── Potted plant ──────────────────────────────────────────────────────
    if (type === "plant") {
      const r = Math.min(pw, ph) / 2;
      return (
        <g>
          <circle cx={cx} cy={cy} r={r * 0.9} className="fill-none stroke-muted-foreground/70" strokeWidth={sw} strokeDasharray="1.2 1" />
          <circle cx={cx} cy={cy} r={r * 0.35} className={fillClass} strokeWidth={sw} />
        </g>
      );
    }

    // ── Ottoman ───────────────────────────────────────────────────────────
    if (type === "ottoman") {
      return <rect x={px} y={py} width={pw} height={ph} rx={pw * 0.15} className={fillClass} strokeWidth={sw} />;
    }

    // ── Bookshelf ─────────────────────────────────────────────────────────
    if (type.startsWith("bookshelf")) {
      const shelves = 4;
      const sh = ph / shelves;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          {Array.from({ length: shelves - 1 }).map((_, i) => (
            <line key={i} x1={px + 1} y1={py + sh * (i + 1)} x2={px + pw - 1} y2={py + sh * (i + 1)}
              className={baseClass} strokeWidth={0.5} />
          ))}
        </g>
      );
    }

    // ── WC ────────────────────────────────────────────────────────────────
    if (type === "wc") {
      const tankH = ph * 0.28;
      const bowlH = ph - tankH;
      return (
        <g>
          {/* tank */}
          <rect x={px} y={py} width={pw} height={tankH} rx={1} className={fillClass} strokeWidth={sw} />
          {/* bowl — D shape */}
          <path d={`M ${px} ${py + tankH} L ${px} ${py + ph - 2} Q ${px + pw / 2} ${py + ph + 4} ${px + pw} ${py + ph - 2} L ${px + pw} ${py + tankH} Z`}
            className={fillClass} strokeWidth={sw} />
          {/* bowl opening */}
          <ellipse cx={cx} cy={py + tankH + bowlH * 0.55} rx={pw * 0.38} ry={bowlH * 0.38}
            className="fill-card stroke-muted-foreground/60" strokeWidth={0.6} />
        </g>
      );
    }

    // ── Basin ─────────────────────────────────────────────────────────────
    if (type === "basin") {
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} rx={3} className={fillClass} strokeWidth={sw} />
          <ellipse cx={cx} cy={cy + ph * 0.05} rx={pw * 0.38} ry={ph * 0.36}
            className="fill-card stroke-muted-foreground/60" strokeWidth={0.6} />
          {/* tap dot */}
          <circle cx={cx} cy={py + ph * 0.15} r={1.5} className="fill-muted-foreground/60" />
        </g>
      );
    }

    // ── Kitchen sink ──────────────────────────────────────────────────────
    if (type === "sink") {
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} rx={1} className={fillClass} strokeWidth={sw} />
          <rect x={px + pw * 0.15} y={py + ph * 0.2} width={pw * 0.7} height={ph * 0.6} rx={2}
            className="fill-card stroke-muted-foreground/60" strokeWidth={0.6} />
          <circle cx={cx} cy={py + ph * 0.15} r={1.2} className="fill-muted-foreground/60" />
        </g>
      );
    }

    // ── Shower ────────────────────────────────────────────────────────────
    if (type === "shower") {
      const g2 = 6;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          {/* corner lines — shower tray indicator */}
          <line x1={px} y1={py + g2} x2={px + g2} y2={py} className={baseClass} strokeWidth={0.6} />
          <line x1={px + pw} y1={py + g2} x2={px + pw - g2} y2={py} className={baseClass} strokeWidth={0.6} />
          <line x1={px} y1={py + ph - g2} x2={px + g2} y2={py + ph} className={baseClass} strokeWidth={0.6} />
          <line x1={px + pw} y1={py + ph - g2} x2={px + pw - g2} y2={py + ph} className={baseClass} strokeWidth={0.6} />
          {/* head */}
          <circle cx={cx} cy={cy} r={Math.min(pw, ph) * 0.18}
            className="fill-muted-foreground/20 stroke-muted-foreground/60" strokeWidth={0.6} />
        </g>
      );
    }

    // ── Bathtub ───────────────────────────────────────────────────────────
    if (type === "bathtub") {
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} rx={pw * 0.12} className={fillClass} strokeWidth={sw} />
          <ellipse cx={cx} cy={cy + ph * 0.1} rx={pw * 0.38} ry={ph * 0.38}
            className="fill-card stroke-muted-foreground/50" strokeWidth={0.6} />
          {/* tap end */}
          <rect x={px + pw * 0.3} y={py + 3} width={pw * 0.4} height={6} rx={2}
            className="fill-muted-foreground/25 stroke-muted-foreground/60" strokeWidth={0.5} />
        </g>
      );
    }

    // ── Refrigerator ──────────────────────────────────────────────────────
    if (type === "refrigerator") {
      const divY = py + ph * 0.35;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} rx={2} className={fillClass} strokeWidth={sw} />
          <line x1={px + 2} y1={divY} x2={px + pw - 2} y2={divY} className={baseClass} strokeWidth={0.6} />
          {/* handles */}
          <line x1={px + pw * 0.2} y1={py + ph * 0.12} x2={px + pw * 0.2} y2={py + ph * 0.28}
            className={baseClass} strokeWidth={1.2} />
          <line x1={px + pw * 0.2} y1={divY + ph * 0.1} x2={px + pw * 0.2} y2={divY + ph * 0.25}
            className={baseClass} strokeWidth={1.2} />
        </g>
      );
    }

    // ── Counter (kitchen) ─────────────────────────────────────────────────
    if (type.startsWith("counter")) {
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          {/* front edge shadow */}
          <rect x={px} y={py + ph - 3} width={pw} height={3} className="fill-muted-foreground/20" />
        </g>
      );
    }

    // ── Cooktop ───────────────────────────────────────────────────────────
    if (type === "cooktop") {
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          {[[0.28, 0.3], [0.72, 0.3], [0.28, 0.7], [0.72, 0.7]].map(([tx, ty], i) => (
            <circle key={i} cx={px + pw * tx} cy={py + ph * ty} r={Math.min(pw, ph) * 0.14}
              className={baseClass} strokeWidth={0.6} />
          ))}
        </g>
      );
    }

    // ── Shelving / storage ────────────────────────────────────────────────
    if (type.startsWith("shelving") || type === "shoe_rack") {
      const cols = Math.max(1, Math.floor(pw / 14));
      const colW = pw / cols;
      return (
        <g>
          <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />
          {Array.from({ length: cols - 1 }).map((_, i) => (
            <line key={i} x1={px + colW * (i + 1)} y1={py + 1} x2={px + colW * (i + 1)} y2={py + ph - 1}
              className={baseClass} strokeWidth={0.5} />
          ))}
        </g>
      );
    }

    // ── Console / outdoor table ───────────────────────────────────────────
    if (type === "console_table" || type === "outdoor_table") {
      return <rect x={px} y={py} width={pw} height={ph} rx={2} className={fillClass} strokeWidth={sw} />;
    }

    // ── Generic fallback ──────────────────────────────────────────────────
    return <rect x={px} y={py} width={pw} height={ph} className={fillClass} strokeWidth={sw} />;
  }

  const handlePointerDown = (e: React.PointerEvent<SVGGElement>) => {
    if (!draggable) return;
    e.stopPropagation();
    const svg = e.currentTarget.ownerSVGElement;
    if (!svg) return;
    const cursor = clientToFeet(svg, e.clientX, e.clientY);
    dragRef.current = { grabDX: item.x - cursor.x, grabDY: item.y - cursor.y, moved: false, lastX: item.x, lastY: item.y };
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      // Pointer capture can fail for non-standard pointer sessions (e.g. some
      // automated/synthetic input) — drag still works via bubbled move/up.
    }
  };

  const handlePointerMove = (e: React.PointerEvent<SVGGElement>) => {
    if (!dragRef.current) return;
    const svg = e.currentTarget.ownerSVGElement;
    if (!svg) return;
    const cursor = clientToFeet(svg, e.clientX, e.clientY);
    const rawX = cursor.x + dragRef.current.grabDX;
    const rawY = cursor.y + dragRef.current.grabDY;
    if (!dragRef.current.moved && Math.hypot(rawX - item.x, rawY - item.y) > 0.05) {
      dragRef.current.moved = true;
    }
    if (dragRef.current.moved) {
      const snapped = { x: Math.max(0, snapFt(rawX)), y: Math.max(0, snapFt(rawY)) };
      dragRef.current.lastX = snapped.x;
      dragRef.current.lastY = snapped.y;
      setDragPos(snapped);
    }
  };

  const handlePointerUp = (e: React.PointerEvent<SVGGElement>) => {
    if (!dragRef.current) return;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // no-op — see handlePointerDown
    }
    const { moved, lastX, lastY } = dragRef.current;
    dragRef.current = null;
    setDragPos(null);
    if (moved && onMove) {
      onMove(item.id, lastX, lastY);
    } else if (!moved && onSelect) {
      // Plain click (no drag distance) — select, same as the onClick path,
      // but pointerdown already stopped propagation so onClick won't fire.
      onSelect(item.id);
    }
  };

  return (
    <g
      opacity={selected ? 1 : 0.85}
      className={onSelect ? (draggable ? "cursor-move" : "cursor-pointer") : undefined}
      onClick={
        onSelect && !draggable
          ? (e) => {
              e.stopPropagation();
              onSelect(item.id);
            }
          : undefined
      }
      onPointerDown={draggable ? handlePointerDown : undefined}
      onPointerMove={draggable ? handlePointerMove : undefined}
      onPointerUp={draggable ? handlePointerUp : undefined}
    >
      {selected && (
        <rect
          x={px - 2}
          y={py - 2}
          width={pw + 4}
          height={ph + 4}
          rx={2}
          className={dragPos ? "fill-none stroke-emerald-500" : "fill-none stroke-sky-500"}
          strokeWidth={1.5}
          strokeDasharray="3 2"
        />
      )}
      {symbol()}
    </g>
  );
}

function FurnitureLayer({
  project,
  visibleRoomIds,
  show,
  selectedItemId,
  onSelectItem,
  draggable,
  onMoveFurniture,
}: {
  project: ArchitectureProject;
  visibleRoomIds: Set<string>;
  /** Override project.show_furniture for canvas-level toggle. */
  show?: boolean;
  selectedItemId?: string | null;
  onSelectItem?: (id: string) => void;
  /** Stage 43.17 — freehand drag-with-snap. */
  draggable?: boolean;
  onMoveFurniture?: (id: string, x: number, y: number) => void;
}) {
  const shouldShow = show !== undefined ? show : project.show_furniture;
  if (!shouldShow) return null;
  const visible = project.furniture.filter((f) => visibleRoomIds.has(f.room_id));
  if (visible.length === 0) return null;

  return (
    <g>
      {visible.map((item) => (
        <FurnitureSymbol
          key={item.id}
          item={item}
          selected={item.id === selectedItemId}
          onSelect={onSelectItem}
          draggable={draggable}
          onMove={onMoveFurniture}
        />
      ))}
    </g>
  );
}

// ── Room-level dimension layer (Phase 29.0) ───────────────────────────────────

function RoomDimensionLines({ rooms }: { rooms: Room[] }) {
  const dimOff = 10; // px offset from room edge for the dimension tick line
  return (
    <g className="stroke-blue-400/60" strokeWidth={0.6} fontSize={7}>
      {rooms.map((room) => {
        const rx = room.x * SCALE;
        const ry = room.y * SCALE;
        const rw = room.width * SCALE;
        const rd = room.depth * SCALE;
        const wLabel = `${room.width}′`;
        const dLabel = `${room.depth}′`;
        const mx = rx + rw / 2;
        const my = ry + rd / 2;
        return (
          <g key={`rdim-${room.id}`}>
            {/* Width dim above room */}
            <line x1={rx} y1={ry - 6} x2={rx + rw} y2={ry - 6} />
            <line x1={rx} y1={ry - 9} x2={rx} y2={ry - 3} />
            <line x1={rx + rw} y1={ry - 9} x2={rx + rw} y2={ry - 3} />
            <text
              x={mx}
              y={ry - 8}
              textAnchor="middle"
              className="fill-blue-500"
              stroke="none"
              style={{ fontSize: 7 }}
            >
              {wLabel}
            </text>
            {/* Depth dim right of room */}
            <line x1={rx + rw + 6} y1={ry} x2={rx + rw + 6} y2={ry + rd} />
            <line x1={rx + rw + 3} y1={ry} x2={rx + rw + 9} y2={ry} />
            <line x1={rx + rw + 3} y1={ry + rd} x2={rx + rw + 9} y2={ry + rd} />
            <text
              x={rx + rw + dimOff}
              y={my}
              textAnchor="middle"
              className="fill-blue-500"
              stroke="none"
              transform={`rotate(-90 ${rx + rw + dimOff} ${my})`}
              style={{ fontSize: 7 }}
            >
              {dLabel}
            </text>
          </g>
        );
      })}
    </g>
  );
}

// ── MEP overlay layer (Phase 29) ──────────────────────────────────────────────

const MEP_COLORS: Record<MEPSystem, string> = {
  plumbing:   "#1a6eb5",
  electrical: "#d97706",
  lighting:   "#ca8a04",
  ac:         "#0891b2",
};

const MEP_SYMBOLS: Record<string, string> = {
  wc:       "WC",
  sink:     "S",
  basin:    "B",
  shower:   "SH",
  switch:   "SW",
  socket:   "SO",
  ceiling:  "L",
  ac_unit:  "AC",
};

function MepPoint({
  pt,
  selected,
  onSelect,
}: {
  pt: ServicePoint;
  selected: boolean;
  onSelect?: (id: string) => void;
}) {
  const cx = pt.x * SCALE;
  const cy = pt.y * SCALE;
  const color = MEP_COLORS[pt.system] ?? "#888";
  const r = pt.system === "ac" ? 5 : 4;
  const sym = MEP_SYMBOLS[pt.kind] ?? pt.kind.slice(0, 2).toUpperCase();

  return (
    <g
      className="cursor-pointer"
      onClick={() => onSelect?.(pt.id)}
    >
      <circle
        cx={cx}
        cy={cy}
        r={r + (selected ? 2 : 0)}
        fill={color}
        fillOpacity={0.85}
        stroke={selected ? "#fff" : "none"}
        strokeWidth={selected ? 1.5 : 0}
      />
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#fff"
        stroke="none"
        style={{ fontSize: 5, fontWeight: 700, userSelect: "none" }}
      >
        {sym}
      </text>
      {pt.user_override && (
        <circle cx={cx + r - 1} cy={cy - r + 1} r={1.5} fill="#f59e0b" />
      )}
    </g>
  );
}

function MEPLayer({
  project,
  activeLayer,
  selectedPointId,
  onSelectPoint,
  visibleRoomIds,
}: {
  project: ArchitectureProject;
  activeLayer: Set<MEPSystem>;
  selectedPointId?: string | null;
  onSelectPoint?: (id: string) => void;
  visibleRoomIds: Set<string>;
}) {
  if (!project.mep_plan.generated) return null;

  const mep = project.mep_plan;
  const allPoints: ServicePoint[] = [
    ...(activeLayer.has("plumbing") ? mep.plumbing.points : []),
    ...(activeLayer.has("electrical") ? mep.electrical.points : []),
    ...(activeLayer.has("lighting") ? mep.lighting.points : []),
    ...(activeLayer.has("ac") ? mep.ac.points : []),
  ].filter((pt) => visibleRoomIds.has(pt.room_id));

  const routes = [
    ...(activeLayer.has("plumbing") ? mep.plumbing.routes : []),
    ...(activeLayer.has("electrical") ? mep.electrical.routes : []),
  ];

  return (
    <g>
      {/* Advisory routes */}
      {routes.map((rt) => {
        if (rt.polyline.length < 2) return null;
        const color = MEP_COLORS[rt.system] ?? "#888";
        const pts = rt.polyline.map(([x, y]) => `${x * SCALE},${y * SCALE}`).join(" ");
        return (
          <polyline
            key={rt.id}
            points={pts}
            fill="none"
            stroke={color}
            strokeWidth={0.7}
            strokeDasharray="4 2"
            opacity={0.5}
          />
        );
      })}
      {/* Service points */}
      {allPoints.map((pt) => (
        <MepPoint
          key={pt.id}
          pt={pt}
          selected={pt.id === selectedPointId}
          onSelect={onSelectPoint}
        />
      ))}
    </g>
  );
}

export function FloorPlanSvg({
  project,
  style,
  className,
  selectedRoomId = null,
  interactive = false,
  activeLevel = 0,
  showDimensions,
  showFurniturePlan,
  activeMepLayers,
  selectedMepPointId,
  onSelectMepPoint,
  selectedFurnitureId,
  onSelectFurniture,
  onMoveFurniture,
}: {
  project: ArchitectureProject;
  style?: React.CSSProperties;
  className?: string;
  /** Highlighted room (Phase 6 selection). */
  selectedRoomId?: string | null;
  /** Enables pointer affordances on rooms; click handling is delegated to the parent. */
  interactive?: boolean;
  /** Active floor level for multi-floor plans (Phase 22). */
  activeLevel?: number;
  /** Override show_dimensions from project; undefined = use project.show_dimensions. */
  showDimensions?: boolean;
  /** Override furniture visibility; undefined = use project.show_furniture. */
  showFurniturePlan?: boolean;
  /** Which MEP systems to show as overlay (Phase 29). */
  activeMepLayers?: Set<MEPSystem>;
  selectedMepPointId?: string | null;
  onSelectMepPoint?: (id: string) => void;
  /** Selected furniture item (Phase 43 — click-to-select interior editing). */
  selectedFurnitureId?: string | null;
  onSelectFurniture?: (id: string) => void;
  /** Stage 43.17 — freehand drag-with-snap; supplying this enables dragging. */
  onMoveFurniture?: (id: string, x: number, y: number) => void;
}) {
  const { site } = project;
  const { width: vw, height: vh } = planPixelSize(project);
  const sw = site.width * SCALE;
  const sd = site.depth * SCALE;
  const unit = project.units === "feet" ? "ft" : "m";
  const visibleRooms = project.rooms.filter((r) => r.level === activeLevel);
  const visibleRoomIds = new Set(visibleRooms.map((r) => r.id));
  const roomsById = new Map(visibleRooms.map((r) => [r.id, r]));
  const dimOffset = 26;
  const dimsOn = showDimensions ?? project.show_dimensions ?? true;
  const mepLayers = activeMepLayers ?? (project.show_mep ? new Set<MEPSystem>(["plumbing", "electrical", "lighting", "ac"]) : new Set<MEPSystem>());

  return (
    <svg
      viewBox={`0 0 ${vw} ${vh}`}
      style={style}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label={`Floor plan of ${project.name}`}
    >
      <g transform={`translate(${MARGIN} ${MARGIN})`}>
        {/* site */}
        <rect
          x={0}
          y={0}
          width={sw}
          height={sd}
          className="fill-muted/40 stroke-muted-foreground"
          strokeWidth={1}
          strokeDasharray="6 3"
        />

        {/* rooms: fills + walls, then openings, then labels */}
        <g>
          {visibleRooms.map((room) => (
            <RoomShape
              key={room.id}
              room={room}
              selected={room.id === selectedRoomId}
              interactive={interactive}
            />
          ))}
        </g>
        <g>
          {project.doors.filter((d) => visibleRoomIds.has(d.room_id)).map((door) => {
            const room = roomsById.get(door.room_id);
            return room ? (
              <DoorSymbol key={door.id} door={door} room={room} />
            ) : null;
          })}
          {project.windows.filter((w) => visibleRoomIds.has(w.room_id)).map((win) => {
            const room = roomsById.get(win.room_id);
            return room ? (
              <WindowSymbol key={win.id} window={win} room={room} />
            ) : null;
          })}
        </g>
        <FurnitureLayer
          project={project}
          visibleRoomIds={visibleRoomIds}
          show={showFurniturePlan}
          selectedItemId={selectedFurnitureId}
          onSelectItem={onSelectFurniture}
          draggable={!!onMoveFurniture}
          onMoveFurniture={onMoveFurniture}
        />
        {/* MEP overlay (Phase 29) */}
        {mepLayers.size > 0 && (
          <MEPLayer
            project={project}
            activeLayer={mepLayers}
            selectedPointId={selectedMepPointId}
            onSelectPoint={onSelectMepPoint}
            visibleRoomIds={visibleRoomIds}
          />
        )}
        <g>
          {visibleRooms.map((room) => (
            <RoomLabel key={room.id} room={room} unit={unit} />
          ))}
        </g>
        {/* Room-level dimension annotations (Phase 29.0) */}
        {dimsOn && <RoomDimensionLines rooms={visibleRooms} />}

        {/* site dimensions */}
        <DimensionLine
          x1={0}
          y1={sd + dimOffset}
          x2={sw}
          y2={sd + dimOffset}
          label={`${site.width}′-0″`}
        />
        <DimensionLine
          x1={-dimOffset}
          y1={sd}
          x2={-dimOffset}
          y2={0}
          label={`${site.depth}′-0″`}
          vertical
        />

        {/* north arrow, top-right of the site */}
        <NorthArrow cx={sw + 34} cy={4} topDirection={site.orientation} />
      </g>
    </svg>
  );
}
