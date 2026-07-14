/**
 * Stage 43.2 — "Enter room" camera framing.
 *
 * Pure client-side geometry (no backend round-trip needed — the frontend
 * already has full room bounds). Mirrors the elevated 3/4-view convention
 * used for the whole-building default camera in massing-viewer.tsx, just
 * scoped to one room's footprint instead of the whole site.
 */

import type { ArchitectureProject } from "@/features/project/types";

export interface RoomCameraFrame {
  roomId: string;
  roomName: string;
  position: [number, number, number];
  target: [number, number, number];
}

export function deriveRoomFocusCamera(
  project: ArchitectureProject,
  roomId: string,
): RoomCameraFrame | null {
  const room = project.rooms.find((r) => r.id === roomId);
  if (!room) return null;

  const h = project.building.floor_height;
  const baseY = room.level * h;
  const roomCenterX = room.x + room.width / 2;
  const roomCenterZ = room.y + room.depth / 2;
  const roomMaxDim = Math.max(room.width, room.depth);

  const d = roomMaxDim * 1.3;
  return {
    roomId: room.id,
    roomName: room.name,
    position: [roomCenterX + d * 0.55, baseY + d * 0.5, roomCenterZ + d * 0.75],
    target: [roomCenterX, baseY + h * 0.35, roomCenterZ],
  };
}
