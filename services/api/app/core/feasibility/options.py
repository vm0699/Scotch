"""Phase 40 — Feasibility option generator.

Produces compact / balanced / spacious / future_expansion / rental_friendly
variants given site metrics. All figures advisory.
"""

from __future__ import annotations

import math

from app.core.models.project import FeasibilityOption


# Approximate unit sizes (sq ft built-up, including circulation)
_UNIT_SQFT = {
    "studio": 250,
    "1BHK": 450,
    "2BHK": 850,
    "3BHK": 1300,
    "4BHK": 1800,
}


def _units_that_fit(buildable_area: float, unit_sqft: int, parking_area: float = 0) -> int:
    available = buildable_area - parking_area
    return max(1, math.floor(available / unit_sqft))


class OptionGenerator:
    """Generate feasibility options for a given site envelope."""

    def generate(
        self,
        site_area: float,
        usable_footprint: float,
        buildable_area: float,
        max_floors: int,
        parking_slots: int,
    ) -> list[FeasibilityOption]:
        parking_area = parking_slots * 120.0  # ~120 sq ft per car slot
        net_buildable = max(0, buildable_area - parking_area)

        options: list[FeasibilityOption] = []

        # 1. Compact — 1BHK/studio units, maximise count
        count_1bhk = _units_that_fit(net_buildable, _UNIT_SQFT["1BHK"])
        options.append(FeasibilityOption(
            name="compact",
            label="Compact — maximize unit count",
            unit_count=count_1bhk,
            unit_type="1BHK",
            unit_sizes_sqft=[float(_UNIT_SQFT["1BHK"])] * count_1bhk,
            coverage_pct=round(usable_footprint / site_area * 100, 1),
            built_up_area=round(min(net_buildable, count_1bhk * _UNIT_SQFT["1BHK"]), 1),
            parking_slots=parking_slots,
            description=f"{count_1bhk}× 1BHK units across {max_floors} floor(s). Maximum yield per sq ft.",
            trade_offs=[
                "Smaller units attract rental tenants or junior professionals.",
                "Corridor and staircase space reduces net area further.",
                "Ventilation and natural light harder to achieve for internal units.",
            ],
        ))

        # 2. Balanced — 2BHK, typical family
        count_2bhk = _units_that_fit(net_buildable, _UNIT_SQFT["2BHK"])
        options.append(FeasibilityOption(
            name="balanced",
            label="Balanced — 2BHK family units",
            unit_count=count_2bhk,
            unit_type="2BHK",
            unit_sizes_sqft=[float(_UNIT_SQFT["2BHK"])] * count_2bhk,
            coverage_pct=round(usable_footprint / site_area * 100, 1),
            built_up_area=round(min(net_buildable, count_2bhk * _UNIT_SQFT["2BHK"]), 1),
            parking_slots=parking_slots,
            description=f"{count_2bhk}× 2BHK units (~{_UNIT_SQFT['2BHK']} sq ft each). Best balance of unit size and count.",
            trade_offs=[
                "Good rental/resale value for family occupants.",
                "Typical configuration for Tamil Nadu residential plots.",
                "Each unit needs 1 car parking — ensure slots match unit count.",
            ],
        ))

        # 3. Spacious — 3BHK, owner-occupier focus
        count_3bhk = max(1, _units_that_fit(net_buildable, _UNIT_SQFT["3BHK"]))
        options.append(FeasibilityOption(
            name="spacious",
            label="Spacious — 3BHK owner-occupier",
            unit_count=count_3bhk,
            unit_type="3BHK",
            unit_sizes_sqft=[round(net_buildable / count_3bhk, 1)] * count_3bhk,
            coverage_pct=round(usable_footprint / site_area * 100, 1),
            built_up_area=round(net_buildable, 1),
            parking_slots=parking_slots,
            description=f"{count_3bhk}× 3BHK villa-style unit(s). Maximum room size and comfort.",
            trade_offs=[
                "Premium living experience; lower yield per sq ft.",
                "Ideal for owner-occupier or high-end rental.",
                "Fewer units means lower total rental income.",
            ],
        ))

        # 4. Future expansion — ground floor now, ready for upper floor later
        gf_area = round(usable_footprint * 0.85, 1)  # leave 15% for future staircase/provisions
        options.append(FeasibilityOption(
            name="future_expansion",
            label="Future-ready — ground floor + expansion",
            unit_count=1,
            unit_type="2BHK (expandable)",
            unit_sizes_sqft=[gf_area],
            coverage_pct=round(usable_footprint / site_area * 100, 1),
            built_up_area=gf_area,
            parking_slots=max(1, parking_slots),
            description=(
                f"Single {gf_area:.0f} sq ft unit now. RCC frame provisions for {max_floors} floors. "
                "Add upper floors as family/budget allows."
            ),
            trade_offs=[
                "Lower upfront cost; future flexibility is the key benefit.",
                "RCC frame must be designed for full FSI from day one (structural engineer needed).",
                "Upper floors trigger fresh regulatory approvals.",
            ],
        ))

        # 5. Rental-friendly — mix of studios/1BHK for maximum rental income
        count_studio = _units_that_fit(net_buildable, _UNIT_SQFT["studio"])
        options.append(FeasibilityOption(
            name="rental_friendly",
            label="Rental-friendly — studio/1BHK mix",
            unit_count=count_studio,
            unit_type="Studio/1BHK",
            unit_sizes_sqft=[float(_UNIT_SQFT["studio"])] * count_studio,
            coverage_pct=round(usable_footprint / site_area * 100, 1),
            built_up_area=round(min(net_buildable, count_studio * _UNIT_SQFT["studio"]), 1),
            parking_slots=parking_slots,
            description=(
                f"Up to {count_studio} studio/compact-1BHK units for maximum rental income. "
                "Ideal for student/professional rental market."
            ),
            trade_offs=[
                "Highest gross rental yield per sq ft.",
                "Higher tenant turnover; more management needed.",
                "Studio units may need shared amenities (laundry, common areas) to attract quality tenants.",
                "Local bylaws may restrict number of dwelling units per plot — verify with CMDA.",
            ],
        ))

        return options
