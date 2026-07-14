"""Phase 43 Stage 43.3 — Interior furniture validation.

Extends the shared validator (validator.py) with rules specific to a single
room's furniture layout: used by both the deterministic placer's output (as
a sanity check / warning source) and the AI proposer's output (as the
authoritative gate before it's accepted).

Door-swing and window-blocking checks are geometric approximations — good
enough to catch "wardrobe dumped in front of the door" mistakes, not a
substitute for a real swing-arc/sightline engine.
"""

from __future__ import annotations

import uuid

from app.core.models.project import ArchitectureProject, FurnitureItem, ProjectWarning, Room
from app.core.validation.validator import ValidationResult

ITEM_GAP = 0.1  # ft — matches furniture_placer.ITEM_GAP


def _overlaps(ax: float, ay: float, aw: float, ad: float, bx: float, by: float, bw: float, bd: float) -> bool:
    return not (
        ax + aw + ITEM_GAP <= bx
        or bx + bw + ITEM_GAP <= ax
        or ay + ad + ITEM_GAP <= by
        or by + bd + ITEM_GAP <= ay
    )


def _door_swing_zone(room: Room, door) -> tuple[float, float, float, float]:
    """Conservative square swing zone extending `door.width` into the room
    from the opening, covering the full arc the door sweeps through."""
    w = door.width
    if door.wall == "north":
        return (room.x + door.offset, room.y, w, w)
    if door.wall == "south":
        return (room.x + door.offset, room.y + room.depth - w, w, w)
    if door.wall == "west":
        return (room.x, room.y + door.offset, w, w)
    # east
    return (room.x + room.width - w, room.y + door.offset, w, w)


def door_blocking_item_ids(room: Room, items: list[FurnitureItem], project: ArchitectureProject) -> set[str]:
    """Item ids whose footprint intrudes into a door's swing zone. Shared by
    the validator (to report the error) and interior_designer.py's
    deterministic path (to self-heal by dropping the blocker before it's ever
    persisted, rather than shipping a room that then rejects every edit)."""
    doors = [d for d in project.doors if d.room_id == room.id]
    blocking: set[str] = set()
    for door in doors:
        zx, zy, zw, zd = _door_swing_zone(room, door)
        for item in items:
            if _overlaps(item.x, item.y, item.width, item.depth, zx, zy, zw, zd):
                blocking.add(item.id)
    return blocking


def validate_room_furniture(
    room: Room, items: list[FurnitureItem], project: ArchitectureProject
) -> ValidationResult:
    errors: list[str] = []
    warning_msgs: list[str] = []

    # Bounds — every item's footprint fits inside the room.
    for item in items:
        if (
            item.x < room.x - 1e-6
            or item.y < room.y - 1e-6
            or item.x + item.width > room.x + room.width + 1e-6
            or item.y + item.depth > room.y + room.depth + 1e-6
        ):
            errors.append(f"'{item.label}' extends outside room '{room.name}'")

    # No-overlap between items in this room.
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if _overlaps(a.x, a.y, a.width, a.depth, b.x, b.y, b.width, b.depth):
                errors.append(f"'{a.label}' overlaps '{b.label}' in room '{room.name}'")

    # Door-swing collision — hard error (blocks the door from opening).
    by_id = {item.id: item for item in items}
    for item_id in door_blocking_item_ids(room, items, project):
        item = by_id[item_id]
        errors.append(f"'{item.label}' blocks a door swing in '{room.name}'")

    # Window blocking — advisory only (a dresser under a window is common and fine;
    # something taller than the sill blocking most of the window's span is not).
    windows = [w for w in project.windows if w.room_id == room.id]
    for window in windows:
        sill_ratio = 0.25  # matches WIN_SILL_RATIO in massing-data.ts
        for item in items:
            item_wall_span = _wall_span_overlap(room, window, item)
            if item_wall_span > 0.5 * window.width and item.height > room_wall_sill_height(project, sill_ratio):
                warning_msgs.append(
                    f"'{item.label}' may block the window on the {window.wall} wall of '{room.name}'"
                )

    warnings = [
        ProjectWarning(id=f"interior-{uuid.uuid4().hex[:8]}", severity="warning", message=msg)
        for msg in warning_msgs
    ]
    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def room_wall_sill_height(project: ArchitectureProject, sill_ratio: float) -> float:
    return project.building.floor_height * sill_ratio


def _wall_span_overlap(room: Room, window, item: FurnitureItem) -> float:
    """How much of the window's along-wall span the item's footprint covers,
    in feet (0 = no overlap). Only meaningful when the item sits against the
    same wall as the window."""
    if window.wall in ("north", "south"):
        item_wall = "north" if abs(item.y - room.y) < 0.5 else ("south" if abs(item.y + item.depth - (room.y + room.depth)) < 0.5 else None)
        if item_wall != window.wall:
            return 0.0
        win_start, win_end = room.x + window.offset, room.x + window.offset + window.width
        item_start, item_end = item.x, item.x + item.width
    else:
        item_wall = "west" if abs(item.x - room.x) < 0.5 else ("east" if abs(item.x + item.width - (room.x + room.width)) < 0.5 else None)
        if item_wall != window.wall:
            return 0.0
        win_start, win_end = room.y + window.offset, room.y + window.offset + window.width
        item_start, item_end = item.y, item.y + item.depth

    return max(0.0, min(win_end, item_end) - max(win_start, item_start))
