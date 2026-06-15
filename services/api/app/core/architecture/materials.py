"""Stage 17.2 — Default material assignment for ArchitectureProject.

Produces one Material record per element class (wall, floor, roof, glass,
door, exterior) plus one per room type present in the project, with design-
intent hints (base_color, roughness, metallic) that render engines can pick
up via object name → material mapping.

Called by generate_floorplan() and create_sample_project() so all generated
projects arrive with a full material list.
"""

from app.core.models import ArchitectureProject, Material

# ── Element-class materials ───────────────────────────────────────────────────
# Keyed by target string; each maps to one Material in every project.

_ELEMENT_MATS: list[dict] = [
    {
        "id": "mat-wall", "name": "Scotch_Wall", "target": "wall",
        "finish": "matte paint", "base_color": "#F5F4F2",
        "roughness": 0.70, "metallic": 0.0,
    },
    {
        "id": "mat-floor", "name": "Scotch_Floor", "target": "floor",
        "finish": "polished stone", "base_color": "#E8E3DC",
        "roughness": 0.50, "metallic": 0.0,
    },
    {
        "id": "mat-roof", "name": "Scotch_Roof", "target": "roof",
        "finish": "concrete", "base_color": "#C8C4BE",
        "roughness": 0.85, "metallic": 0.0,
    },
    {
        "id": "mat-glass", "name": "Scotch_Glass", "target": "glass",
        "finish": "clear glass", "base_color": "#A8CADF",
        "roughness": 0.05, "metallic": 0.15,
    },
    {
        "id": "mat-door", "name": "Scotch_Door", "target": "door",
        "finish": "wood", "base_color": "#C4A882",
        "roughness": 0.65, "metallic": 0.0,
    },
    {
        "id": "mat-exterior", "name": "Scotch_Exterior", "target": "exterior",
        "finish": "render", "base_color": "#EDEAE4",
        "roughness": 0.75, "metallic": 0.0,
    },
    {
        "id": "mat-ground", "name": "Scotch_Ground", "target": "ground",
        "finish": "landscaping", "base_color": "#D8D5CC",
        "roughness": 0.90, "metallic": 0.0,
    },
]

# ── Room-type floor/interior materials ────────────────────────────────────────
# Keyed by normalised room type string. Added only when that room type is
# present in the project so the material list stays compact.

_ROOM_TYPE_MATS: dict[str, dict] = {
    "living":         {"id": "mat-room-living",   "name": "Scotch_Room_Living",   "base_color": "#EDE8DC", "roughness": 0.55},
    "dining":         {"id": "mat-room-dining",   "name": "Scotch_Room_Dining",   "base_color": "#EDE9DF", "roughness": 0.55},
    "kitchen":        {"id": "mat-room-kitchen",  "name": "Scotch_Room_Kitchen",  "base_color": "#EEEADE", "roughness": 0.30},
    "master_bedroom": {"id": "mat-room-master",   "name": "Scotch_Room_Master",   "base_color": "#E5DDD8", "roughness": 0.60},
    "bedroom":        {"id": "mat-room-bedroom",  "name": "Scotch_Room_Bedroom",  "base_color": "#EAE0DC", "roughness": 0.60},
    "bathroom":       {"id": "mat-room-bath",     "name": "Scotch_Room_Bath",     "base_color": "#DDE8EA", "roughness": 0.20},
    "balcony":        {"id": "mat-room-balcony",  "name": "Scotch_Room_Balcony",  "base_color": "#E2E5DE", "roughness": 0.65},
    "parking":        {"id": "mat-room-parking",  "name": "Scotch_Room_Parking",  "base_color": "#D8D8D5", "roughness": 0.80},
    "study":          {"id": "mat-room-study",    "name": "Scotch_Room_Study",    "base_color": "#E9E6E0", "roughness": 0.60},
    "storage":        {"id": "mat-room-storage",  "name": "Scotch_Room_Storage",  "base_color": "#E0DDD8", "roughness": 0.70},
    "foyer":          {"id": "mat-room-foyer",    "name": "Scotch_Room_Foyer",    "base_color": "#EAE7E1", "roughness": 0.50},
    "corridor":       {"id": "mat-room-corridor", "name": "Scotch_Room_Corridor", "base_color": "#ECEBE6", "roughness": 0.50},
    "seating":        {"id": "mat-room-seating",  "name": "Scotch_Room_Seating",  "base_color": "#EDE8DC", "roughness": 0.55},
}


def assign_default_materials(project: ArchitectureProject) -> ArchitectureProject:
    """Return the project with a full default material list.

    Idempotent — replaces any existing materials. Always produces at least
    the 7 element-class materials; adds room-type materials for each unique
    room type present.
    """
    mats: list[Material] = []

    # 1. Element-class materials (always present)
    for m in _ELEMENT_MATS:
        mats.append(Material(**m))  # type: ignore[arg-type]

    # 2. Room-type floor/interior materials (only for types in this project)
    seen_types: set[str] = set()
    for room in project.rooms:
        t = room.type.lower().replace(" ", "_")
        if t in seen_types:
            continue
        seen_types.add(t)
        if t in _ROOM_TYPE_MATS:
            md = _ROOM_TYPE_MATS[t]
            mats.append(Material(
                id=md["id"],
                name=md["name"],
                target=f"room:{t}",
                finish="interior paint",
                base_color=md["base_color"],
                roughness=md["roughness"],
                metallic=0.0,
            ))

    return project.model_copy(update={"materials": mats})
