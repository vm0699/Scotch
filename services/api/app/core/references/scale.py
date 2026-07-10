"""Phase 39 — Scale calibration engine.

User marks two known points on the reference image (pixel coords) and provides
the real-world distance between them in feet. From this we derive pixels_per_foot
and can transform any pixel coordinate into project-space feet coords.
"""
from __future__ import annotations

import math

from app.core.references.models import ScaleCalibration


def compute_scale(
    p1_x: float,
    p1_y: float,
    p2_x: float,
    p2_y: float,
    known_distance_ft: float,
    origin_x_ft: float = 0.0,
    origin_y_ft: float = 0.0,
) -> ScaleCalibration:
    """Create a ScaleCalibration from two pixel points and a known distance."""
    if known_distance_ft <= 0:
        raise ValueError("known_distance_ft must be positive")
    dx = p2_x - p1_x
    dy = p2_y - p1_y
    pixel_dist = math.sqrt(dx * dx + dy * dy)
    if pixel_dist < 1.0:
        raise ValueError("Calibration points must be at least 1 pixel apart")
    return ScaleCalibration(
        p1_x=p1_x,
        p1_y=p1_y,
        p2_x=p2_x,
        p2_y=p2_y,
        known_distance_ft=known_distance_ft,
        pixels_per_foot=pixel_dist / known_distance_ft,
        origin_x_ft=origin_x_ft,
        origin_y_ft=origin_y_ft,
    )


def pixel_to_ft(
    px: float,
    py: float,
    calibration: ScaleCalibration,
) -> tuple[float, float]:
    """Convert pixel coords to project-space feet, with origin offset applied."""
    x_ft = (px - calibration.p1_x) / calibration.pixels_per_foot + calibration.origin_x_ft
    y_ft = (py - calibration.p1_y) / calibration.pixels_per_foot + calibration.origin_y_ft
    return round(x_ft, 3), round(y_ft, 3)


def ft_to_pixel(
    x_ft: float,
    y_ft: float,
    calibration: ScaleCalibration,
) -> tuple[float, float]:
    """Inverse: project-space feet → pixel coords."""
    px = (x_ft - calibration.origin_x_ft) * calibration.pixels_per_foot + calibration.p1_x
    py = (y_ft - calibration.origin_y_ft) * calibration.pixels_per_foot + calibration.p1_y
    return round(px, 1), round(py, 1)


def pixel_distance_ft(
    p1_x: float,
    p1_y: float,
    p2_x: float,
    p2_y: float,
    calibration: ScaleCalibration,
) -> float:
    """Compute the real-world distance (ft) between two pixel points."""
    dx = p2_x - p1_x
    dy = p2_y - p1_y
    pixel_dist = math.sqrt(dx * dx + dy * dy)
    return round(pixel_dist / calibration.pixels_per_foot, 3)
