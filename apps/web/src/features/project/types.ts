/**
 * ArchitectureProject — the universal architecture model and single source
 * of truth for previews, parameters, schedules, and exports.
 *
 * Field names are snake_case to match the backend Pydantic JSON one-to-one
 * (formalized in Phase 3); the mock data and all UI components use these
 * types so the backend swap is a data-source change, not a refactor.
 */

export type Units = "feet" | "meters";
export type Orientation = "north" | "south" | "east" | "west";
export type WallSide = "north" | "south" | "east" | "west";
export type WarningSeverity = "info" | "warning" | "error";

export interface Site {
  width: number;
  depth: number;
  orientation: Orientation;
}

export interface Building {
  type: string;
  style: string;
  floors: number;
  floor_height: number;
}

export interface Level {
  index: number;
  name: string;
  elevation: number;
}

export interface Room {
  id: string;
  name: string;
  type: string;
  /** Position of the room's top-left corner on the site plan, in project units. */
  x: number;
  y: number;
  width: number;
  depth: number;
  level: number;
}

/** Explicit wall segment; optional while rooms imply their own walls. */
export interface Wall {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  thickness: number;
  room_id?: string | null;
}

export interface Door {
  id: string;
  room_id: string;
  wall: WallSide;
  /** Distance from the wall's start (left/top end) to the opening start. */
  offset: number;
  width: number;
}

export interface WindowOpening {
  id: string;
  room_id: string;
  wall: WallSide;
  offset: number;
  width: number;
}

export interface Material {
  id: string;
  name: string;
  /** What the material applies to, e.g. wall, floor, roof, glass. */
  target: string;
  finish?: string | null;
  /** Hex color hint for render engines, e.g. "#F5F4F2". */
  base_color: string;
  /** Principled BSDF roughness hint (0–1). */
  roughness: number;
  /** Principled BSDF metallic hint (0–1). */
  metallic: number;
}

/** A camera preset derived from site/room geometry for render workflows. */
export interface CameraSuggestion {
  name: string;
  type: "perspective" | "orthographic";
  /** [plan_x, height, plan_y] in project units — maps to three.js [x, y, z] */
  position: [number, number, number];
  /** [plan_x, height, plan_y] in project units */
  target: [number, number, number];
  /** Horizontal FOV in degrees; 0 for orthographic. */
  fov: number;
  description: string;
}

export interface Parameter {
  key: string;
  label: string;
  value: string | number;
  unit?: string | null;
  category: "site" | "building" | "room";
  editable: boolean;
  target_id?: string | null;
  min?: number | null;
  max?: number | null;
}

export interface ProjectWarning {
  id: string;
  severity: WarningSeverity;
  message: string;
}

export interface ArchitectureProject {
  id: string;
  name: string;
  units: Units;
  site: Site;
  building: Building;
  levels: Level[];
  rooms: Room[];
  walls: Wall[];
  doors: Door[];
  windows: WindowOpening[];
  materials: Material[];
  parameters: Parameter[];
  notes: string[];
  warnings: ProjectWarning[];
}

export interface ExportManifest {
  filename: string;
  format: string;
  path: string;
  created_at: string;
}

/** One compact / balanced / spacious variant generated from a prompt (Phase 10). */
export interface DesignOption {
  option_id: string;
  variant: "compact" | "balanced" | "spacious";
  score: number;
  summary: string;
  warnings: ProjectWarning[];
  preview: ArchitectureProject;
}

// ── Version history (Phase 19) ────────────────────────────────────────────────

export type VersionChangeType =
  | "generate"
  | "regenerate"
  | "edit"
  | "option"
  | "restore";

export interface ProjectVersionMeta {
  version_id: string;
  created_at: string;
  change_type: VersionChangeType;
  summary: string;
  room_count: number;
  total_area: number;
  thumbnail: string | null;
}

export interface ProjectVersion {
  version_id: string;
  created_at: string;
  change_type: VersionChangeType;
  summary: string;
  snapshot: ArchitectureProject;
}

export function roomArea(room: Room): number {
  return room.width * room.depth;
}

export function formatRoomSize(room: Room): string {
  return `${room.width} × ${room.depth}`;
}

export function totalBuiltArea(project: ArchitectureProject): number {
  return project.rooms.reduce((sum, room) => sum + roomArea(room), 0);
}

export function unitLabel(units: Units): string {
  return units === "feet" ? "ft" : "m";
}
