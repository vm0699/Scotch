"""Architecture Intelligence — Phase 13.

Exports: compute_areas, run_spatial_checks, run_vastu_checks,
         and all model types.
"""

from app.core.intelligence.area_calculator import compute_areas
from app.core.intelligence.models import (
    AreaSummary,
    IntelligenceReport,
    RoomAreaEntry,
    SpatialCheck,
    VastuSuggestion,
)
from app.core.intelligence.spatial_checks import run_spatial_checks
from app.core.intelligence.vastu import run_vastu_checks

__all__ = [
    "compute_areas",
    "run_spatial_checks",
    "run_vastu_checks",
    "AreaSummary",
    "IntelligenceReport",
    "RoomAreaEntry",
    "SpatialCheck",
    "VastuSuggestion",
]
