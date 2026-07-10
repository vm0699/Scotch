"""Tests for Material / BOQ / Cost models — Phase 31.2 / 31.4."""

import json

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models.project import (
    ArchitectureProject,
    BOQItem,
    CategoryTotal,
    CostPlan,
    MaterialPlan,
    RateEntry,
    RoomFinish,
    TileSpec,
)
from app.core.validation import validate_project


def _base_project():
    p, _ = generate_floorplan(parse_prompt("2BHK 30x50 east-facing with 2 bathrooms kitchen"))
    return p


def test_new_project_has_material_plan() -> None:
    project = _base_project()
    assert hasattr(project, "material_plan")
    assert project.material_plan.generated is False


def test_new_project_has_cost_plan() -> None:
    project = _base_project()
    assert hasattr(project, "cost_plan")
    assert project.cost_plan.generated is False
    assert project.cost_plan.grand_total == 0.0


def test_old_project_loads_without_boq_fields() -> None:
    project = _base_project()
    data = project.model_dump()
    data.pop("material_plan", None)
    data.pop("cost_plan", None)
    loaded = ArchitectureProject.model_validate(data)
    assert loaded.material_plan.generated is False
    assert loaded.cost_plan.grand_total == 0.0


def test_tile_spec_model() -> None:
    ts = TileSpec(id="ts-1", size_w=24.0, size_h=24.0, rate_per_sqft=80.0, wastage_pct=10.0)
    assert ts.size_w == 24.0
    assert ts.wastage_pct == 10.0


def test_room_finish_model() -> None:
    rf = RoomFinish(room_id="bath-1", floor_material="tile", wall_material="tile")
    assert rf.floor_material == "tile"


def test_rate_entry_model() -> None:
    re = RateEntry(category="flooring", item="tile_supply", unit="sqft", rate=80.0, source="manual")
    assert re.rate == 80.0


def test_boq_item_model() -> None:
    item = BOQItem(
        id="boq-1", category="flooring", description="Floor tile — Living",
        source_object_ids=["living"], unit="sqft", quantity=120.0, rate=80.0, amount=9600.0,
    )
    assert item.amount == 9600.0
    assert item.rate == 80.0


def test_boq_item_missing_rate() -> None:
    item = BOQItem(
        id="boq-2", category="furniture", description="Sofa",
        unit="nos", quantity=1.0, rate=0.0, amount=0.0,
    )
    assert item.rate == 0.0
    assert item.amount == 0.0


def test_cost_plan_round_trip() -> None:
    cp = CostPlan(
        boq_items=[
            BOQItem(id="b1", category="flooring", description="Tile",
                    unit="sqft", quantity=100.0, rate=80.0, amount=8000.0),
        ],
        category_totals=[CategoryTotal(category="flooring", total=8000.0)],
        grand_total=8000.0,
        missing_rates=[],
        assumptions=["Standard rates applied"],
        generated=True,
    )
    data = json.loads(cp.model_dump_json())
    loaded = CostPlan.model_validate(data)
    assert loaded.grand_total == 8000.0
    assert len(loaded.boq_items) == 1


def test_material_plan_round_trip() -> None:
    mp = MaterialPlan(
        tile_specs=[TileSpec(id="ts-1", size_w=24.0, size_h=24.0)],
        room_finishes=[RoomFinish(room_id="bath-1", floor_material="tile")],
        editable_rates=[RateEntry(category="flooring", item="tile_supply", unit="sqft", rate=90.0)],
        generated=True,
    )
    data = json.loads(mp.model_dump_json())
    loaded = MaterialPlan.model_validate(data)
    assert len(loaded.tile_specs) == 1
    assert loaded.tile_specs[0].id == "ts-1"


def test_project_with_cost_plan_validates() -> None:
    project = _base_project()
    room = project.rooms[0]
    cp = CostPlan(
        boq_items=[BOQItem(id="b1", category="flooring", description="Tile",
                           source_object_ids=[room.id], unit="sqft",
                           quantity=100.0, rate=80.0, amount=8000.0)],
        category_totals=[CategoryTotal(category="flooring", total=8000.0)],
        grand_total=8000.0, generated=True,
    )
    project2 = project.model_copy(update={"cost_plan": cp})
    result = validate_project(project2)
    assert result.valid, result.errors


def test_project_round_trip_with_boq() -> None:
    project = _base_project()
    cp = CostPlan(
        boq_items=[BOQItem(id="b1", category="paint", description="Paint",
                           unit="sqft", quantity=50.0, rate=18.0, amount=900.0)],
        category_totals=[CategoryTotal(category="paint", total=900.0)],
        grand_total=900.0, generated=True,
    )
    project2 = project.model_copy(update={"cost_plan": cp})
    data = json.loads(project2.model_dump_json())
    loaded = ArchitectureProject.model_validate(data)
    assert loaded.cost_plan.grand_total == 900.0
    assert len(loaded.cost_plan.boq_items) == 1
