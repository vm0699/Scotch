"""Semantic validation for ArchitectureProject.

One reusable module for every path that produces or mutates a project:
generation (Phase 5), editing/regeneration (Phase 6), and exports (Phase 7).
Schema-level constraints (positive dimensions, literal enums) live on the
Pydantic models; this validator covers cross-entity rules and produces
advisory warnings for imperfect-but-valid layouts.
"""

from itertools import combinations

from pydantic import BaseModel

from app.core.models import ArchitectureProject, ProjectWarning, Room

# A layout qualifies as "mostly open" when unbuilt site area exceeds this share.
OPEN_AREA_WARNING_RATIO = 0.35


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[ProjectWarning] = []


def _wall_length(room: Room, wall: str) -> float:
    return room.width if wall in ("north", "south") else room.depth


def _rooms_overlap(a: Room, b: Room) -> bool:
    return (
        a.x < b.x + b.width
        and b.x < a.x + a.width
        and a.y < b.y + b.depth
        and b.y < a.y + a.depth
    )


def validate_project(project: ArchitectureProject) -> ValidationResult:
    errors: list[str] = []
    warnings: list[ProjectWarning] = []

    # Unique room ids.
    seen: set[str] = set()
    for room in project.rooms:
        if room.id in seen:
            errors.append(f"Duplicate room id '{room.id}'")
        seen.add(room.id)
    rooms_by_id = {room.id: room for room in project.rooms}

    # Rooms inside the site boundary.
    for room in project.rooms:
        if (
            room.x + room.width > project.site.width + 1e-9
            or room.y + room.depth > project.site.depth + 1e-9
        ):
            errors.append(
                f"Room '{room.id}' extends outside the {project.site.width}x"
                f"{project.site.depth} site boundary"
            )

    # Level references stay within the building's floor count.
    for room in project.rooms:
        if room.level >= project.building.floors:
            errors.append(
                f"Room '{room.id}' references level {room.level} but the "
                f"building has {project.building.floors} floor(s)"
            )
    for level in project.levels:
        if level.index >= project.building.floors:
            errors.append(
                f"Level '{level.name}' index {level.index} exceeds the "
                f"building's floor count"
            )

    # Openings reference existing rooms and fit on their wall.
    for opening, kind in [(d, "Door") for d in project.doors] + [
        (w, "Window") for w in project.windows
    ]:
        room = rooms_by_id.get(opening.room_id)
        if room is None:
            errors.append(
                f"{kind} '{opening.id}' references unknown room "
                f"'{opening.room_id}'"
            )
            continue
        wall_len = _wall_length(room, opening.wall)
        if opening.offset + opening.width > wall_len + 1e-9:
            warnings.append(
                ProjectWarning(
                    id=f"warn-fit-{opening.id}",
                    severity="warning",
                    message=(
                        f"{kind} '{opening.id}' ({opening.width} wide at offset "
                        f"{opening.offset}) does not fit the {wall_len}-long "
                        f"{opening.wall} wall of room '{room.id}'"
                    ),
                )
            )

    # Overlapping rooms on the same level are almost always a layout bug.
    for a, b in combinations(project.rooms, 2):
        if a.level == b.level and _rooms_overlap(a, b):
            warnings.append(
                ProjectWarning(
                    id=f"warn-overlap-{a.id}-{b.id}",
                    severity="warning",
                    message=f"Rooms '{a.id}' and '{b.id}' overlap on level {a.level}",
                )
            )

    # Advisory: large unbuilt share of the site.
    site_area = project.site.width * project.site.depth
    ground_rooms = [r for r in project.rooms if r.level == 0]
    built = sum(r.width * r.depth for r in ground_rooms)
    if ground_rooms and site_area > 0 and (site_area - built) / site_area > OPEN_AREA_WARNING_RATIO:
        open_pct = round((site_area - built) / site_area * 100)
        warnings.append(
            ProjectWarning(
                id="warn-open-area",
                severity="info",
                message=(
                    f"{open_pct}% of the site is unbuilt — consider garden, "
                    f"parking, or future expansion"
                ),
            )
        )

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)
