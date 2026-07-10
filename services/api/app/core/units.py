"""Unit conversion service — feet ↔ meters, project-unit-aware.

Default project unit is feet. All model coordinates are stored in the
project's declared units. This module handles conversion for display,
input parsing, and metric-toggle output.
"""

from __future__ import annotations

FEET_PER_METER: float = 3.28084
METER_PER_FOOT: float = 1.0 / FEET_PER_METER

Units = str  # "feet" | "meters" — mirrors models.project.Units


class UnitConversionService:
    """Stateless feet ↔ meters converter."""

    @staticmethod
    def to_meters(value: float, from_units: Units) -> float:
        if from_units == "meters":
            return round(value, 4)
        return round(value * METER_PER_FOOT, 4)

    @staticmethod
    def to_feet(value: float, from_units: Units) -> float:
        if from_units == "feet":
            return round(value, 4)
        return round(value * FEET_PER_METER, 4)

    @staticmethod
    def convert(value: float, from_units: Units, to_units: Units) -> float:
        if from_units == to_units:
            return value
        if to_units == "meters":
            return UnitConversionService.to_meters(value, from_units)
        return UnitConversionService.to_feet(value, from_units)

    @staticmethod
    def format_dimension(value: float, units: Units) -> str:
        """Architectural dimension string with unit suffix."""
        if units == "feet":
            feet = int(value)
            inches = round((value - feet) * 12)
            if inches >= 12:
                feet += 1
                inches = 0
            if inches == 0:
                return f"{feet}′-0″"
            return f"{feet}′-{inches}″"
        # meters
        return f"{value:.2f}m"
