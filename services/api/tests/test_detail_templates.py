"""Tests for detail template library (Phase 30.2)."""

import json
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).parent.parent / "app" / "data" / "detail_templates"

ALL_TEMPLATES = [
    "toilet_detail.json",
    "kitchen_detail.json",
    "door_window_detail.json",
    "wall_section_detail.json",
    "tile_layout_detail.json",
    "stair_detail.json",
]

REQUIRED_FIELDS = ["type", "name", "view", "scale", "annotations", "confidence", "needs_review", "source"]


@pytest.mark.parametrize("filename", ALL_TEMPLATES)
def test_template_file_exists(filename: str) -> None:
    assert (TEMPLATES_DIR / filename).exists(), f"Template not found: {filename}"


@pytest.mark.parametrize("filename", ALL_TEMPLATES)
def test_template_is_valid_json(filename: str) -> None:
    data = json.loads((TEMPLATES_DIR / filename).read_text(encoding="utf-8"))
    assert isinstance(data, dict)


@pytest.mark.parametrize("filename", ALL_TEMPLATES)
def test_template_has_required_fields(filename: str) -> None:
    data = json.loads((TEMPLATES_DIR / filename).read_text(encoding="utf-8"))
    for field in REQUIRED_FIELDS:
        assert field in data, f"{filename} missing required field: {field}"


@pytest.mark.parametrize("filename", ALL_TEMPLATES)
def test_template_confidence_in_range(filename: str) -> None:
    data = json.loads((TEMPLATES_DIR / filename).read_text(encoding="utf-8"))
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.parametrize("filename", ALL_TEMPLATES)
def test_template_has_source_attribution(filename: str) -> None:
    data = json.loads((TEMPLATES_DIR / filename).read_text(encoding="utf-8"))
    assert data["source"], f"{filename}: source field must not be empty"


@pytest.mark.parametrize("filename", ALL_TEMPLATES)
def test_template_has_annotations(filename: str) -> None:
    data = json.loads((TEMPLATES_DIR / filename).read_text(encoding="utf-8"))
    assert len(data["annotations"]) >= 2, f"{filename}: must have at least 2 advisory annotations"


def test_toilet_template_has_fixtures() -> None:
    data = json.loads((TEMPLATES_DIR / "toilet_detail.json").read_text(encoding="utf-8"))
    assert "fixtures" in data
    fixture_ids = [f["id"] for f in data["fixtures"]]
    assert "wc" in fixture_ids
    assert "basin" in fixture_ids


def test_kitchen_template_has_appliances() -> None:
    data = json.loads((TEMPLATES_DIR / "kitchen_detail.json").read_text(encoding="utf-8"))
    assert "appliances" in data
    app_ids = [a["id"] for a in data["appliances"]]
    assert "sink" in app_ids
    assert "stove" in app_ids


def test_wall_section_has_layers() -> None:
    data = json.loads((TEMPLATES_DIR / "wall_section_detail.json").read_text(encoding="utf-8"))
    assert "floor_layers" in data
    assert len(data["floor_layers"]) >= 2


def test_stair_template_has_required_fields() -> None:
    data = json.loads((TEMPLATES_DIR / "stair_detail.json").read_text(encoding="utf-8"))
    assert "show_risers" in data
    assert "show_handrail" in data
    assert "handrail_height_ft" in data
