"""Tests for UnitConversionService (Phase 29.0)."""

import pytest

from app.core.units import FEET_PER_METER, METER_PER_FOOT, UnitConversionService


def test_constants_reciprocal() -> None:
    assert abs(FEET_PER_METER * METER_PER_FOOT - 1.0) < 1e-9


def test_to_meters_from_feet() -> None:
    result = UnitConversionService.to_meters(10.0, "feet")
    assert abs(result - 3.048) < 0.001


def test_to_meters_from_meters() -> None:
    result = UnitConversionService.to_meters(5.0, "meters")
    assert result == 5.0


def test_to_feet_from_meters() -> None:
    result = UnitConversionService.to_feet(3.048, "meters")
    assert abs(result - 10.0) < 0.01


def test_to_feet_from_feet() -> None:
    result = UnitConversionService.to_feet(7.0, "feet")
    assert result == 7.0


def test_convert_feet_to_meters() -> None:
    v = UnitConversionService.convert(30.0, "feet", "meters")
    assert abs(v - 9.144) < 0.001


def test_convert_meters_to_feet() -> None:
    v = UnitConversionService.convert(9.144, "meters", "feet")
    assert abs(v - 30.0) < 0.01


def test_convert_same_units() -> None:
    v = UnitConversionService.convert(12.5, "feet", "feet")
    assert v == 12.5


def test_format_dimension_feet_whole() -> None:
    label = UnitConversionService.format_dimension(10.0, "feet")
    assert label == "10′-0″"


def test_format_dimension_feet_with_inches() -> None:
    # 10.5 ft = 10 ft 6 in
    label = UnitConversionService.format_dimension(10.5, "feet")
    assert label == "10′-6″"


def test_format_dimension_feet_inch_rollover() -> None:
    # 10 ft + 12 in = 11 ft 0 in
    label = UnitConversionService.format_dimension(11.0, "feet")
    assert label == "11′-0″"


def test_format_dimension_meters() -> None:
    label = UnitConversionService.format_dimension(3.05, "meters")
    assert label == "3.05m"


def test_round_trip_feet_meters_feet() -> None:
    original = 25.0
    m = UnitConversionService.to_meters(original, "feet")
    back = UnitConversionService.to_feet(m, "meters")
    assert abs(back - original) < 0.01
