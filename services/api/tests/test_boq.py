"""Tests for rate system and BOQ logic — Phase 31.5."""

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.boq.quantity_engine import QuantityEngine
from app.core.boq.rates import DEFAULT_RATES, RateTable
from app.core.models.project import RateEntry


def _project(prompt="2BHK 30x50 east-facing with 2 bathrooms kitchen"):
    p, _ = generate_floorplan(parse_prompt(prompt))
    return p


# ── RateTable tests ───────────────────────────────────────────────────────────


def test_rate_table_defaults_loaded() -> None:
    rt = RateTable()
    assert rt.get("flooring", "tile_supply") > 0
    assert rt.get("paint", "interior_paint") > 0


def test_rate_table_missing_returns_zero() -> None:
    rt = RateTable()
    assert rt.get("nonexistent", "nonexistent") == 0.0


def test_rate_table_set_updates_rate() -> None:
    rt = RateTable()
    rt.set("flooring", "tile_supply", 100.0)
    assert rt.get("flooring", "tile_supply") == 100.0


def test_rate_table_override_on_init() -> None:
    overrides = [RateEntry(category="flooring", item="tile_supply", unit="sqft", rate=150.0)]
    rt = RateTable(overrides=overrides)
    assert rt.get("flooring", "tile_supply") == 150.0


def test_rate_table_preserves_other_defaults() -> None:
    overrides = [RateEntry(category="flooring", item="tile_supply", unit="sqft", rate=150.0)]
    rt = RateTable(overrides=overrides)
    assert rt.get("paint", "interior_paint") > 0


def test_rate_table_all_entries_includes_defaults() -> None:
    rt = RateTable()
    entries = rt.all_entries()
    cats = {e.category for e in entries}
    assert "flooring" in cats
    assert "paint" in cats
    assert "plumbing" in cats


def test_rate_table_from_project() -> None:
    project = _project()
    rt = RateTable.from_project(project.material_plan.editable_rates)
    assert rt.get("flooring", "tile_supply") > 0


# ── Missing rate warnings ─────────────────────────────────────────────────────


def test_zero_rate_items_in_missing_rates() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    # Furniture items get rate=0 → should appear in missing_rates
    if project.furniture:
        assert len(cost.missing_rates) > 0
    # Grand total should exclude zero-rate items
    included = sum(i.amount for i in cost.boq_items if i.rate > 0)
    assert abs(cost.grand_total - included) < 1.0


def test_rate_override_changes_amount() -> None:
    from app.core.models.project import RateEntry as RE
    project = _project()
    # Set tile supply rate to 0 manually
    rates = [RE(category="flooring", item="tile_supply", unit="sqft", rate=0.0, source="manual")]
    mat = project.material_plan.model_copy(update={"editable_rates": rates})
    project_low = project.model_copy(update={"material_plan": mat})
    engine_low = QuantityEngine(project_low)
    _, cost_low = engine_low.build_boq()
    # Tile supply items should have amount=0
    tile_supply = [i for i in cost_low.boq_items
                   if "tile supply" in i.description.lower() and "floor" in i.description.lower()]
    for item in tile_supply:
        assert item.amount == 0.0


def test_rate_increase_increases_grand_total() -> None:
    from app.core.models.project import RateEntry as RE
    project = _project()
    engine_default = QuantityEngine(project)
    _, cost_default = engine_default.build_boq()

    rates = [RE(category="flooring", item="tile_supply", unit="sqft", rate=200.0, source="manual")]
    mat = project.material_plan.model_copy(update={"editable_rates": rates})
    project_hi = project.model_copy(update={"material_plan": mat})
    engine_hi = QuantityEngine(project_hi)
    _, cost_hi = engine_hi.build_boq()
    assert cost_hi.grand_total > cost_default.grand_total


def test_default_rates_all_have_rate_gt_zero() -> None:
    for entry in DEFAULT_RATES:
        assert entry.rate > 0, f"{entry.category}/{entry.item} has rate=0"


def test_default_rates_all_have_unit() -> None:
    for entry in DEFAULT_RATES:
        assert entry.unit, f"{entry.category}/{entry.item} missing unit"


def test_boq_assumptions_populated() -> None:
    project = _project()
    engine = QuantityEngine(project)
    updated_mat, cost = engine.build_boq()
    # Default tile spec assumption should appear
    assert len(cost.assumptions) > 0


def test_boq_confidence_above_zero() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    assert cost.confidence > 0.0


def test_boq_needs_review_true() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    assert cost.needs_review is True
