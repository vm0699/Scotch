"""Vastu Shastra rule engine — Phase 13.3.

Coordinate system: x=0 = west, x=site_w = east,
                   y=0 = north (entrance), y=site_d = south.
Thresholds split each axis at 0.4 / 0.6 to define 8 directions + center.
"""

from app.core.models import ArchitectureProject, Room
from app.core.intelligence.models import VastuSuggestion


def _compass(room: Room, site_w: float, site_d: float) -> str:
    rel_x = (room.x + room.width / 2) / site_w   # 0=west 1=east
    rel_y = (room.y + room.depth / 2) / site_d    # 0=north 1=south

    east  = rel_x > 0.6
    west  = rel_x < 0.4
    north = rel_y < 0.4
    south = rel_y > 0.6

    if east  and north: return "northeast"
    if east  and south: return "southeast"
    if west  and south: return "southwest"
    if west  and north: return "northwest"
    if north:           return "north"
    if south:           return "south"
    if east:            return "east"
    if west:            return "west"
    return "center"


# (room_type_keywords, good_directions, bad_directions, ok_msg, bad_msg)
# ok_msg = None means no positive feedback for that type (e.g. bathrooms)
_RULES: list[tuple[set[str], set[str], set[str], str | None, str]] = [
    (
        {"kitchen"},
        {"southeast", "east"},
        {"northeast", "southwest", "north"},
        "Kitchen in the {dir} (Agni direction) is auspicious per Vastu.",
        "Kitchen in the {dir} conflicts with Vastu — southeast or east is preferred.",
    ),
    (
        {"master_bedroom", "master bedroom"},
        {"southwest", "south"},
        {"northeast", "east"},
        "Master bedroom in the {dir} follows Vastu — promotes stability and rest.",
        "Master bedroom in the {dir} is inauspicious per Vastu — southwest or south is preferred.",
    ),
    (
        {"bathroom", "toilet", "wc", "bath"},
        {"northwest", "southeast", "west"},
        {"northeast", "north"},
        None,
        "Bathroom in the {dir} is highly inauspicious per Vastu — avoid the northeast corner.",
    ),
    (
        {"living", "drawing", "hall", "lounge"},
        {"north", "east", "northeast"},
        {"south", "southwest"},
        "Living room in the {dir} promotes positive energy per Vastu.",
        "Living room in the {dir} may conflict with Vastu — north or east is preferred.",
    ),
    (
        {"study", "office", "library", "work"},
        {"east", "northeast", "north"},
        {"southwest"},
        "Study in the {dir} supports concentration per Vastu.",
        "Study in the {dir} may reduce focus per Vastu — east or north is preferred.",
    ),
    (
        {"puja", "prayer", "meditation", "temple", "mandir"},
        {"northeast"},
        {"south", "southwest", "southeast"},
        "Puja room in the northeast (Ishan corner) is the ideal Vastu placement.",
        "Puja room in the {dir} is not ideal per Vastu — the northeast is the sacred corner.",
    ),
    (
        {"dining"},
        {"west", "east"},
        {"south"},
        "Dining room in the {dir} is a favourable Vastu placement.",
        "Dining room in the {dir} may not be ideal per Vastu — east or west is preferred.",
    ),
]


def run_vastu_checks(project: ArchitectureProject) -> list[VastuSuggestion]:
    suggestions: list[VastuSuggestion] = []
    site_w = project.site.width
    site_d = project.site.depth

    for room in project.rooms:
        rtype     = room.type.lower().replace("_", " ").strip()
        direction = _compass(room, site_w, site_d)

        for kw_set, good, bad, ok_msg, bad_msg in _RULES:
            matched = rtype in kw_set or any(kw in rtype for kw in kw_set)
            if not matched:
                continue

            if direction in bad:
                suggestions.append(VastuSuggestion(
                    rule_id=f"vastu_{rtype.replace(' ', '_')}_{direction}",
                    severity="warning",
                    message=bad_msg.format(dir=direction),
                    room_id=room.id,
                    direction=direction,
                ))
            elif direction in good and ok_msg:
                suggestions.append(VastuSuggestion(
                    rule_id=f"vastu_{rtype.replace(' ', '_')}_{direction}_ok",
                    severity="info",
                    message=ok_msg.format(dir=direction),
                    room_id=room.id,
                    direction=direction,
                ))

    # Entrance (site orientation) check
    orientation = project.site.orientation
    if orientation in ("north", "east"):
        suggestions.append(VastuSuggestion(
            rule_id="vastu_entrance_good",
            severity="info",
            message=f"Entrance faces {orientation} — an auspicious direction per Vastu Shastra.",
        ))
    elif orientation in ("south", "west"):
        suggestions.append(VastuSuggestion(
            rule_id="vastu_entrance_bad",
            severity="warning",
            message=(
                f"Entrance faces {orientation} — Vastu recommends north- or "
                f"east-facing entrances for prosperity."
            ),
        ))

    return suggestions
