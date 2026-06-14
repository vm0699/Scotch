"""Intelligence report models — Phase 13."""

from typing import Literal
from pydantic import BaseModel

CheckSeverity = Literal["info", "warning", "error"]


class SpatialCheck(BaseModel):
    rule_id: str
    severity: CheckSeverity
    message: str
    room_id: str | None = None
    detail: str | None = None


class RoomAreaEntry(BaseModel):
    room_id: str
    room_name: str
    room_type: str
    gross_area: float
    carpet_area: float


class AreaSummary(BaseModel):
    site_area: float
    built_up_area: float
    carpet_area: float
    circulation_area: float
    coverage_ratio: float   # %
    floor_efficiency: float  # %
    rooms: list[RoomAreaEntry]


class VastuSuggestion(BaseModel):
    rule_id: str
    severity: CheckSeverity
    message: str
    room_id: str | None = None
    direction: str | None = None


class IntelligenceReport(BaseModel):
    project_id: str
    spatial_checks: list[SpatialCheck]
    area_summary: AreaSummary
    vastu_suggestions: list[VastuSuggestion] | None = None
