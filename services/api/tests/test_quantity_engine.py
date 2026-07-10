"""Tests for QuantityEngine — Phase 31.3."""

import math

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.boq.quantity_engine import QuantityEngine


def _project(prompt="2BHK 30x50 east-facing with 2 bathrooms kitchen 2 floors"):
    p, _ = generate_floorplan(parse_prompt(prompt))
    return p


def test_build_boq_returns_cost_plan() -> None:
    project = _project()
    engine = QuantityEngine(project)
    mat, cost = engine.build_boq()
    assert cost.generated is True
    assert len(cost.boq_items) > 0


def test_build_boq_has_floor_items() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    categories = {item.category for item in cost.boq_items}
    assert "flooring" in categories


def test_floor_tile_quantity_includes_wastage() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    # Sum of all flooring tile supply quantities
    floor_supply = [i for i in cost.boq_items
                    if i.category == "flooring" and "supply" in i.description.lower()]
    for item in floor_supply:
        # Source room
        room_ids = item.source_object_ids
        if not room_ids:
            continue
        room = next((r for r in project.rooms if r.id == room_ids[0]), None)
        if room is None:
            continue
        raw_area = room.width * room.depth
        # Default wastage 10% → tile_area ≥ raw_area * 1.10
        assert item.quantity >= raw_area * 1.09  # allow fp rounding


def test_skirting_length_less_than_or_equal_perimeter() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    skirting_items = [i for i in cost.boq_items if "skirting" in i.description.lower()]
    for item in skirting_items:
        room_ids = item.source_object_ids
        if not room_ids:
            continue
        room = next((r for r in project.rooms if r.id == room_ids[0]), None)
        if room is None:
            continue
        perimeter = 2 * (room.width + room.depth)
        assert item.quantity <= perimeter


def test_build_boq_has_wall_tile_for_bathroom() -> None:
    project = _project()
    bath_rooms = [r for r in project.rooms if r.type in ("bathroom", "master_bathroom")]
    if not bath_rooms:
        pytest.skip("No bathroom in project")
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    wall_tile_items = [i for i in cost.boq_items if i.category == "wall_tile"]
    assert len(wall_tile_items) > 0


def test_build_boq_has_paint_for_dry_rooms() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    paint_items = [i for i in cost.boq_items if i.category == "paint"]
    assert len(paint_items) > 0


def test_build_boq_has_door_items() -> None:
    project = _project()
    if not project.doors:
        pytest.skip("No doors")
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    door_items = [i for i in cost.boq_items if i.category == "doors"]
    assert len(door_items) == len(project.doors)


def test_build_boq_has_window_items() -> None:
    project = _project()
    if not project.windows:
        pytest.skip("No windows")
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    win_items = [i for i in cost.boq_items if i.category == "windows"]
    assert len(win_items) == len(project.windows)


def test_build_boq_has_plumbing_items() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    plumbing_items = [i for i in cost.boq_items if i.category == "plumbing"]
    assert len(plumbing_items) > 0


def test_build_boq_has_electrical_items() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    elec_items = [i for i in cost.boq_items if i.category == "electrical"]
    assert len(elec_items) > 0


def test_grand_total_equals_sum_of_category_totals() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    expected = round(sum(ct.total for ct in cost.category_totals), 2)
    assert abs(cost.grand_total - expected) < 0.1


def test_items_with_zero_rate_excluded_from_total() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    # Items with rate=0 should have amount=0 and appear in missing_rates or be skipped from total
    zero_rate_items = [i for i in cost.boq_items if i.rate == 0.0]
    for item in zero_rate_items:
        assert item.amount == 0.0


def test_source_object_ids_trace_back_to_rooms() -> None:
    project = _project()
    room_ids = {r.id for r in project.rooms}
    door_ids = {d.id for d in project.doors}
    win_ids  = {w.id for w in project.windows}
    furn_ids = {f.id for f in project.furniture}
    all_ids  = room_ids | door_ids | win_ids | furn_ids
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    for item in cost.boq_items:
        for src_id in item.source_object_ids:
            assert src_id in all_ids or src_id.startswith("pt-"), (
                f"BOQ item '{item.description}' has unknown source_id '{src_id}'"
            )


def test_category_totals_populated() -> None:
    project = _project()
    engine = QuantityEngine(project)
    _, cost = engine.build_boq()
    assert len(cost.category_totals) > 0
    cats = {ct.category for ct in cost.category_totals}
    assert "flooring" in cats


def test_material_plan_has_default_tile_spec() -> None:
    project = _project()
    engine = QuantityEngine(project)
    updated_mat, _ = engine.build_boq()
    assert len(updated_mat.tile_specs) > 0
    assert updated_mat.tile_specs[0].size_w == 24.0


def test_boq_with_mep_generated() -> None:
    from app.core.architecture.mep_generator import MEPGenerator
    project = _project()
    mep_plan = MEPGenerator.generate(project)
    mep_project = project.model_copy(update={"mep_plan": mep_plan})
    engine = QuantityEngine(mep_project)
    _, cost = engine.build_boq()
    # With MEP generated, electrical items should come from MEP points
    elec_items = [i for i in cost.boq_items if i.category == "electrical"]
    assert len(elec_items) > 0
    # Plumbing should reference MEP point IDs
    plumbing_items = [i for i in cost.boq_items if i.category == "plumbing"]
    assert len(plumbing_items) > 0
