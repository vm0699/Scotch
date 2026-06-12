"""Apply parameter changes to an existing project and re-pack the layout.

Edits never silently break a plan: after any change the rooms are re-packed
band by band (bands inferred from current y positions, preserving room
order, ids, names, and types), doors and windows are re-derived, and the
result is re-validated by the caller. Clamping and compression surface as
warnings exactly like first-pass generation.
"""

from pydantic import BaseModel

from app.core.architecture.floorplan_generator import (
    _GenState,
    _openings,
    _pack_bands,
    _Spec,
)
from app.core.models import ArchitectureProject

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
                applied.append(f"{room.id} renamed to “{room.name}”")
            elif change.key == "room_width":
                room.width = _as_number(change, ROOM_MIN, ROOM_MAX)
                applied.append(f"{room.name} width → {room.width:g} ft")
            else:
                room.depth = _as_number(change, ROOM_MIN, ROOM_MAX)
                applied.append(f"{room.name} depth → {room.depth:g} ft")
        else:
            raise ChangeError(f"Unknown parameter '{change.key}'")

    # Re-pack: rebuild bands from current y positions (order preserved).
    state = _GenState()
    bands: list[list[_Spec]] = []
    band_ys: list[float] = []
    for room in sorted(project.rooms, key=lambda r: (r.y, r.x)):
        spec = _Spec(id=room.id, name=room.name, type=room.type, width=room.width, depth=room.depth)
        if bands and abs(room.y - band_ys[-1]) < 1e-9:
            bands[-1].append(spec)
        else:
            bands.append([spec])
            band_ys.append(room.y)

    project.rooms = _pack_bands(bands, project.site.width, project.site.depth, state)
    doors, windows = _openings(project.rooms, project.site.width, state)
    project.doors = doors
    project.windows = windows

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

    summary = (
        f"Applied {len(applied)} change{'s' if len(applied) != 1 else ''}: "
        + "; ".join(applied[:4])
        + ("…" if len(applied) > 4 else ".")
    )
    return project, summary
