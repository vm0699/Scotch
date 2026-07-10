"""Per-room-type furniture template library (Phase 26.2).

Each ROOM_FURNITURE entry maps a room type to an ordered list of FurnitureSpec
items. The placer works through each spec in priority order; items are placed
first-come-first-served and later items fill around earlier ones.

Sizes are in feet. Heights are for 3D rendering only.

Wall conventions (matching the plan model):
  "north"  — top edge (entrance side, y = room.y)
  "south"  — bottom edge (y = room.y + room.depth)
  "east"   — right edge  (x = room.x + room.width)
  "west"   — left edge   (x = room.x)
  "center" — centred in the room
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field


@dataclass
class FurnitureSpec:
    """Specification for one furniture item in a room template.

    width / depth are the canonical item dimensions assuming rotation = 0°
    (item faces south when placed against the north wall).  The placer
    computes the placed footprint — swapping width/depth for 90°/270° — and
    stores it on FurnitureItem so rendering never needs to rotate coordinates.

    wall       — which room edge to place against, or "center".
    clearance  — minimum free space perpendicular to the front of the item
                 (checked inside room bounds, not into walls).
    x_align    — "center" | "left" | "right" — along-wall horizontal alignment.
    x_gap      — gap from the wall's near edge for left/right alignments (ft).
    priority   — placement order; 1 = placed first (gets the best spot).
    min_room_area — room must be at least this many ft² for the item to appear.
    min_room_w    — room must be at least this wide (ft).
    min_room_d    — room must be at least this deep (ft).
    """

    type: str
    label: str
    width: float           # ft, along X when rotation = 0°
    depth: float           # ft, along Y when rotation = 0°
    height: float          # ft, 3D block height
    wall: str              # "north"|"south"|"east"|"west"|"center"
    clearance: float       # ft, min free space in front
    priority: int = 5
    x_align: str = "center"  # "center"|"left"|"right"
    x_gap: float = 0.4        # ft gap for left/right alignment
    min_room_area: float = 0.0
    min_room_w: float = 0.0
    min_room_d: float = 0.0


# ── Per-room-type templates ───────────────────────────────────────────────────

ROOM_FURNITURE: dict[str, list[FurnitureSpec]] = {

    # ── Standard bedroom ──────────────────────────────────────────────────────
    "bedroom": [
        FurnitureSpec("double_bed",  "Bed",          5.5, 6.5, 2.0,  "south", 3.5, priority=1),
        FurnitureSpec("wardrobe",    "Wardrobe",      4.5, 2.0, 7.0,  "north", 2.5, priority=2, min_room_area=88),
        FurnitureSpec("bedside_l",   "Bedside Table", 1.5, 1.5, 2.0,  "south", 0.0, priority=3,
                      x_align="left",  x_gap=0.3),
        FurnitureSpec("bedside_r",   "Bedside Table", 1.5, 1.5, 2.0,  "south", 0.0, priority=3,
                      x_align="right", x_gap=0.3),
        FurnitureSpec("dresser",     "Dresser",       3.5, 1.5, 4.5,  "east",  2.5, priority=5, min_room_area=100),
    ],

    # ── Master bedroom ────────────────────────────────────────────────────────
    "master_bedroom": [
        FurnitureSpec("king_bed",       "King Bed",      6.5, 7.0, 2.2,  "south", 3.5, priority=1),
        FurnitureSpec("wardrobe",       "Wardrobe",      5.5, 2.0, 7.0,  "north", 2.5, priority=2),
        FurnitureSpec("wardrobe_2",     "Wardrobe",      4.0, 2.0, 7.0,  "west",  2.5, priority=3, min_room_area=130),
        FurnitureSpec("bedside_l",      "Bedside Table", 1.5, 1.5, 2.0,  "south", 0.0, priority=4,
                      x_align="left",  x_gap=0.3),
        FurnitureSpec("bedside_r",      "Bedside Table", 1.5, 1.5, 2.0,  "south", 0.0, priority=4,
                      x_align="right", x_gap=0.3),
        FurnitureSpec("dressing_table", "Dressing Table",4.0, 1.5, 4.5,  "east",  3.0, priority=5, min_room_area=130),
    ],

    # ── Living room ───────────────────────────────────────────────────────────
    "living": [
        FurnitureSpec("tv_unit",      "TV Unit",      6.0, 1.5, 1.5,  "north", 4.0, priority=1),
        FurnitureSpec("sofa",         "Sofa",         7.0, 3.0, 3.0,  "south", 2.5, priority=2),
        FurnitureSpec("coffee_table", "Coffee Table", 4.0, 2.0, 1.5,  "center",2.5, priority=3),
        FurnitureSpec("armchair_l",   "Armchair",     3.0, 3.0, 3.0,  "west",  2.5, priority=4, min_room_area=130),
        FurnitureSpec("armchair_r",   "Armchair",     3.0, 3.0, 3.0,  "east",  2.5, priority=4, min_room_area=130),
        FurnitureSpec("side_table",   "Side Table",   1.5, 1.5, 2.0,  "east",  1.0, priority=6, min_room_area=150,
                      x_align="right", x_gap=0.3),
    ],

    # ── Open seating / studio living ──────────────────────────────────────────
    "seating": [
        FurnitureSpec("tv_unit",      "TV Unit",      6.0, 1.5, 1.5,  "north", 4.0, priority=1),
        FurnitureSpec("sofa",         "Sofa",         7.0, 3.0, 3.0,  "south", 2.5, priority=2),
        FurnitureSpec("coffee_table", "Coffee Table", 4.0, 2.0, 1.5,  "center",2.5, priority=3),
        FurnitureSpec("armchair_l",   "Armchair",     3.0, 3.0, 3.0,  "west",  2.5, priority=5, min_room_area=110),
    ],

    # ── Dining room ───────────────────────────────────────────────────────────
    "dining": [
        FurnitureSpec("dining_table", "Dining Table", 5.0, 3.0, 2.5,  "center",2.5, priority=1),
        # Chairs: placed by special chair logic around the table
        FurnitureSpec("chair_n1",    "Chair",         1.5, 1.5, 3.0,  "center",0.0, priority=7),
        FurnitureSpec("chair_n2",    "Chair",         1.5, 1.5, 3.0,  "center",0.0, priority=7),
        FurnitureSpec("chair_s1",    "Chair",         1.5, 1.5, 3.0,  "center",0.0, priority=7),
        FurnitureSpec("chair_s2",    "Chair",         1.5, 1.5, 3.0,  "center",0.0, priority=7),
        FurnitureSpec("chair_e",     "Chair",         1.5, 1.5, 3.0,  "center",0.0, priority=8, min_room_area=80),
        FurnitureSpec("chair_w",     "Chair",         1.5, 1.5, 3.0,  "center",0.0, priority=8, min_room_area=80),
        FurnitureSpec("sideboard",   "Sideboard",     5.0, 1.5, 3.5,  "east",  2.0, priority=6, min_room_area=100),
    ],

    # ── Kitchen ───────────────────────────────────────────────────────────────
    "kitchen": [
        # counter_n width is stretched to room width by the placer
        FurnitureSpec("counter_n",   "Counter",       8.0, 2.0, 3.0,  "north", 4.0, priority=1),
        FurnitureSpec("counter_w",   "Counter",       2.0, 6.0, 3.0,  "west",  4.0, priority=2, min_room_area=80),
        FurnitureSpec("refrigerator","Refrigerator",  2.5, 2.5, 5.5,  "north", 1.5, priority=3,
                      x_align="right", x_gap=0.1),
        FurnitureSpec("cooktop",     "Cooktop",       2.0, 2.0, 3.0,  "north", 2.5, priority=4),
    ],

    # ── Kitchenette ───────────────────────────────────────────────────────────
    "kitchenette": [
        FurnitureSpec("counter_n",   "Counter",       6.0, 1.5, 3.0,  "north", 3.0, priority=1),
        FurnitureSpec("refrigerator","Refrigerator",  2.0, 2.0, 5.5,  "north", 1.5, priority=2,
                      x_align="right", x_gap=0.1),
    ],

    # ── Study / home office ───────────────────────────────────────────────────
    "study": [
        FurnitureSpec("desk",         "Desk",         5.0, 2.5, 2.5,  "north", 3.0, priority=1),
        FurnitureSpec("office_chair", "Chair",        2.0, 2.0, 3.5,  "north", 1.5, priority=2),
        FurnitureSpec("bookshelf_e",  "Bookshelf",    3.0, 1.0, 7.0,  "east",  2.0, priority=3, min_room_area=60),
        FurnitureSpec("bookshelf_w",  "Bookshelf",    3.0, 1.0, 7.0,  "west",  2.0, priority=4, min_room_area=80),
    ],

    # ── Bathroom (standard) ───────────────────────────────────────────────────
    "bathroom": [
        FurnitureSpec("wc",     "WC",     1.5, 2.5, 2.5,  "north", 2.0, priority=1, x_align="left"),
        FurnitureSpec("basin",  "Basin",  2.0, 1.5, 3.0,  "east",  2.0, priority=2),
        FurnitureSpec("shower", "Shower", 3.0, 3.0, 7.0,  "south", 0.5, priority=3, x_align="right"),
    ],

    # ── Foyer / entry ─────────────────────────────────────────────────────────
    "foyer": [
        FurnitureSpec("shoe_rack",     "Shoe Rack",  3.0, 1.0, 3.5,  "west",  2.0, priority=2),
        FurnitureSpec("console_table", "Console",    3.0, 1.0, 3.0,  "north", 2.5, priority=3, min_room_area=40),
    ],

    # ── Balcony ───────────────────────────────────────────────────────────────
    "balcony": [
        FurnitureSpec("outdoor_chair_l", "Chair", 2.0, 2.0, 3.0, "south", 1.5, priority=2,
                      x_align="left",  x_gap=0.5),
        FurnitureSpec("outdoor_chair_r", "Chair", 2.0, 2.0, 3.0, "south", 1.5, priority=2,
                      x_align="right", x_gap=0.5),
        FurnitureSpec("outdoor_table",   "Table", 2.5, 2.5, 2.5, "center",1.5, priority=3, min_room_area=40),
    ],

    # ── Storage / utility ─────────────────────────────────────────────────────
    "storage": [
        FurnitureSpec("shelving_n", "Shelving", 4.0, 1.0, 7.0, "north", 2.5, priority=3),
        FurnitureSpec("shelving_e", "Shelving", 4.0, 1.0, 7.0, "east",  2.5, priority=4, min_room_area=30),
    ],

    # ── Restroom ─────────────────────────────────────────────────────────────
    "restroom": [
        FurnitureSpec("wc",    "WC",    1.5, 2.5, 2.5, "north", 2.0, priority=1, x_align="left"),
        FurnitureSpec("basin", "Basin", 2.0, 1.5, 3.0, "east",  2.0, priority=2),
    ],

    # ── Corridor / parking — no furniture ────────────────────────────────────
    "corridor": [],
    "parking":  [],
    "stair":    [],
}

# ── 3D height lookup (ft) ─────────────────────────────────────────────────────

FURNITURE_HEIGHTS: dict[str, float] = {
    "double_bed": 2.0, "king_bed": 2.2, "single_bed": 2.0,
    "wardrobe": 7.0, "wardrobe_2": 7.0, "dresser": 4.5, "dressing_table": 4.5,
    "bedside_l": 2.0, "bedside_r": 2.0,
    "sofa": 3.0, "armchair_l": 3.0, "armchair_r": 3.0, "armchair": 3.0,
    "coffee_table": 1.5, "side_table": 2.0, "tv_unit": 1.5,
    "dining_table": 2.5, "sideboard": 3.5,
    "chair_n1": 3.0, "chair_n2": 3.0, "chair_s1": 3.0, "chair_s2": 3.0,
    "chair_e": 3.0, "chair_w": 3.0,
    "counter_n": 3.0, "counter_w": 3.0, "counter_e": 3.0, "counter_s": 3.0,
    "refrigerator": 5.5, "cooktop": 3.0,
    "desk": 2.5, "office_chair": 3.5,
    "bookshelf_e": 7.0, "bookshelf_w": 7.0,
    "wc": 2.5, "basin": 3.0, "shower": 7.0, "bathtub": 1.5,
    "outdoor_chair_l": 3.0, "outdoor_chair_r": 3.0, "outdoor_table": 2.5,
    "console_table": 3.0, "shoe_rack": 3.5,
    "shelving_n": 7.0, "shelving_e": 7.0,
}

_DEFAULT_HEIGHT = 2.5


def furniture_height(ftype: str) -> float:
    return FURNITURE_HEIGHTS.get(ftype, _DEFAULT_HEIGHT)


def get_template(room_type: str, room_w: float, room_d: float) -> list[FurnitureSpec]:
    """Return the size-filtered template for *room_type*."""
    area = room_w * room_d
    specs = ROOM_FURNITURE.get(room_type.lower(), [])
    return [
        s for s in specs
        if s.min_room_area <= area
        and s.min_room_w <= room_w
        and s.min_room_d <= room_d
    ]
