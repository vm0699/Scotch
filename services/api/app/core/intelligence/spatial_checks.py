"""Spatial quality checks — Phase 13.1.

Each function returns list[SpatialCheck]. Empty = pass.
Coordinate system: x=0 west, y=0 north (entrance edge).
"""

import math

from app.core.models import ArchitectureProject, Room
from app.core.intelligence.models import SpatialCheck

# Minimum recommended room areas by type (sq ft)
_MIN_AREA: dict[str, float] = {
    "bedroom": 100.0,
    "master_bedroom": 120.0,
    "bathroom": 35.0,
    "kitchen": 60.0,
    "living": 150.0,
    "dining": 80.0,
    "study": 60.0,
    "storage": 20.0,
    "parking": 100.0,
    "balcony": 20.0,
}

_BEDROOM_TYPES = {"bedroom", "master_bedroom", "master bedroom"}
_BATH_TYPES    = {"bathroom", "bath", "toilet", "wc"}
_SKIP_TYPES    = {"corridor", "hallway", "passage", "foyer", "lobby"}


def _area(r: Room) -> float:
    return r.width * r.depth


def _centroid(r: Room) -> tuple[float, float]:
    return r.x + r.width / 2, r.y + r.depth / 2


def _dist(a: Room, b: Room) -> float:
    ax, ay = _centroid(a)
    bx, by = _centroid(b)
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def _rtype(r: Room) -> str:
    return r.type.lower().replace(" ", "_")


def check_room_sizes(project: ArchitectureProject) -> list[SpatialCheck]:
    checks: list[SpatialCheck] = []
    for room in project.rooms:
        rt = _rtype(room)
        min_a = _MIN_AREA.get(rt)
        if min_a is None:
            continue
        area = _area(room)
        if area < min_a * 0.75:
            checks.append(SpatialCheck(
                rule_id="room_too_small",
                severity="warning",
                message=(
                    f"{room.name} is {area:.0f} ft² — well below the recommended "
                    f"{min_a:.0f} ft² minimum for a {room.type}."
                ),
                room_id=room.id,
            ))
        elif area < min_a:
            checks.append(SpatialCheck(
                rule_id="room_small",
                severity="info",
                message=(
                    f"{room.name} is {area:.0f} ft² — slightly under the "
                    f"recommended {min_a:.0f} ft² for a {room.type}."
                ),
                room_id=room.id,
            ))
    return checks


def check_bath_bedroom_proximity(project: ArchitectureProject) -> list[SpatialCheck]:
    bedrooms  = [r for r in project.rooms if _rtype(r) in _BEDROOM_TYPES]
    bathrooms = [r for r in project.rooms if _rtype(r) in _BATH_TYPES or "bath" in r.type.lower()]
    if not bathrooms:
        return []

    checks: list[SpatialCheck] = []
    MAX_DIST = 25.0  # ft
    for bed in bedrooms:
        nearest = min((_dist(bed, b) for b in bathrooms), default=None)
        if nearest is not None and nearest > MAX_DIST:
            checks.append(SpatialCheck(
                rule_id="bath_far_from_bedroom",
                severity="warning",
                message=(
                    f"{bed.name} is {nearest:.0f} ft from the nearest bathroom "
                    f"— consider relocating them closer."
                ),
                room_id=bed.id,
            ))
    return checks


def check_ventilation(project: ArchitectureProject) -> list[SpatialCheck]:
    """Flag habitable rooms with no window openings."""
    window_rooms = {w.room_id for w in project.windows}
    door_rooms   = {d.room_id for d in project.doors}
    checks: list[SpatialCheck] = []

    for room in project.rooms:
        if room.type.lower() in _SKIP_TYPES or _rtype(room) in {"storage", "parking"}:
            continue
        if room.id not in window_rooms and room.id in door_rooms:
            checks.append(SpatialCheck(
                rule_id="no_window",
                severity="info",
                message=(
                    f"{room.name} has no window — add one for natural light "
                    f"and cross-ventilation."
                ),
                room_id=room.id,
            ))
    return checks


def check_bathroom_missing(project: ArchitectureProject) -> list[SpatialCheck]:
    bedrooms  = [r for r in project.rooms if _rtype(r) in _BEDROOM_TYPES]
    bathrooms = [r for r in project.rooms if _rtype(r) in _BATH_TYPES or "bath" in r.type.lower()]

    if bedrooms and not bathrooms:
        return [SpatialCheck(
            rule_id="no_bathroom",
            severity="error",
            message="No bathroom found — at least one bathroom is required.",
        )]
    if len(bedrooms) >= 2 and len(bathrooms) == 0:
        return [SpatialCheck(
            rule_id="bath_ratio_low",
            severity="warning",
            message=(
                f"{len(bedrooms)} bedrooms share only {len(bathrooms)} bathroom(s) "
                f"— consider adding another bathroom."
            ),
        )]
    return []


def check_parking(project: ArchitectureProject) -> list[SpatialCheck]:
    bedrooms = [r for r in project.rooms if _rtype(r) in _BEDROOM_TYPES]
    parking  = [
        r for r in project.rooms
        if any(kw in r.type.lower() for kw in ("parking", "garage", "carport", "car"))
    ]
    if len(bedrooms) >= 2 and not parking:
        return [SpatialCheck(
            rule_id="parking_missing",
            severity="info",
            message=(
                f"No parking space for a {len(bedrooms)}-bedroom unit "
                f"— consider adding a car park or garage."
            ),
        )]
    return []


def check_coverage(project: ArchitectureProject) -> list[SpatialCheck]:
    site_area  = project.site.width * project.site.depth
    built_area = sum(_area(r) for r in project.rooms)
    coverage   = built_area / site_area * 100 if site_area > 0 else 0

    if coverage > 90:
        return [SpatialCheck(
            rule_id="overcoverage",
            severity="warning",
            message=(
                f"Built-up area covers {coverage:.0f}% of the site — "
                f"very little space left for setbacks, gardens, and circulation."
            ),
        )]
    if coverage < 20 and len(project.rooms) > 2:
        return [SpatialCheck(
            rule_id="undercoverage",
            severity="info",
            message=(
                f"Built-up area is only {coverage:.0f}% of the site — "
                f"the design has significant unused area."
            ),
        )]
    return []


def check_circulation(project: ArchitectureProject) -> list[SpatialCheck]:
    """Rooms with no door are inaccessible."""
    door_rooms = {d.room_id for d in project.doors}
    checks: list[SpatialCheck] = []
    for room in project.rooms:
        if room.type.lower() in _SKIP_TYPES:
            continue
        if room.id not in door_rooms:
            checks.append(SpatialCheck(
                rule_id="no_door_access",
                severity="error",
                message=f"{room.name} has no door — it cannot be accessed.",
                room_id=room.id,
            ))
    return checks


def run_spatial_checks(project: ArchitectureProject) -> list[SpatialCheck]:
    checks: list[SpatialCheck] = []
    checks.extend(check_room_sizes(project))
    checks.extend(check_bath_bedroom_proximity(project))
    checks.extend(check_ventilation(project))
    checks.extend(check_bathroom_missing(project))
    checks.extend(check_parking(project))
    checks.extend(check_coverage(project))
    checks.extend(check_circulation(project))
    return checks
