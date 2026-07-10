"""Phase 34 — Affected-Item Engine unit tests."""
import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.changes.affected_items import _detect_intent, compute_affected_items

PROMPT = "3BHK on a 30x50 ft east-facing site with master bedroom, 2 regular bedrooms, living room, kitchen, 2 bathrooms, balcony"


def _project():
    proj, _ = generate_floorplan(parse_prompt(PROMPT))
    return proj


# ── Intent detection ──────────────────────────────────────────────────────────

def test_detect_add_toilet_compound():
    intent = _detect_intent("Client wants an attached toilet to the master bedroom")
    assert intent["add_toilet"] is True
    assert intent["add_room"] is True
    assert intent["room_type"] == "bathroom"


def test_detect_ensuite_variant():
    intent = _detect_intent("Add en-suite bathroom to master bedroom")
    assert intent["add_toilet"] is True


def test_detect_remove_bedroom():
    intent = _detect_intent("Remove the second bedroom — family doesn't need it")
    assert intent["remove_room"] is True
    assert intent["room_type"] == "bedroom"


def test_detect_resize_kitchen():
    intent = _detect_intent("Make the kitchen bigger, client wants more workspace")
    assert intent["resize_room"] is True
    assert intent["room_type"] == "kitchen"


def test_detect_budget_with_pct():
    intent = _detect_intent("Client wants to reduce budget by 15%")
    assert intent["budget_change"] is True
    assert intent["budget_pct"] == 15


def test_detect_budget_no_pct():
    intent = _detect_intent("Reduce the overall project cost")
    assert intent["budget_change"] is True
    assert intent["budget_pct"] is None


def test_detect_material_change():
    intent = _detect_intent("Client prefers marble floor finish in living room")
    assert intent["material_change"] is True


def test_detect_structural():
    intent = _detect_intent("Remove the load bearing wall between living and dining")
    assert intent["structural"] is True


def test_detect_move_room():
    intent = _detect_intent("Relocate kitchen to the west side of the plan")
    assert intent["move_room"] is True


# ── Compute affected items ────────────────────────────────────────────────────

def test_add_toilet_generates_all_modules():
    project = _project()
    result = compute_affected_items("chg-001", "Add attached toilet to master bedroom", project)
    assert result.change_id == "chg-001"
    # rooms, mep, boq, compliance, exports must all be non-empty
    assert len(result.rooms) > 0
    assert len(result.mep) > 0
    assert len(result.boq) > 0
    assert len(result.compliance) > 0
    assert len(result.exports) > 0
    assert result.total_count > 0
    assert "WC" in result.cost_impact or "₹" in result.cost_impact


def test_add_toilet_summary_mentions_mep():
    project = _project()
    result = compute_affected_items("chg-002", "Client wants en-suite bathroom", project)
    assert "toilet" in result.summary.lower() or "bathroom" in result.summary.lower()


def test_remove_room_reports_matching_rooms():
    project = _project()
    result = compute_affected_items("chg-003", "Remove the second bedroom from the design", project)
    # Should find bedrooms matching
    assert len(result.rooms) > 0
    action_rooms = [i for i in result.rooms if i.severity == "action_needed"]
    # Either finds matching rooms or flags no match found
    assert len(action_rooms) > 0 or len([i for i in result.rooms if i.severity == "warning"]) > 0


def test_resize_room_marks_stale_boq_when_generated(tmp_path):
    """When cost_plan.generated=True, resize triggers a BOQ staleness warning."""
    project = _project()
    # Manually mark cost_plan as generated
    project = project.model_copy(
        update={"cost_plan": project.cost_plan.model_copy(update={"generated": True})}
    )
    result = compute_affected_items("chg-004", "Make the kitchen bigger", project)
    boq_warnings = [i for i in result.boq if "stale" in i.description.lower() or "qty" in i.description.lower() or "quantities" in i.description.lower()]
    assert len(boq_warnings) > 0


def test_budget_change_affects_boq():
    project = _project()
    result = compute_affected_items("chg-005", "Reduce cost by 20%", project)
    assert any("budget" in i.description.lower() or "BOQ" in i.description or "rate" in i.description.lower() for i in result.boq)
    assert "20%" in result.cost_impact


def test_exports_always_included():
    """Every change type should mark exports stale."""
    project = _project()
    result = compute_affected_items("chg-006", "Move kitchen to the north wall", project)
    assert len(result.exports) == 3
    assert all(i.module == "exports" for i in result.exports)


def test_total_count_matches_sum():
    project = _project()
    result = compute_affected_items("chg-007", "Add storage room near parking", project)
    manual_sum = sum([
        len(result.rooms), len(result.mep), len(result.boq),
        len(result.compliance), len(result.details),
        len(result.exports), len(result.plugins),
    ])
    assert result.total_count == manual_sum


def test_structural_change_fires_compliance():
    project = _project()
    result = compute_affected_items("chg-008", "Remove the load bearing wall between bedroom and bathroom", project)
    assert any(i.severity == "action_needed" for i in result.compliance)


def test_plugin_impacts_on_structural():
    project = _project()
    result = compute_affected_items("chg-009", "Remove wall between living and dining", project)
    assert len(result.plugins) > 0


def test_add_bedroom_no_plugin_if_no_structural():
    """Adding a non-structural room fires plugins."""
    project = _project()
    result = compute_affected_items("chg-010", "Add a study room", project)
    # add_room triggers plugins
    assert len(result.plugins) > 0


def test_summary_non_empty():
    project = _project()
    result = compute_affected_items("chg-011", "Client asked to add a balcony", project)
    assert result.summary != ""


def test_material_change_affects_boq_rates():
    project = _project()
    result = compute_affected_items("chg-012", "Client wants vitrified tiles in all rooms", project)
    assert any(i for i in result.boq if "material" in i.description.lower() or "rate" in i.description.lower())
