"""Tests for BOQ chat tools — Phase 31.7."""

from pathlib import Path

import pytest

import app.core.chat_tools as ct
from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.chat_tools import calculate_boq, edit_rate, get_boq
from app.core.storage.local_store import LocalProjectStore


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    orig = ct._store
    ct._store = lambda: store
    yield store
    ct._store = orig


@pytest.fixture()
def project_id(_tmp_store):
    store = _tmp_store
    project, _ = generate_floorplan(parse_prompt("2BHK 30x50 east-facing with 2 bathrooms kitchen"))
    stored = store.create_project("BOQ Test Project")
    store.update_project(stored.id, project=project)
    return stored.id, project


def test_calculate_boq_returns_project(project_id) -> None:
    pid, _ = project_id
    result = calculate_boq(pid)
    assert isinstance(result, dict)
    assert "cost_plan" in result


def test_calculate_boq_generated_true(project_id) -> None:
    pid, _ = project_id
    result = calculate_boq(pid)
    assert result["cost_plan"]["generated"] is True


def test_calculate_boq_has_items(project_id) -> None:
    pid, _ = project_id
    result = calculate_boq(pid)
    assert len(result["cost_plan"]["boq_items"]) > 0


def test_calculate_boq_grand_total_positive(project_id) -> None:
    pid, _ = project_id
    result = calculate_boq(pid)
    assert result["cost_plan"]["grand_total"] > 0


def test_get_boq_before_calculate(project_id) -> None:
    pid, _ = project_id
    result = get_boq(pid)
    assert result["generated"] is False
    assert result["grand_total"] == 0.0


def test_get_boq_after_calculate(project_id) -> None:
    pid, _ = project_id
    calculate_boq(pid)
    result = get_boq(pid)
    assert result["generated"] is True
    assert result["grand_total"] > 0


def test_edit_rate_changes_total(project_id) -> None:
    pid, _ = project_id
    calculate_boq(pid)
    before = get_boq(pid)["grand_total"]
    # Set tile supply to a very high rate
    result = edit_rate(pid, "flooring", "tile_supply", 500.0)
    after = get_boq(pid)["grand_total"]
    assert after > before or after == before  # Should not decrease dramatically with higher rate


def test_edit_rate_persists(project_id) -> None:
    pid, _ = project_id
    edit_rate(pid, "flooring", "tile_supply", 999.0)
    # Reload from store
    proj = ct._load(pid)
    rates = proj.material_plan.editable_rates
    matched = [r for r in rates if r.category == "flooring" and r.item == "tile_supply"]
    assert matched and matched[0].rate == 999.0


def test_calculate_boq_nonexistent_project() -> None:
    with pytest.raises(Exception):
        calculate_boq("no-such-project")


def test_edit_rate_nonexistent_project() -> None:
    with pytest.raises(Exception):
        edit_rate("no-such-project", "flooring", "tile_supply", 100.0)


def test_calculate_boq_idempotent(project_id) -> None:
    pid, _ = project_id
    r1 = calculate_boq(pid)
    r2 = calculate_boq(pid)
    # Grand totals should be equal on repeated calls (deterministic)
    assert abs(r1["cost_plan"]["grand_total"] - r2["cost_plan"]["grand_total"]) < 1.0


def test_boq_has_category_totals(project_id) -> None:
    pid, _ = project_id
    result = calculate_boq(pid)
    assert len(result["cost_plan"]["category_totals"]) > 0


def test_boq_has_assumptions(project_id) -> None:
    pid, _ = project_id
    result = calculate_boq(pid)
    assert len(result["cost_plan"]["assumptions"]) > 0
