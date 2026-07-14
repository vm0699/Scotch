"""Default room sizes (feet) for the deterministic layout generator.

Sizes are (width, depth) as drawn on the plan. Locked in the Phase 0
questionnaire; tune here, not in the generator.
"""

ROOM_DEFAULTS: dict[str, tuple[float, float]] = {
    "living": (14, 12),
    "kitchen": (8, 10),
    "kitchenette": (6, 8),
    "bedroom": (11, 12),
    "master_bedroom": (12, 13),
    "bathroom": (5, 8),
    "balcony": (6, 10),
    "parking": (10, 15),
    "dining": (8, 10),
    "study": (8, 10),
    "storage": (5, 6),
    "studio_room": (14, 16),
    "seating": (10, 12),
    "foyer": (6, 6),
    # Cafe program (seating is sized to the site by the generator).
    "cafe_counter": (8, 10),
    "cafe_kitchen": (8, 10),
    "restroom": (5, 6),
    # Office fallback program (detailed office logic arrives later).
    "open_plan": (20, 20),
}

DEFAULT_SITE = (30.0, 50.0)
DEFAULT_ORIENTATION = "east"
DEFAULT_FLOOR_HEIGHT = 10.0
DEFAULT_STYLE = "modern minimal"


def default_size(room_type: str) -> tuple[float, float]:
    return ROOM_DEFAULTS[room_type]
