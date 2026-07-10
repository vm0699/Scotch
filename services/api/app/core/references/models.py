"""Phase 39 — Reference asset model.

A ReferenceAsset is a sidecar file (image/PDF/sketch) uploaded to a project
for use as an overlay or extraction source. It is not part of ArchitectureProject
— it lives in a separate sidecar directory per project.

Layout:
    {data_dir}/users/{uid}/projects/{project_id}/references/{asset_id}.json  ← metadata
    {data_dir}/users/{uid}/projects/{project_id}/references/files/{filename}  ← binary
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ReferenceType = Literal[
    "sketch",
    "photo",
    "pdf_page",
    "site_plan",
    "existing_plan",
    "reference_image",
]

ScaleStatus = Literal["uncalibrated", "calibrated", "auto_detected"]


class ScaleCalibration(BaseModel):
    """User-provided calibration: two pixel points + known real-world distance."""
    p1_x: float = Field(..., description="Pixel X of calibration point 1")
    p1_y: float = Field(..., description="Pixel Y of calibration point 1")
    p2_x: float = Field(..., description="Pixel X of calibration point 2")
    p2_y: float = Field(..., description="Pixel Y of calibration point 2")
    known_distance_ft: float = Field(..., gt=0, description="Known real-world distance in feet")
    pixels_per_foot: float = Field(default=0.0, description="Derived: pixel distance / known_distance_ft")
    origin_x_ft: float = Field(default=0.0, description="Project X offset for pixel origin")
    origin_y_ft: float = Field(default=0.0, description="Project Y offset for pixel origin")

    @model_validator(mode="after")
    def _derive_scale(self) -> "ScaleCalibration":
        # Always derive from points so JSON roundtrips stay consistent.
        dx = self.p2_x - self.p1_x
        dy = self.p2_y - self.p1_y
        pixel_dist = math.sqrt(dx * dx + dy * dy)
        if pixel_dist < 1.0:
            raise ValueError("Calibration points must be at least 1 pixel apart")
        self.pixels_per_foot = pixel_dist / self.known_distance_ft
        return self


class ExtractedEntity(BaseModel):
    """A single entity detected or manually traced from a reference image."""
    id: str
    entity_type: str = Field(
        ...,
        description="One of: wall, room, opening, label, dimension, stair, column",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    geometry: dict = Field(default_factory=dict, description="Type-specific geometry primitives")
    label: str | None = None
    needs_review: bool = True
    linked_project_object_id: str | None = None


class ReferenceAsset(BaseModel):
    """Metadata record for a single uploaded reference file."""
    id: str
    project_id: str
    file_name: str
    file_path: str = Field(..., description="Path relative to the project references/files/ dir")
    mime_type: str
    file_size_bytes: int
    reference_type: ReferenceType = "reference_image"
    scale_status: ScaleStatus = "uncalibrated"
    calibration: ScaleCalibration | None = None
    extracted_entities: list[ExtractedEntity] = Field(default_factory=list)
    needs_review: bool = True
    linked_project_objects: list[str] = Field(
        default_factory=list,
        description="IDs of ArchitectureProject objects traced from this reference",
    )
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
