"""Apply parameter changes to an existing project and re-pack the layout.

Edits never silently break a plan: after any change the rooms are re-packed
band by band (bands inferred from current y positions, preserving room
order, ids, names, and types), doors and windows are re-derived, and the
result is re-validated by the caller. Clamping and compression surface as
warnings exactly like first-pass generation.

Room IDs are stable across re-layout:
- apply_changes preserves each room's id via _Spec; ids survive site-size
  changes, add/remove operations, and parameter edits.
- add_room generates semantic ids (e.g. bed-master, bed-2, bath-1) rather
  than random strings, so diffs are human-readable.
"""

from pydantic import BaseModel

from app.core.architecture.defaults import DEFAULT_FLOOR_HEIGHT, default_size
from app.core.architecture.furniture_placer import place_all_furniture
from app.core.architecture.floorplan_generator import (
    _GenState,
    _openings,
    _pack_bands,
    _Spec,
    _stair_spec,
    _STAIR_W,
    _STAIR_D,
)
from app.core.models import ArchitectureProject, Level, Room

ROOM_MIN, ROOM_MAX = 3.0, 60.0
SITE_MIN, SITE_MAX = 10.0, 300.0
ORIENTATIONS = {"north", "south", "east", "west"}

# Generation-derived warning prefixes that must be recomputed, not carried over.
_STALE_WARNING_PREFIXES = (
    "warn-clamp-",
    "warn-depth-compressed",
    "warn-fit-",
    "warn-overlap-",
    "warn-open-area",
    "warn-entry-not-front",
)

# ── Stable room ID & zone helpers ──────────────────────────────────────────────

_ROOM_ZONE: dict[str, str] = {
    "living": "front",
    "studio": "front",
    "parking": "front",
    "balcony": "front",
    "cafe_seating": "front",
    "office": "front",
    "kitchen": "service",
    "kitchenette": "service",
    "dining": "service",
    "study": "service",
    "storage": "service",
    "cafe_counter": "service",
    "cafe_kitchen": "service",
    "restroom": "service",
    "bedroom": "private",
    "bathroom": "private",
}

_TYPE_ID_PREFIX: dict[str, str] = {
    "bedroom": "bed",
    "bathroom": "bath",
    "living": "living",
    "kitchenette": "kitchen",
    "kitchen": "kitchen",
    "dining": "dining",
    "study": "study",
    "storage": "storage",
    "balcony": "balcony",
    "parking": "parking",
    "cafe_seating": "seating",
    "cafe_counter": "counter",
    "cafe_kitchen": "cafe-kitchen",
    "office": "office",
    "studio": "studio",
    "restroom": "restroom",
}

# Room types that can be added via the add_room change key.
VALID_ADD_ROOM_TYPES: frozenset[str] = frozenset(_TYPE_ID_PREFIX.keys())

# Default size key for each room type (maps to defaults.py ROOM_DEFAULTS).
_SIZE_KEY: dict[str, str] = {
    "bedroom": "bedroom",
    "bathroom": "bathroom",
    "living": "living",
    "kitchen": "kitchen",
    "kitchenette": "kitchenette",
    "dining": "dining",
    "study": "study",
    "storage": "storage",
    "balcony": "balcony",
    "parking": "parking",
    "cafe_seating": "cafe_counter",
    "cafe_counter": "cafe_counter",
    "cafe_kitchen": "cafe_kitchen",
    "restroom": "restroom",
    "office": "open_plan",
    "studio": "studio_room",
}


def _stable_room_id(room_type: str, existing_rooms: list[Room]) -> str:
    """Generate the next stable semantic room ID for the given type.

    Uses the same id scheme the generator uses so version diffs are readable:
    bed-master / bed-2 / bed-3, bath-1 / bath-2, kitchen, dining, …
    """
    prefix = _TYPE_ID_PREFIX.get(room_type, room_type.replace("_", "-"))
    taken = {r.id for r in existing_rooms}

    if room_type == "bedroom":
        candidates = ["bed-master"] + [f"bed-{i}" for i in range(2, 20)]
    elif room_type == "bathroom":
        candidates = [f"bath-{i}" for i in range(1, 20)]
    else:
        candidates = [prefix] + [f"{prefix}-{i}" for i in range(2, 20)]

    for c in candidates:
        if c not in taken:
            return c
    same = sum(1 for r in existing_rooms if r.type == room_type)
    return f"{prefix}-{same + 1}"


def _default_room_name(room_type: str, existing_rooms: list[Room]) -> str:
    """Human-readable name for the next room of this type."""
    n = sum(1 for r in existing_rooms if r.type == room_type) + 1
    if room_type == "bedroom":
        return "Master Bedroom" if n == 1 else f"Bedroom {n}"
    if room_type == "bathroom":
        return "Common Bath" if n == 1 else f"Bath {n}"
    label = {
        "living": "Living Room",
        "kitchen": "Kitchen",
        "kitchenette": "Kitchenette",
        "dining": "Dining",
        "study": "Study",
        "storage": "Storage",
        "balcony": "Balcony",
        "parking": "Parking",
        "cafe_seating": "Seating Area",
        "cafe_counter": "Service Counter",
        "cafe_kitchen": "Cafe Kitchen",
        "restroom": "Restroom",
        "office": "Open Workspace",
        "studio": "Studio",
    }
    return label.get(room_type, room_type.replace("_", " ").title())


def _zone_y(rooms: list[Room], room_type: str) -> float:
    """Pick a y-position that places the new room in the correct zone band."""
    target_zone = _ROOM_ZONE.get(room_type, "service")
    zone_ys = [r.y for r in rooms if _ROOM_ZONE.get(r.type, "service") == target_zone]
    if zone_ys:
        return sorted(zone_ys)[0]
    if not rooms:
        return 0.0
    all_ys = sorted({r.y for r in rooms})
    if target_zone == "front":
        return all_ys[0]
    if target_zone == "service" and len(all_ys) >= 2:
        return all_ys[len(all_ys) // 2]
    return all_ys[-1]  # private zone or fallback


# ── Multi-floor helpers ────────────────────────────────────────────────────────


def _redistribute_floors(project: ArchitectureProject) -> None:
    """Re-assign room.level after a floors change, regenerating stair cores.

    - Public/service rooms stay on level 0.
    - Private rooms are distributed evenly across upper floors.
    - Stair rooms are removed and replaced with one per floor (if floors > 1).
    """
    n_floors = project.building.floors
    non_stair = [r for r in project.rooms if r.type != "stair"]

    front_svc = [r for r in non_stair if _ROOM_ZONE.get(r.type, "service") in ("front", "service")]
    private = [r for r in non_stair if _ROOM_ZONE.get(r.type, "service") == "private"]

    for r in front_svc:
        r.level = 0

    if n_floors <= 1:
        for r in private:
            r.level = 0
    else:
        n_upper = n_floors - 1
        chunk = max(1, (len(private) + n_upper - 1) // n_upper)
        for i, r in enumerate(private):
            r.level = min(i // chunk + 1, n_floors - 1)

    stair_rooms: list[Room] = []
    if n_floors > 1:
        for floor_idx in range(n_floors):
            spec = _stair_spec(floor_idx)
            stair_rooms.append(
                Room(
                    id=spec.id, name=spec.name, type=spec.type,
                    x=0.0, y=0.0, width=_STAIR_W, depth=_STAIR_D,
                    level=floor_idx,
                )
            )

    project.rooms = front_svc + private + stair_rooms


def _repack_project(project: ArchitectureProject, state: _GenState) -> None:
    """Re-pack rooms by level, regenerate doors and windows."""
    level_indices = sorted({r.level for r in project.rooms})
    all_rooms: list[Room] = []
    all_doors = []
    all_windows = []

    for lv in level_indices:
        level_rooms = [r for r in project.rooms if r.level == lv]
        bands: list[list[_Spec]] = []
        band_ys: list[float] = []
        for room in sorted(level_rooms, key=lambda r: (r.y, r.x)):
            spec = _Spec(id=room.id, name=room.name, type=room.type, width=room.width, depth=room.depth)
            if bands and abs(room.y - band_ys[-1]) < 1e-9:
                bands[-1].append(spec)
            else:
                bands.append([spec])
                band_ys.append(room.y)
        packed = _pack_bands(bands, project.site.width, project.site.depth, state, level=lv)
        all_rooms.extend(packed)
        d, w = _openings(packed, project.site.width, state)
        all_doors.extend(d)
        all_windows.extend(w)

    project.rooms = all_rooms
    project.doors = all_doors
    project.windows = all_windows


# ── Public API ─────────────────────────────────────────────────────────────────


class ParameterChange(BaseModel):
    key: str
    value: str | float | int
    target_id: str | None = None


class ChangeError(ValueError):
    """A change referenced an unknown key/room or an out-of-range value."""


def _as_number(change: ParameterChange, low: float, high: float) -> float:
    try:
        number = float(change.value)
    except (TypeError, ValueError) as exc:
        raise ChangeError(f"'{change.key}' expects a number, got {change.value!r}") from exc
    if not (low <= number <= high):
        raise ChangeError(f"'{change.key}' must be between {low:g} and {high:g}, got {number:g}")
    return number


def apply_changes(
    project: ArchitectureProject, changes: list[ParameterChange]
) -> tuple[ArchitectureProject, str]:
    project = project.model_copy(deep=True)
    rooms_by_id = {room.id: room for room in project.rooms}
    applied: list[str] = []

    for change in changes:
        if change.key == "site_width":
            project.site.width = _as_number(change, SITE_MIN, SITE_MAX)
            applied.append(f"site width → {project.site.width:g} ft")
        elif change.key == "site_depth":
            project.site.depth = _as_number(change, SITE_MIN, SITE_MAX)
            applied.append(f"site depth → {project.site.depth:g} ft")
        elif change.key == "orientation":
            value = str(change.value).lower()
            if value not in ORIENTATIONS:
                raise ChangeError(f"Unknown orientation '{change.value}'")
            project.site.orientation = value  # type: ignore[assignment]
            applied.append(f"orientation → {value}")
        elif change.key == "floors":
            project.building.floors = int(_as_number(change, 1, 4))
            applied.append(f"floors → {project.building.floors}")
            _redistribute_floors(project)
            project.levels = [
                Level(
                    index=i,
                    name="Ground Floor" if i == 0 else f"Floor {i}",
                    elevation=round(i * project.building.floor_height, 1),
                )
                for i in range(project.building.floors)
            ]
        elif change.key == "floor_height":
            project.building.floor_height = _as_number(change, 8, 14)
            applied.append(f"floor height → {project.building.floor_height:g} ft")
        elif change.key == "style":
            project.building.style = str(change.value).strip() or project.building.style
            applied.append(f"style → {project.building.style}")
        elif change.key in ("room_width", "room_depth", "room_name"):
            room = rooms_by_id.get(change.target_id or "")
            if room is None:
                raise ChangeError(f"'{change.key}' targets unknown room '{change.target_id}'")
            if change.key == "room_name":
                room.name = str(change.value).strip() or room.name
                applied.append(f"{room.id} renamed to \"{room.name}\"")
            elif change.key == "room_width":
                room.width = _as_number(change, ROOM_MIN, ROOM_MAX)
                applied.append(f"{room.name} width → {room.width:g} ft")
            else:
                room.depth = _as_number(change, ROOM_MIN, ROOM_MAX)
                applied.append(f"{room.name} depth → {room.depth:g} ft")

        elif change.key == "add_room":
            room_type = str(change.value).strip().lower()
            if room_type not in VALID_ADD_ROOM_TYPES:
                raise ChangeError(
                    f"Unknown room type '{room_type}'. "
                    f"Valid types: {', '.join(sorted(VALID_ADD_ROOM_TYPES))}"
                )
            new_id = _stable_room_id(room_type, list(project.rooms))
            is_first_bedroom = room_type == "bedroom" and not any(
                r.type == "bedroom" for r in project.rooms
            )
            size_key = "master_bedroom" if is_first_bedroom else _SIZE_KEY.get(room_type, room_type)
            try:
                w, d = default_size(size_key)
            except KeyError:
                w, d = 8.0, 10.0
            y = _zone_y(list(project.rooms), room_type)
            name = _default_room_name(room_type, list(project.rooms))
            new_room = Room(
                id=new_id, name=name, type=room_type,
                x=0.0, y=y, width=w, depth=d, level=0,
            )
            project.rooms.append(new_room)
            rooms_by_id[new_id] = new_room
            applied.append(f"added {name}")

        elif change.key == "remove_room":
            target = rooms_by_id.get(change.target_id or "")
            if target is None:
                raise ChangeError(f"'remove_room' targets unknown room '{change.target_id}'")
            if len(project.rooms) <= 1:
                raise ChangeError("Cannot remove the last room")
            project.rooms = [r for r in project.rooms if r.id != target.id]
            del rooms_by_id[target.id]
            applied.append(f"removed {target.name}")

        elif change.key == "room_level":
            room = rooms_by_id.get(change.target_id or "")
            if room is None:
                raise ChangeError(f"'room_level' targets unknown room '{change.target_id}'")
            new_level = int(_as_number(change, 0, project.building.floors - 1))
            room.level = new_level
            applied.append(f"{room.name} → level {new_level}")

        elif change.key == "show_furniture":
            project.show_furniture = bool(change.value)
            applied.append(f"furniture layer {'visible' if project.show_furniture else 'hidden'}")

        elif change.key == "show_dimensions":
            project.show_dimensions = bool(change.value)
            applied.append(f"dimension layer {'visible' if project.show_dimensions else 'hidden'}")

        elif change.key == "show_mep":
            project.show_mep = bool(change.value)
            applied.append(f"MEP layer {'visible' if project.show_mep else 'hidden'}")

        else:
            raise ChangeError(f"Unknown parameter '{change.key}'")

    # Re-pack per level (level-aware; IDs and order preserved).
    state = _GenState()
    _repack_project(project, state)

    # Mark MEP stale if rooms changed and MEP was already generated.
    room_mutating = {"add_room", "remove_room", "room_width", "room_depth", "site_width", "site_depth", "floors"}
    if project.mep_plan.generated and any(c.key in room_mutating for c in changes):
        from app.core.architecture.mep_generator import MEPGenerator
        project.mep_plan = MEPGenerator.mark_stale(project.mep_plan)

    # Mark detail drawings stale when their source rooms are mutated.
    if project.detail_drawings and any(c.key in room_mutating for c in changes):
        from app.core.architecture.detail_engine import DetailEngine
        affected_ids = {c.target_id for c in changes if c.target_id and c.key in room_mutating}
        for sid in affected_ids:
            project.detail_drawings = DetailEngine.mark_stale_for_source(project.detail_drawings, sid)

    # Refresh auto-dimensions
    from app.core.architecture.dimension_engine import AutoDimensionEngine
    project.dimensions = AutoDimensionEngine.derive(project)
    project.stairs = AutoDimensionEngine.derive_stair_entities(project)

    # Refresh parameter values; drop stale generation warnings, keep assumptions.
    values = {
        "site_width": project.site.width,
        "site_depth": project.site.depth,
        "orientation": project.site.orientation,
        "floors": project.building.floors,
        "floor_height": project.building.floor_height,
        "style": project.building.style,
    }
    for parameter in project.parameters:
        if parameter.key in values:
            parameter.value = values[parameter.key]

    project.warnings = [
        w for w in project.warnings if not w.id.startswith(_STALE_WARNING_PREFIXES)
    ] + state.warnings

    project = place_all_furniture(project)

    summary = (
        f"Applied {len(applied)} change{'s' if len(applied) != 1 else ''}: "
        + "; ".join(applied[:4])
        + ("…" if len(applied) > 4 else ".")
    )
    return project, summary
