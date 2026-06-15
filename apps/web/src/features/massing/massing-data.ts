/**
 * Stage 8.1 — 3D massing data generator.
 *
 * Converts an ArchitectureProject into a flat list of MassingBox descriptors
 * that the viewer turns into three.js meshes.
 *
 * Coordinate mapping:
 *   Plan x  → three.js x  (east = +x)
 *   Plan y  → three.js z  (south = +z, y=0 is entrance/north)
 *   Height  → three.js y  (up = +y)
 *
 * MVP simplification: walls as solid boxes; door and window openings are
 * rendered as inset glass-material boxes overlaid on the wall face (no CSG).
 * The roof and floor are flat slabs over the full site footprint.
 */

import type { ArchitectureProject } from "@/features/project/types";

// ── types ────────────────────────────────────────────────────────────────────

export type MaterialId = "wall" | "floor" | "roof" | "glass" | "ground";

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

const WALL_T = 0.5;    // ft — matches plan model
const SLAB_T = 0.4;    // ft — floor / roof thickness
const DOOR_H_RATIO = 0.8;   // door height as fraction of floor_height
const WIN_SILL_RATIO = 0.25; // window sill bottom as fraction of floor_height
const WIN_H_RATIO = 0.42;    // window height as fraction of floor_height

// ── helpers ──────────────────────────────────────────────────────────────────

let _uid = 0;
function uid(): string {
  return `b${_uid++}`;
}

// ── main entry ────────────────────────────────────────────────────────────────

export function buildMassingData(project: ArchitectureProject): MassingData {
  _uid = 0; // deterministic within one call
  const { site, building, rooms, doors, windows } = project;
  const h = building.floor_height;
  const sw = site.width;
  const sd = site.depth;

  const boxes: MassingBox[] = [];

  // Ground plane (large, slightly below y=0)
  boxes.push({
    id: uid(),
    name: "Scotch_Ground",
    pos: [sw / 2, -SLAB_T / 2, sd / 2],
    size: [sw + 4, SLAB_T, sd + 4],
    mat: "ground",
  });

  // Floor slab
  boxes.push({
    id: uid(),
    name: "Scotch_Floor_Slab",
    pos: [sw / 2, SLAB_T / 4, sd / 2],
    size: [sw, SLAB_T / 2, sd],
    mat: "floor",
  });

  // Roof slab (flat, one per building; multi-floor in Phase 10+)
  boxes.push({
    id: uid(),
    name: "Scotch_Roof",
    pos: [sw / 2, h + SLAB_T / 2, sd / 2],
    size: [sw, SLAB_T, sd],
    mat: "roof",
  });

  // Per-room: 4 wall boxes + opening overlays
  for (const room of rooms) {
    const rx = room.x;
    const rz = room.y; // plan y → three.js z
    const rw = room.width;
    const rd = room.depth;

    const rSafe = room.name.replace(/\s+/g, "_");
    // Four perimeter walls — named for GLTF node hierarchy
    const wallDefs: Array<{ id_: string; name_: string; pos: [number, number, number]; size: [number, number, number] }> = [
      { id_: uid(), name_: `Scotch_Wall_${rSafe}_N`, pos: [rx + rw / 2, h / 2, rz],        size: [rw, h, WALL_T] },
      { id_: uid(), name_: `Scotch_Wall_${rSafe}_S`, pos: [rx + rw / 2, h / 2, rz + rd],   size: [rw, h, WALL_T] },
      { id_: uid(), name_: `Scotch_Wall_${rSafe}_W`, pos: [rx,          h / 2, rz + rd / 2], size: [WALL_T, h, rd] },
      { id_: uid(), name_: `Scotch_Wall_${rSafe}_E`, pos: [rx + rw,     h / 2, rz + rd / 2], size: [WALL_T, h, rd] },
    ];
    for (const w of wallDefs) {
      boxes.push({ id: w.id_, name: w.name_, pos: w.pos, size: w.size, mat: "wall" });
    }

    // Door openings — inset glass box through the wall
    for (const door of doors.filter((d) => d.room_id === room.id)) {
      const dh = h * DOOR_H_RATIO;
      const oy = dh / 2;
      const o = door.offset;
      const dw = door.width;
      const girth = WALL_T + 0.12; // poke through both wall faces

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
      const wy = sill + wh / 2;
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

  const maxDim = Math.max(sw, sd, h * 2);
  return { boxes, centerX: sw / 2, centerZ: sd / 2, maxDim };
}
