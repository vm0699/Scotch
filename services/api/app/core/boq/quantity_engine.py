"""Quantity engine — Phase 31.3.

Computes Bill of Quantities from an ArchitectureProject:
  - Floor tile/area per room
  - Wall tile (bathrooms, kitchens)
  - Skirting (perimeter minus door widths)
  - Paint area (walls + ceiling per room)
  - Door / window counts
  - Plumbing fixture counts (from MEP plan or room-type inference)
  - Electrical point counts (from MEP plan or room-type inference)
  - Furniture count

All quantities trace back to source_object_ids.
All areas in sqft. Rates applied from RateTable; rate=0 → missing-rate warning.
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict

from app.core.boq.rates import RateTable
from app.core.models.project import (
    ArchitectureProject,
    BOQItem,
    CategoryTotal,
    CostPlan,
    MaterialPlan,
    RoomFinish,
    TileSpec,
)

# Standard wall height assumption (feet)
_WALL_HEIGHT = 9.0
# Bathroom/kitchen: tile up to this height (feet)
_WALL_TILE_HEIGHT = 7.0

_BATHROOM_TYPES = {"bathroom", "master_bathroom", "toilet", "powder_room"}
_KITCHEN_TYPES = {"kitchen", "pantry"}
_WET_ROOM_TYPES = _BATHROOM_TYPES | _KITCHEN_TYPES

# Inference: fixture counts per room type when MEP is not generated
_INFERRED_PLUMBING: dict[str, dict[str, int]] = {
    "bathroom":        {"wc": 1, "basin": 1, "shower": 1},
    "master_bathroom": {"wc": 1, "basin": 1, "shower": 1},
    "toilet":          {"wc": 1, "basin": 1},
    "powder_room":     {"wc": 1, "basin": 1},
    "kitchen":         {"sink": 1},
    "pantry":          {"sink": 1},
}


def _uid() -> str:
    return str(uuid.uuid4())[:8]


def _make_item(
    category: str,
    description: str,
    source_ids: list[str],
    unit: str,
    quantity: float,
    rate: float,
    needs_review: bool = False,
) -> BOQItem:
    amount = round(quantity * rate, 2)
    return BOQItem(
        id=f"boq-{_uid()}",
        category=category,
        description=description,
        source_object_ids=source_ids,
        unit=unit,
        quantity=round(quantity, 3),
        rate=rate,
        amount=amount,
        confidence=0.85 if rate > 0 else 0.5,
        needs_review=needs_review or rate == 0.0,
    )


class QuantityEngine:
    """Generate CostPlan + update MaterialPlan from an ArchitectureProject."""

    def __init__(self, project: ArchitectureProject) -> None:
        self.project = project
        self.rates = RateTable.from_project(project.material_plan.editable_rates)

    # ── public ────────────────────────────────────────────────────────────────

    def build_boq(self) -> tuple[MaterialPlan, CostPlan]:
        """Return (updated MaterialPlan, CostPlan) without mutating the project."""
        items: list[BOQItem] = []
        assumptions: list[str] = []

        mat = self.project.material_plan

        # Seed default tile spec if none exist
        tile_specs = list(mat.tile_specs)
        if not tile_specs:
            tile_specs = [TileSpec(id="ts-default", label="Standard Tile 24×24″",
                                   size_w=24.0, size_h=24.0,
                                   rate_per_sqft=self.rates.get("flooring", "tile_supply"),
                                   wastage_pct=10.0)]
            assumptions.append("Default 24×24″ tile spec applied — adjust in material plan.")

        # Seed room finishes if missing
        room_finishes = {rf.room_id: rf for rf in mat.room_finishes}

        items += self._floor_items(tile_specs, room_finishes, assumptions)
        items += self._wall_tile_items(tile_specs, room_finishes, assumptions)
        items += self._skirting_items(assumptions)
        items += self._paint_items(assumptions)
        items += self._door_items(assumptions)
        items += self._window_items(assumptions)
        items += self._plumbing_items(assumptions)
        items += self._electrical_items(assumptions)
        items += self._furniture_items(assumptions)

        # Category totals
        cat_sums: dict[str, float] = defaultdict(float)
        missing_rates: list[str] = []
        for item in items:
            if item.rate == 0.0:
                missing_rates.append(f"{item.category}/{item.description}")
            else:
                cat_sums[item.category] += item.amount

        cat_totals = [CategoryTotal(category=k, total=round(v, 2))
                      for k, v in sorted(cat_sums.items())]
        grand = round(sum(c.total for c in cat_totals), 2)

        updated_mat = mat.model_copy(update={
            "tile_specs": tile_specs,
            "assumptions": assumptions,
            "generated": True,
            "stale": False,
        })
        cost = CostPlan(
            boq_items=items,
            category_totals=cat_totals,
            grand_total=grand,
            missing_rates=missing_rates,
            assumptions=assumptions,
            confidence=0.75 if missing_rates else 0.85,
            needs_review=True,
            generated=True,
        )
        return updated_mat, cost

    # ── private helpers ────────────────────────────────────────────────────────

    def _default_tile_spec(self, tile_specs: list[TileSpec]) -> TileSpec:
        return tile_specs[0] if tile_specs else TileSpec(
            id="ts-fallback", size_w=24.0, size_h=24.0)

    def _room_tile_spec(
        self,
        room_id: str,
        room_finishes: dict[str, RoomFinish],
        tile_specs: list[TileSpec],
    ) -> TileSpec:
        ts_id = None
        if room_id in room_finishes:
            ts_id = room_finishes[room_id].floor_tile_spec_id
        if ts_id:
            for ts in tile_specs:
                if ts.id == ts_id:
                    return ts
        return self._default_tile_spec(tile_specs)

    def _floor_items(
        self,
        tile_specs: list[TileSpec],
        room_finishes: dict[str, RoomFinish],
        assumptions: list[str],
    ) -> list[BOQItem]:
        items: list[BOQItem] = []
        for room in self.project.rooms:
            rf = room_finishes.get(room.id)
            mat_type = rf.floor_material if rf else "tile"
            area_sqft = room.width * room.depth
            ts = self._room_tile_spec(room.id, room_finishes, tile_specs)
            wastage = ts.wastage_pct / 100.0

            if mat_type in ("tile", ""):
                tile_area = math.ceil(area_sqft * (1 + wastage) * 10) / 10
                tile_rate = self.rates.get("flooring", "tile_supply")
                lay_rate  = self.rates.get("flooring", "tile_laying")
                items.append(_make_item(
                    "flooring", f"Floor tile supply — {room.name}",
                    [room.id], "sqft", tile_area, tile_rate))
                items.append(_make_item(
                    "flooring", f"Floor tile laying — {room.name}",
                    [room.id], "sqft", tile_area, lay_rate))
            elif mat_type == "marble":
                tile_area = math.ceil(area_sqft * (1 + wastage) * 10) / 10
                rate = self.rates.get("flooring", "marble_supply")
                lay  = self.rates.get("flooring", "marble_laying")
                items.append(_make_item("flooring", f"Marble supply — {room.name}",
                                        [room.id], "sqft", tile_area, rate))
                items.append(_make_item("flooring", f"Marble laying — {room.name}",
                                        [room.id], "sqft", tile_area, lay))
            elif mat_type == "wood":
                rate = self.rates.get("flooring", "wood_flooring")
                items.append(_make_item("flooring", f"Wood flooring — {room.name}",
                                        [room.id], "sqft", area_sqft, rate))
        return items

    def _wall_tile_items(
        self,
        tile_specs: list[TileSpec],
        room_finishes: dict[str, RoomFinish],
        assumptions: list[str],
    ) -> list[BOQItem]:
        items: list[BOQItem] = []
        for room in self.project.rooms:
            if room.type not in _WET_ROOM_TYPES:
                continue
            rf = room_finishes.get(room.id)
            if rf and rf.wall_material not in ("tile", ""):
                continue
            # Perimeter × tile height
            perimeter = 2 * (room.width + room.depth)
            # Deduct door openings in this room
            door_deduction = sum(
                d.width * _WALL_TILE_HEIGHT
                for d in self.project.doors if d.room_id == room.id
            )
            wall_area = max(0.0, perimeter * _WALL_TILE_HEIGHT - door_deduction)
            ts = self._room_tile_spec(room.id, room_finishes, tile_specs)
            wastage = ts.wastage_pct / 100.0
            tile_area = math.ceil(wall_area * (1 + wastage) * 10) / 10
            supply_rate = self.rates.get("wall_tile", "tile_supply")
            lay_rate    = self.rates.get("wall_tile", "tile_laying")
            items.append(_make_item("wall_tile", f"Wall tile supply — {room.name}",
                                    [room.id], "sqft", tile_area, supply_rate))
            items.append(_make_item("wall_tile", f"Wall tile laying — {room.name}",
                                    [room.id], "sqft", tile_area, lay_rate))
        return items

    def _skirting_items(self, assumptions: list[str]) -> list[BOQItem]:
        items: list[BOQItem] = []
        skirting_rate = self.rates.get("flooring", "tile_laying")  # proxy
        for room in self.project.rooms:
            perimeter = 2 * (room.width + room.depth)
            door_deduction = sum(
                d.width for d in self.project.doors if d.room_id == room.id
            )
            skirting = max(0.0, perimeter - door_deduction)
            items.append(_make_item(
                "flooring", f"Skirting — {room.name}",
                [room.id], "rft", skirting, skirting_rate))
        return items

    def _paint_items(self, assumptions: list[str]) -> list[BOQItem]:
        items: list[BOQItem] = []
        wall_rate    = self.rates.get("paint", "interior_paint")
        ceiling_rate = self.rates.get("paint", "ceiling_paint")
        for room in self.project.rooms:
            if room.type in _WET_ROOM_TYPES:
                continue  # wet rooms get tiles, not paint
            perimeter   = 2 * (room.width + room.depth)
            door_deduct = sum(d.width * 7.0 for d in self.project.doors if d.room_id == room.id)
            win_deduct  = sum(w.width * 4.0 for w in self.project.windows if w.room_id == room.id)
            wall_area   = max(0.0, perimeter * _WALL_HEIGHT - door_deduct - win_deduct)
            ceiling_area = room.width * room.depth
            items.append(_make_item("paint", f"Interior wall paint — {room.name}",
                                    [room.id], "sqft", wall_area, wall_rate))
            items.append(_make_item("paint", f"Ceiling paint — {room.name}",
                                    [room.id], "sqft", ceiling_area, ceiling_rate))
        return items

    def _door_items(self, assumptions: list[str]) -> list[BOQItem]:
        items: list[BOQItem] = []
        # Main door: first door in list (or any door with width > 3.5 ft)
        main_rate = self.rates.get("doors", "main_door")
        int_rate  = self.rates.get("doors", "interior_door")
        for i, door in enumerate(self.project.doors):
            is_main = i == 0
            rate    = main_rate if is_main else int_rate
            label   = "Main door" if is_main else "Interior door"
            items.append(_make_item("doors", f"{label} — {door.id}",
                                    [door.id], "nos", 1.0, rate))
        if not self.project.doors:
            assumptions.append("No doors found — check plan for door schedule.")
        return items

    def _window_items(self, assumptions: list[str]) -> list[BOQItem]:
        items: list[BOQItem] = []
        rate = self.rates.get("windows", "upvc_window")
        for window in self.project.windows:
            items.append(_make_item("windows", f"UPVC window — {window.id}",
                                    [window.id], "nos", 1.0, rate))
        if not self.project.windows:
            assumptions.append("No windows found — check plan for window schedule.")
        return items

    def _plumbing_items(self, assumptions: list[str]) -> list[BOQItem]:
        items: list[BOQItem] = []
        mep = self.project.mep_plan

        if mep.generated:
            # Count fixtures from MEP plan
            fixture_counts: dict[str, int] = defaultdict(int)
            src_map: dict[str, list[str]] = defaultdict(list)
            for pt in mep.plumbing.points:
                fixture_counts[pt.kind] += 1
                src_map[pt.kind].append(pt.id)
            for kind, count in fixture_counts.items():
                rate = self.rates.get("plumbing", kind)
                items.append(_make_item("plumbing", f"Plumbing fixture — {kind}",
                                        src_map[kind], "nos", float(count), rate))
        else:
            assumptions.append("MEP not generated — plumbing quantities inferred from room types.")
            for room in self.project.rooms:
                fixtures = _INFERRED_PLUMBING.get(room.type, {})
                for kind, qty in fixtures.items():
                    rate = self.rates.get("plumbing", kind)
                    items.append(_make_item("plumbing", f"{kind.upper()} — {room.name}",
                                            [room.id], "nos", float(qty), rate,
                                            needs_review=True))
        return items

    def _electrical_items(self, assumptions: list[str]) -> list[BOQItem]:
        items: list[BOQItem] = []
        mep = self.project.mep_plan

        if mep.generated:
            from collections import Counter
            counts: Counter[str] = Counter()
            src_map: dict[str, list[str]] = defaultdict(list)
            for pt in mep.electrical.points:
                counts[pt.kind] += 1
                src_map[pt.kind].append(pt.id)
            for pt in mep.lighting.points:
                counts[pt.kind] += 1
                src_map[pt.kind].append(pt.id)
            for pt in mep.ac.points:
                counts[pt.kind] += 1
                src_map[pt.kind].append(pt.id)
            kind_map = {"switch": "switch_point", "socket": "socket_point",
                        "light": "light_point", "ac_unit": "ac_point"}
            for kind, count in counts.items():
                item_key = kind_map.get(kind, kind)
                rate = self.rates.get("electrical", item_key)
                items.append(_make_item("electrical", f"Electrical — {kind}",
                                        src_map[kind], "nos", float(count), rate))
        else:
            assumptions.append("MEP not generated — electrical quantities inferred (1 switch+light per room, 2 sockets per room).")
            for room in self.project.rooms:
                sw_rate = self.rates.get("electrical", "switch_point")
                lt_rate = self.rates.get("electrical", "light_point")
                sk_rate = self.rates.get("electrical", "socket_point")
                items.append(_make_item("electrical", f"Switch — {room.name}",
                                        [room.id], "nos", 1.0, sw_rate))
                items.append(_make_item("electrical", f"Light — {room.name}",
                                        [room.id], "nos", 1.0, lt_rate))
                items.append(_make_item("electrical", f"Sockets — {room.name}",
                                        [room.id], "nos", 2.0, sk_rate))
        return items

    def _furniture_items(self, assumptions: list[str]) -> list[BOQItem]:
        # Furniture BOQ is informational — rate=0 (manual entry needed)
        items: list[BOQItem] = []
        if self.project.furniture:
            counts: dict[str, int] = defaultdict(int)
            src: dict[str, list[str]] = defaultdict(list)
            for fi in self.project.furniture:
                counts[fi.type] += 1
                src[fi.type].append(fi.id)
            for ftype, count in counts.items():
                items.append(_make_item("furniture", f"Furniture — {ftype}",
                                        src[ftype], "nos", float(count), 0.0,
                                        needs_review=True))
            if items:
                assumptions.append("Furniture rates not set — enter manually in BOQ editor.")
        return items
