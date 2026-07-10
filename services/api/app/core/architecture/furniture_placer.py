"""Wall-affinity furniture placement engine (Phase 26.3).

Placing strategy (per room):
  1. Load the per-type FurnitureSpec template filtered to room area/size.
  2. Sort by priority ascending (lower = more important, placed first).
  3. For each spec compute a candidate bounding box flush against the declared
     wall (or centred in the room for "center" items).
  4. Check clearance: the space in front of the item (into the room) must be
     ≥ spec.clearance and must not push the item outside the room.
  5. Check no overlap against already-placed items (ITEM_GAP buffer between
     footprints).
  6. If a chair spec is adjacent to a dining_table, snap it to the correct
     side of that table rather than treating it as wall-affinity.
  7. If the candidate fails checks, skip it with no warning (the room is too
     small for that item given what's already placed).

Coordinate convention:
  Room origin: top-left corner of the room at (room.x, room.y).
  y increases downward in plan space (matching SVG convention).
  "north wall" → item placed at y = room.y + WALL_GAP
  "south wall" → item placed at y = room.y + room.depth - item_depth - WALL_GAP
  "east wall"  → item placed at x = room.x + room.width - item_width - WALL_GAP
  "west wall"  → item placed at x = room.x + WALL_GAP

  Rotation assigned by wall:
    north → 0°  (item faces south into the room)
    south → 180° (item faces north)
    east  → 270° (item faces west)
    west  → 90°  (item faces east)
    center → 0°
"""

from __future__ import annotations

import uuid
from typing import NamedTuple

from app.core.architecture.furniture_defaults import (
    FurnitureSpec,
    furniture_height,
    get_template,
)
from app.core.models.project import ArchitectureProject, FurnitureItem, Room

WALL_GAP = 0.1      # ft gap between item and wall surface
ITEM_GAP = 0.2      # ft minimum buffer between placed items
MIN_CLEARANCE = 2.5 # ft default walkway clearance if spec.clearance is 0


class _Box(NamedTuple):
    x: float
    y: float
    w: float
    d: float


def _overlaps(a: _Box, b: _Box) -> bool:
    """Axis-aligned overlap test with ITEM_GAP buffer."""
    g = ITEM_GAP
    return not (
        a.x + a.w + g <= b.x
        or b.x + b.w + g <= a.x
        or a.y + a.d + g <= b.y
        or b.y + b.d + g <= a.y
    )


def _fits_in_room(box: _Box, room: Room) -> bool:
    return (
        box.x >= room.x - 1e-6
        and box.y >= room.y - 1e-6
        and box.x + box.w <= room.x + room.width + 1e-6
        and box.y + box.d <= room.y + room.depth + 1e-6
    )


def _wall_rotation(wall: str) -> int:
    return {"north": 0, "south": 180, "east": 270, "west": 90, "center": 0}[wall]


def _candidate(
    spec: FurnitureSpec, room: Room, placed_boxes: list[_Box],
) -> _Box | None:
    """Compute a candidate bounding box for *spec* inside *room*.

    Returns the box if it fits and passes all checks, else None.
    """
    rw, rd = room.width, room.depth
    rx, ry = room.x, room.y

    wall = spec.wall
    # For east/west walls the item is rotated 90°: swap width/depth for the
    # placed footprint so the long axis runs along the wall.
    if wall in ("east", "west"):
        iw = spec.depth
        id_ = spec.width
    else:
        iw = spec.width
        id_ = spec.depth

    # Ensure item fits within the room at all
    if iw > rw - 2 * WALL_GAP or id_ > rd - 2 * WALL_GAP:
        return None

    # Along-wall alignment (horizontal for north/south, vertical for east/west)
    def _align_x(item_w: float) -> float:
        a = spec.x_align
        if a == "center":
            return rx + (rw - item_w) / 2
        elif a == "left":
            return rx + spec.x_gap
        else:  # right
            return rx + rw - item_w - spec.x_gap

    def _align_y(item_d: float) -> float:
        a = spec.x_align
        if a == "center":
            return ry + (rd - item_d) / 2
        elif a == "left":  # "left" along south/north wall = top
            return ry + spec.x_gap
        else:
            return ry + rd - item_d - spec.x_gap

    if wall == "north":
        bx = _align_x(iw)
        by = ry + WALL_GAP
        clearance_end = by + id_ + max(spec.clearance, 0)
        if clearance_end > ry + rd - WALL_GAP:
            return None
    elif wall == "south":
        bx = _align_x(iw)
        by = ry + rd - id_ - WALL_GAP
        clearance_start = by - max(spec.clearance, 0)
        if clearance_start < ry + WALL_GAP:
            return None
    elif wall == "east":
        bx = rx + rw - iw - WALL_GAP
        by = _align_y(id_)
        clearance_start = bx - max(spec.clearance, 0)
        if clearance_start < rx + WALL_GAP:
            return None
    elif wall == "west":
        bx = rx + WALL_GAP
        by = _align_y(id_)
        clearance_end = bx + iw + max(spec.clearance, 0)
        if clearance_end > rx + rw - WALL_GAP:
            return None
    else:  # center
        bx = rx + (rw - iw) / 2
        by = ry + (rd - id_) / 2

    box = _Box(round(bx, 2), round(by, 2), round(iw, 2), round(id_, 2))

    if not _fits_in_room(box, room):
        return None
    for pb in placed_boxes:
        if _overlaps(box, pb):
            return None
    return box


def _chair_boxes_around_table(
    table_box: _Box, room: Room, n_chairs: int, placed: list[_Box],
) -> list[_Box]:
    """Return up to *n_chairs* chair boxes placed around *table_box*."""
    chair_size = 1.5
    gap = 0.3
    chairs: list[_Box] = []

    sides = [
        # (x, y, w, d)
        (table_box.x + table_box.w / 2 - chair_size / 2,
         table_box.y - chair_size - gap, chair_size, chair_size),  # north
        (table_box.x + table_box.w / 2 - chair_size / 2,
         table_box.y + table_box.d + gap, chair_size, chair_size),  # south
        (table_box.x - chair_size - gap,
         table_box.y + table_box.d / 2 - chair_size / 2, chair_size, chair_size),  # west
        (table_box.x + table_box.w + gap,
         table_box.y + table_box.d / 2 - chair_size / 2, chair_size, chair_size),  # east
        # Second chair on north side (slightly offset)
        (table_box.x + table_box.w / 4 - chair_size / 2,
         table_box.y - chair_size - gap, chair_size, chair_size),
        (table_box.x + 3 * table_box.w / 4 - chair_size / 2,
         table_box.y - chair_size - gap, chair_size, chair_size),
        # Second chair on south side
        (table_box.x + table_box.w / 4 - chair_size / 2,
         table_box.y + table_box.d + gap, chair_size, chair_size),
        (table_box.x + 3 * table_box.w / 4 - chair_size / 2,
         table_box.y + table_box.d + gap, chair_size, chair_size),
    ]

    added = 0
    for raw in sides:
        if added >= n_chairs:
            break
        b = _Box(round(raw[0], 2), round(raw[1], 2), round(raw[2], 2), round(raw[3], 2))
        if not _fits_in_room(b, room):
            continue
        if any(_overlaps(b, pb) for pb in placed):
            continue
        chairs.append(b)
        placed.append(b)
        added += 1
    return chairs


# Chair type tags to treat as dining-chair items
_CHAIR_TYPES = {"chair_n1", "chair_n2", "chair_s1", "chair_s2", "chair_e", "chair_w"}


def place_furniture_in_room(room: Room) -> list[FurnitureItem]:
    """Place furniture items for one room and return placed FurnitureItems."""
    items: list[FurnitureItem] = []
    placed_boxes: list[_Box] = []

    specs = get_template(room.type, room.width, room.depth)
    if not specs:
        return []

    # Sort by priority ascending
    specs_sorted = sorted(specs, key=lambda s: s.priority)

    # Track the dining table box separately for chair placement
    dining_table_box: _Box | None = None

    # Count chair slots remaining
    chair_slots = sum(1 for s in specs_sorted if s.type in _CHAIR_TYPES)
    chairs_placed = 0

    for spec in specs_sorted:
        # Skip chairs here — they are handled after the table
        if spec.type in _CHAIR_TYPES:
            continue

        box = _candidate(spec, room, placed_boxes)
        if box is None:
            continue

        rotation = _wall_rotation(spec.wall)
        item = FurnitureItem(
            id=str(uuid.uuid4()),
            type=spec.type,
            label=spec.label,
            room_id=room.id,
            x=box.x,
            y=box.y,
            width=box.w,
            depth=box.d,
            rotation=rotation,
            height=furniture_height(spec.type),
        )
        items.append(item)
        placed_boxes.append(box)

        if spec.type == "dining_table":
            dining_table_box = box

    # Place chairs around dining table
    if dining_table_box is not None and chair_slots > 0:
        chair_boxes = _chair_boxes_around_table(
            dining_table_box, room, chair_slots, placed_boxes
        )
        for i, cb in enumerate(chair_boxes):
            items.append(FurnitureItem(
                id=str(uuid.uuid4()),
                type=f"chair_{i}",
                label="Chair",
                room_id=room.id,
                x=cb.x,
                y=cb.y,
                width=cb.w,
                depth=cb.d,
                rotation=0,
                height=furniture_height("chair_n1"),
            ))
            chairs_placed += 1

    return items


def place_all_furniture(project: ArchitectureProject) -> ArchitectureProject:
    """Replace project.furniture with a freshly computed full layout."""
    all_items: list[FurnitureItem] = []
    for room in project.rooms:
        all_items.extend(place_furniture_in_room(room))
    return project.model_copy(update={"furniture": all_items})
