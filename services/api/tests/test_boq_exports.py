"""Tests for BOQ export adapters — Phase 31.8."""

import csv
import io
import json

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.boq.quantity_engine import QuantityEngine
from app.core.exports.boq_exporter import export_boq_csv, export_boq_json


def _project_with_boq(prompt="2BHK 30x50 east-facing with 2 bathrooms kitchen"):
    p, _ = generate_floorplan(parse_prompt(prompt))
    engine = QuantityEngine(p)
    mat, cost = engine.build_boq()
    return p.model_copy(update={"material_plan": mat, "cost_plan": cost})


def test_csv_export_creates_file(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.csv"
    result = export_boq_csv(project, out)
    assert result.exists()
    assert result.stat().st_size > 0


def test_csv_has_header_row(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.csv"
    export_boq_csv(project, out)
    rows = list(csv.reader(out.read_text(encoding="utf-8").splitlines()))
    assert rows[0][0] == "Category"
    assert "Description" in rows[0]


def test_csv_contains_all_boq_items(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.csv"
    export_boq_csv(project, out)
    content = out.read_text(encoding="utf-8")
    for item in project.cost_plan.boq_items[:5]:
        assert item.category in content or item.description[:15] in content


def test_csv_contains_grand_total(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.csv"
    export_boq_csv(project, out)
    content = out.read_text(encoding="utf-8")
    assert "GRAND TOTAL" in content


def test_csv_contains_missing_rates_section_when_present(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.csv"
    export_boq_csv(project, out)
    content = out.read_text(encoding="utf-8")
    if project.cost_plan.missing_rates:
        assert "MISSING RATES" in content


def test_json_export_creates_file(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.json"
    result = export_boq_json(project, out)
    assert result.exists()


def test_json_export_valid_json(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.json"
    export_boq_json(project, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_json_export_has_cost_plan(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.json"
    export_boq_json(project, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "cost_plan" in data
    assert data["cost_plan"]["generated"] is True


def test_json_export_has_material_plan(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.json"
    export_boq_json(project, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "material_plan" in data


def test_json_grand_total_matches_project(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.json"
    export_boq_json(project, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert abs(data["cost_plan"]["grand_total"] - project.cost_plan.grand_total) < 0.1


def test_json_boq_items_count_matches(tmp_path) -> None:
    project = _project_with_boq()
    out = tmp_path / "boq.json"
    export_boq_json(project, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["cost_plan"]["boq_items"]) == len(project.cost_plan.boq_items)


def test_csv_export_with_empty_boq(tmp_path) -> None:
    """CSV should still write header row even with no BOQ items."""
    p, _ = generate_floorplan(parse_prompt("studio 20x30"))
    out = tmp_path / "boq_empty.csv"
    export_boq_csv(p, out)
    rows = list(csv.reader(out.read_text(encoding="utf-8").splitlines()))
    assert rows[0][0] == "Category"
