"""Area calculator — Phase 13.2."""

from app.core.models import ArchitectureProject
from app.core.intelligence.models import AreaSummary, RoomAreaEntry

_CARPET_RATIO = 0.85  # standard deduction for wall thickness


def compute_areas(project: ArchitectureProject) -> AreaSummary:
    site_area = project.site.width * project.site.depth
    total_built = 0.0
    total_carpet = 0.0
    room_entries: list[RoomAreaEntry] = []

    for room in project.rooms:
        gross = room.width * room.depth
        carpet = gross * _CARPET_RATIO
        total_built += gross
        total_carpet += carpet
        room_entries.append(RoomAreaEntry(
            room_id=room.id,
            room_name=room.name,
            room_type=room.type,
            gross_area=round(gross, 2),
            carpet_area=round(carpet, 2),
        ))

    coverage = (total_built / site_area * 100) if site_area > 0 else 0.0
    efficiency = (total_carpet / total_built * 100) if total_built > 0 else 0.0

    return AreaSummary(
        site_area=round(site_area, 2),
        built_up_area=round(total_built, 2),
        carpet_area=round(total_carpet, 2),
        circulation_area=round(max(0.0, site_area - total_built), 2),
        coverage_ratio=round(coverage, 1),
        floor_efficiency=round(efficiency, 1),
        rooms=room_entries,
    )
