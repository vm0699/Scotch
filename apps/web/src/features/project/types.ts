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

export interface Parameter {
  key: string;
  label: string;
  value: string | number;
  unit?: string;
  category: "site" | "building" | "room";
  editable: boolean;
  target_id?: string;
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
  rooms: Room[];
  doors: Door[];
  windows: WindowOpening[];
  parameters: Parameter[];
  notes: string[];
  warnings: ProjectWarning[];
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
