"""Phase 40 — Feasibility / Yield Analysis engine (TestFit-lite).

Advisory only — all figures approximate. For residential plots (India context).
Uses TN setback tiers as default; reuses constants from compliance module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.models.project import ArchitectureProject

from app.core.models.project import Feasibility
from app.core.feasibility.options import OptionGenerator

# TN setback table: (min_road_width_ft, front_ft, side_ft, rear_ft)
_SETBACK_TABLE = [
    (40.0, 15.0, 5.0, 10.0),
    (30.0, 12.0, 4.0, 6.0),
    (20.0,  9.0, 3.0, 4.5),
    (0.0,   7.0, 1.5, 3.0),
]

_TN_RESIDENTIAL_FSI = 1.5
_TN_MAX_COVERAGE_PCT = 66.7  # 2/3 of site
_PARKING_AREA_SQFT = 120.0   # 1 car slot ≈ 120 sq ft


def _setback(road_width_ft: float) -> tuple[float, float, float]:
    """Return (front, side, rear) setback in feet for the given road width."""
    for min_w, f, s, r in _SETBACK_TABLE:
        if road_width_ft >= min_w:
            return f, s, r
    return _SETBACK_TABLE[-1][1], _SETBACK_TABLE[-1][2], _SETBACK_TABLE[-1][3]


class FeasibilityEngine:
    """Compute residential feasibility metrics for an ArchitectureProject site."""

    def compute(self, project: "ArchitectureProject", road_width_ft: float = 0.0) -> Feasibility:
        site = project.site
        floors = project.building.floors

        site_area = site.width * site.depth

        missing: list[str] = []
        warnings: list[str] = []
        assumptions: list[str] = []

        if site_area <= 0:
            missing.append("site_area")
            return Feasibility(
                generated=False,
                missing_inputs=["site dimensions not set"],
                warnings=["Cannot compute feasibility — site area is zero."],
            )

        # Setback-derived usable footprint
        if road_width_ft > 0:
            front, side, rear = _setback(road_width_ft)
            assumptions.append(f"TN setbacks for {road_width_ft:.0f} ft road: front {front} ft, sides {side} ft, rear {rear} ft")
        else:
            front, side, rear = _setback(0)
            assumptions.append("Default minimum setbacks applied (road width not provided). Provide road width for accurate TN setbacks.")
            missing.append("road_width_ft")

        usable_w = max(0.0, site.width - 2 * side)
        usable_d = max(0.0, site.depth - front - rear)
        usable_footprint = usable_w * usable_d

        if usable_footprint <= 0:
            warnings.append(
                "Setbacks exceed site dimensions — usable footprint is zero. Site may be too small for TN setbacks."
            )
            usable_footprint = site_area * 0.5  # fallback

        coverage_pct = usable_footprint / site_area * 100

        if coverage_pct > _TN_MAX_COVERAGE_PCT:
            warnings.append(
                f"Computed coverage {coverage_pct:.1f}% exceeds TN residential max {_TN_MAX_COVERAGE_PCT:.1f}%. "
                "Setbacks may reduce footprint further — verify with CMDA."
            )
            coverage_pct = min(coverage_pct, _TN_MAX_COVERAGE_PCT)
            usable_footprint = site_area * _TN_MAX_COVERAGE_PCT / 100

        fsi = _TN_RESIDENTIAL_FSI
        assumptions.append(f"TN residential FSI/FAR = {fsi} (basic residential zone; premium zones allow up to 2.5)")

        buildable_area = site_area * fsi
        max_floors = max(1, int(buildable_area / usable_footprint)) if usable_footprint > 0 else 1
        effective_floors = min(floors, max_floors)

        if floors > max_floors:
            warnings.append(
                f"Project has {floors} floor(s) but FSI allows max ~{max_floors} floor(s) on this site. "
                f"Built-up area capped at {buildable_area:.0f} sq ft (FSI {fsi})."
            )

        # Parking estimate: 1 slot per ~600 sq ft BUA or minimum 1
        total_bua = usable_footprint * effective_floors
        parking_estimate = max(1, int(total_bua / 600))
        assumptions.append(f"Parking: 1 slot per 600 sq ft BUA (advisory; TN mandates 1 car per 100 m² BUA in CMDA zones)")

        if site_area < 600:
            warnings.append("Site area < 600 sq ft — feasibility options are very constrained. Single-unit only.")

        assumptions.append("All figures advisory — confirm with licensed architect and CMDA/DTCP before applying.")

        # Generate options
        opt_gen = OptionGenerator()
        options = opt_gen.generate(
            site_area=site_area,
            usable_footprint=usable_footprint,
            buildable_area=buildable_area,
            max_floors=max_floors,
            parking_slots=parking_estimate,
        )

        return Feasibility(
            site_area=round(site_area, 1),
            usable_footprint=round(usable_footprint, 1),
            coverage_pct=round(coverage_pct, 1),
            fsi_far=fsi,
            buildable_area=round(buildable_area, 1),
            floors=effective_floors,
            parking_estimate=parking_estimate,
            options=options,
            missing_inputs=missing,
            warnings=warnings,
            assumptions=assumptions,
            confidence=0.75 if missing else 0.85,
            needs_review=True,
            generated=True,
            road_width_ft=road_width_ft,
        )
