/**
 * Phase 35 — 3D massing data generator (2D-to-3D production upgrade).
 *
 * Converts an ArchitectureProject into a flat list of MassingBox descriptors
 * that the viewer turns into three.js meshes.
 *
 * Coordinate mapping:
 *   Plan x  → three.js x  (east = +x)
 *   Plan y  → three.js z  (south = +z, y=0 is entrance/north)
 *   Height  → three.js y  (up = +y)
 *
 * Phase 35 additions:
 *   - Per-room floor tile overlays derived from material_plan.room_finishes
 *   - MEP service points mapped to 3D blocks (WC, basin, shower, AC unit)
 *   - Kitchen counter geometry from room footprint
 *   - Stair geometry from project.stairs
 *   - Extended MaterialId palette
 */

import type { ArchitectureProject } from "@/features/project/types";

// ── types ────────────────────────────────────────────────────────────────────

export type MaterialId =
  | "wall"
  | "floor"
  | "roof"
  | "glass"
  | "ground"
  | "furniture"
  // Phase 35 — material-mapped floor tiles
  | "floor_tile_light"
  | "floor_tile_dark"
  | "floor_marble"
  // Phase 35 — architectural elements
  | "counter"
  | "mep_block"
  | "stair";

export interface MassingBox {
  id: string;
  /** Descriptive name for GLTF node naming — follows Scotch/Category/Room convention. */
  name: string;
  /** World-space centre in three.js coords: [x, y_up, z]. */
  pos: [number, number, number];
  /** Full extents: [width_x, height_y, depth_z]. */
  size: [number, number, number];
  mat: MaterialId;
}

export interface MassingData {
  boxes: MassingBox[];
  /** Site centre in the XZ plane — use as OrbitControls target. */
  centerX: number;
  centerZ: number;
  /** Largest dimension of the scene — used to place the camera. */
  maxDim: number;
}

// ── constants ────────────────────────────────────────────────────────────────

const WALL_T = 0.5;         // ft — matches plan model
const SLAB_T = 0.4;         // ft — floor / roof thickness
const TILE_T = 0.05;        // ft — floor tile overlay thickness
const DOOR_H_RATIO = 0.8;   // door height as fraction of floor_height
const WIN_SILL_RATIO = 0.25;
const WIN_H_RATIO = 0.42;

// Kitchen counter
const COUNTER_DEPTH = 2.0;  // ft (worktop depth)
const COUNTER_H = 3.0;      // ft (counter height)

// MEP block sizes [width_ft, depth_ft, height_ft]
const MEP_SIZES: Record<string, [number, number, number]> = {
  wc:      [1.4, 2.0, 1.5],
  toilet:  [1.4, 2.0, 1.5],
  basin:   [1.0, 1.5, 0.75],
  shower:  [2.5, 3.0, 0.15],   // floor tray only
  bath:    [2.5, 5.0, 1.8],
  ac:      [3.0, 1.0, 0.7],    // indoor wall unit
};

// ── helpers ──────────────────────────────────────────────────────────────────

let _uid = 0;
function uid(): string {
  return `b${_uid++}`;
}

function _safe(name: string): string {
  return name.replace(/\s+/g, "_").replace(/'/g, "");
}

/** Map a room's floor_material string to a MaterialId. */
function _floorMat(material: string): MaterialId {
  const m = material.toLowerCase();
  if (m.includes("marble")) return "floor_marble";
  if (m.includes("dark") || m.includes("granite") || m.includes("slate") || m.includes("black")) return "floor_tile_dark";
  if (m.includes("tile") || m.includes("vitrified") || m.includes("ceramic") || m.includes("stone")) return "floor_tile_light";
  return "floor";
}

// ── floor tile overlays (Phase 35) ───────────────────────────────────────────

function _buildFloorOverlays(project: ArchitectureProject, h: number): MassingBox[] {
  if (!project.material_plan?.generated) return [];
  const boxes: MassingBox[] = [];
  const finishes = project.material_plan.room_finishes ?? [];

  for (const finish of finishes) {
    const room = project.rooms.find((r) => r.id === finish.room_id);
    if (!room) continue;
    const mat = _floorMat(finish.floor_material);
    if (mat === "floor") continue; // unchanged — skip overlay
    const baseY = room.level * h;
    // Thin slab just above floor slab, covering room footprint (minus wall thickness)
    const inset = WALL_T / 2;
    boxes.push({
      id: uid(),
      name: `Scotch_FloorTile_${_safe(room.name)}`,
      pos: [room.x + room.width / 2, baseY + SLAB_T / 4 + TILE_T / 2, room.y + room.depth / 2],
      size: [Math.max(0.5, room.width - inset * 2), TILE_T, Math.max(0.5, room.depth - inset * 2)],
      mat,
    });
  }
  return boxes;
}

// ── MEP 3D blocks (Phase 35) ─────────────────────────────────────────────────

function _buildMepBlocks(project: ArchitectureProject, h: number): MassingBox[] {
  if (!project.mep_plan?.generated) return [];
  const boxes: MassingBox[] = [];
  const roomMap = new Map(project.rooms.map((r) => [r.id, r]));

  const allPoints = [
    ...(project.mep_plan.plumbing.points ?? []),
    ...(project.mep_plan.ac.points ?? []),
  ];

  for (const pt of allPoints) {
    const room = roomMap.get(pt.room_id);
    const baseY = room ? room.level * h : 0;
    const kindKey = pt.kind.toLowerCase().replace(/[^a-z]/g, "");

    const sz = MEP_SIZES[kindKey];
    if (!sz) continue; // skip outlets, switches, lights etc.

    const [bw, bd, bh] = sz;
    // wall-mounted: AC unit placed at mount_height; floor-mounted: at floor level
    const isWallMounted = pt.mount_height > 1.0;
    const centerY = isWallMounted
      ? baseY + pt.mount_height + bh / 2
      : baseY + bh / 2;

    boxes.push({
      id: uid(),
      name: `Scotch_MEP_${pt.kind}_${pt.id.slice(0, 6)}`,
      pos: [pt.x, centerY, pt.y],
      size: [bw, bh, bd],
      mat: "mep_block",
    });
  }
  return boxes;
}

// ── Kitchen counter geometry (Phase 35) ──────────────────────────────────────

function _buildKitchenCounters(project: ArchitectureProject, h: number): MassingBox[] {
  const boxes: MassingBox[] = [];
  const kitchenTypes = new Set(["kitchen", "kitchenette", "pantry"]);

  for (const room of project.rooms) {
    if (!kitchenTypes.has(room.type.toLowerCase())) continue;
    const baseY = room.level * h;
    const rSafe = _safe(room.name);

    // L-shaped counter: long counter along north wall + short return on east wall
    const counterLen = Math.max(2, room.width - WALL_T * 2 - 1.0); // leave 1 ft gap
    const inset = WALL_T + 0.05;

    // Main counter along north (top) wall of kitchen
    boxes.push({
      id: uid(),
      name: `Scotch_Counter_${rSafe}_Main`,
      pos: [room.x + inset + counterLen / 2, baseY + COUNTER_H / 2, room.y + inset + COUNTER_DEPTH / 2],
      size: [counterLen, COUNTER_H, COUNTER_DEPTH],
      mat: "counter",
    });

    // Return counter along east wall if room is wide enough
    if (room.depth > 8) {
      const returnLen = Math.min(room.depth / 2, 4);
      boxes.push({
        id: uid(),
        name: `Scotch_Counter_${rSafe}_Return`,
        pos: [room.x + room.width - inset - COUNTER_DEPTH / 2, baseY + COUNTER_H / 2, room.y + inset + returnLen / 2],
        size: [COUNTER_DEPTH, COUNTER_H, returnLen],
        mat: "counter",
      });
    }
  }
  return boxes;
}

// ── Stair geometry (Phase 35) ─────────────────────────────────────────────────

function _buildStairs(project: ArchitectureProject, h: number): MassingBox[] {
  if (!project.stairs?.length) return [];
  const boxes: MassingBox[] = [];
  const roomMap = new Map(project.rooms.map((r) => [r.id, r]));

  for (const stair of project.stairs) {
    const room = roomMap.get(stair.room_id);
    if (!room) continue;
    const baseY = stair.level_from * h;
    const totalH = (stair.level_to - stair.level_from) * h;
    if (totalH <= 0) continue;

    // Stair flight as a sloped-ish solid block (simplified for 3D preview)
    const rSafe = _safe(room.name);
    const flightLen = stair.risers * stair.tread_depth;

    let pos: [number, number, number];
    let size: [number, number, number];

    switch (stair.flight_direction) {
      case "north":
        pos  = [room.x + room.width / 2, baseY + totalH / 2, room.y + flightLen / 2];
        size = [stair.width, totalH, flightLen];
        break;
      case "south":
        pos  = [room.x + room.width / 2, baseY + totalH / 2, room.y + room.depth - flightLen / 2];
        size = [stair.width, totalH, flightLen];
        break;
      case "east":
        pos  = [room.x + flightLen / 2, baseY + totalH / 2, room.y + room.depth / 2];
        size = [flightLen, totalH, stair.width];
        break;
      default: // west
        pos  = [room.x + room.width - flightLen / 2, baseY + totalH / 2, room.y + room.depth / 2];
        size = [flightLen, totalH, stair.width];
    }

    boxes.push({
      id: uid(),
      name: `Scotch_Stair_${rSafe}`,
      pos,
      size,
      mat: "stair",
    });
  }
  return boxes;
}

// ── main entry ────────────────────────────────────────────────────────────────

export function buildMassingData(project: ArchitectureProject): MassingData {
  _uid = 0; // deterministic within one call
  const { site, building, rooms, doors, windows } = project;
  const h = building.floor_height;
  const sw = site.width;
  const sd = site.depth;
  const nFloors = Math.max(1, building.floors);

  const boxes: MassingBox[] = [];

  // Ground plane (large, slightly below y=0)
  boxes.push({
    id: uid(),
    name: "Scotch_Ground",
    pos: [sw / 2, -SLAB_T / 2, sd / 2],
    size: [sw + 4, SLAB_T, sd + 4],
    mat: "ground",
  });

  // Floor slab per level + roof on top
  for (let lvl = 0; lvl < nFloors; lvl++) {
    const baseY = lvl * h;
    boxes.push({
      id: uid(),
      name: `Scotch_Floor_Slab_L${lvl}`,
      pos: [sw / 2, baseY + SLAB_T / 4, sd / 2],
      size: [sw, SLAB_T / 2, sd],
      mat: "floor",
    });
  }
  // Roof on top floor
  boxes.push({
    id: uid(),
    name: "Scotch_Roof",
    pos: [sw / 2, nFloors * h + SLAB_T / 2, sd / 2],
    size: [sw, SLAB_T, sd],
    mat: "roof",
  });

  // Per-room: 4 wall boxes + opening overlays
  for (const room of rooms) {
    const baseY = room.level * h; // vertical offset for this floor
    const rx = room.x;
    const rz = room.y; // plan y → three.js z
    const rw = room.width;
    const rd = room.depth;

    const rSafe = room.name.replace(/\s+/g, "_");
    const wallDefs: Array<{ id_: string; name_: string; pos: [number, number, number]; size: [number, number, number] }> = [
      { id_: uid(), name_: `Scotch_Wall_${rSafe}_N`, pos: [rx + rw / 2, baseY + h / 2, rz],        size: [rw, h, WALL_T] },
      { id_: uid(), name_: `Scotch_Wall_${rSafe}_S`, pos: [rx + rw / 2, baseY + h / 2, rz + rd],   size: [rw, h, WALL_T] },
      { id_: uid(), name_: `Scotch_Wall_${rSafe}_W`, pos: [rx,          baseY + h / 2, rz + rd / 2], size: [WALL_T, h, rd] },
      { id_: uid(), name_: `Scotch_Wall_${rSafe}_E`, pos: [rx + rw,     baseY + h / 2, rz + rd / 2], size: [WALL_T, h, rd] },
    ];
    for (const w of wallDefs) {
      boxes.push({ id: w.id_, name: w.name_, pos: w.pos, size: w.size, mat: "wall" });
    }

    // Door openings — inset glass box through the wall
    for (const door of doors.filter((d) => d.room_id === room.id)) {
      const dh = h * DOOR_H_RATIO;
      const oy = baseY + dh / 2;
      const o = door.offset;
      const dw = door.width;
      const girth = WALL_T + 0.12;

      let pos: [number, number, number];
      let size: [number, number, number];
      switch (door.wall) {
        case "north": pos = [rx + o + dw / 2, oy, rz];       size = [dw, dh, girth]; break;
        case "south": pos = [rx + o + dw / 2, oy, rz + rd];  size = [dw, dh, girth]; break;
        case "west":  pos = [rx,       oy, rz + o + dw / 2]; size = [girth, dh, dw]; break;
        case "east":  pos = [rx + rw,  oy, rz + o + dw / 2]; size = [girth, dh, dw]; break;
        default:      continue;
      }
      boxes.push({ id: uid(), name: `Scotch_Glass_${rSafe}_Door_${door.wall}`, pos, size, mat: "glass" });
    }

    // Window openings — glass box at sill height
    for (const win of windows.filter((w) => w.room_id === room.id)) {
      const sill = h * WIN_SILL_RATIO;
      const wh = h * WIN_H_RATIO;
      const wy = baseY + sill + wh / 2;
      const o = win.offset;
      const ww = win.width;
      const girth = WALL_T + 0.12;

      let pos: [number, number, number];
      let size: [number, number, number];
      switch (win.wall) {
        case "north": pos = [rx + o + ww / 2, wy, rz];       size = [ww, wh, girth]; break;
        case "south": pos = [rx + o + ww / 2, wy, rz + rd];  size = [ww, wh, girth]; break;
        case "west":  pos = [rx,       wy, rz + o + ww / 2]; size = [girth, wh, ww]; break;
        case "east":  pos = [rx + rw,  wy, rz + o + ww / 2]; size = [girth, wh, ww]; break;
        default:      continue;
      }
      boxes.push({ id: uid(), name: `Scotch_Glass_${rSafe}_Win_${win.wall}`, pos, size, mat: "glass" });
    }
  }

  // Furniture boxes (show_furniture toggle respected)
  if (project.show_furniture) {
    for (const item of project.furniture) {
      const room = rooms.find((r) => r.id === item.room_id);
      const baseY = room ? room.level * h : 0;
      const fh = item.height;
      boxes.push({
        id: uid(),
        name: `Scotch_Furniture_${item.type}_${item.id.slice(0, 6)}`,
        pos: [item.x + item.width / 2, baseY + fh / 2, item.y + item.depth / 2],
        size: [item.width, fh, item.depth],
        mat: "furniture",
      });
    }
  }

  // Phase 35 additions —————————————————————————————————————————————————————————

  // Floor tile overlays from material_plan
  for (const b of _buildFloorOverlays(project, h)) boxes.push(b);

  // Kitchen counters
  for (const b of _buildKitchenCounters(project, h)) boxes.push(b);

  // MEP service point blocks
  for (const b of _buildMepBlocks(project, h)) boxes.push(b);

  // Stair geometry
  for (const b of _buildStairs(project, h)) boxes.push(b);

  const maxDim = Math.max(sw, sd, h * nFloors * 2);
  return { boxes, centerX: sw / 2, centerZ: sd / 2, maxDim };
}
