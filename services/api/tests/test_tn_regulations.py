"""Tests for Tamil Nadu advisory engine — Phase 32.3."""

from __future__ import annotations

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.compliance.tamil_nadu import (
    check_approval_checklist,
    check_ground_coverage,
    check_rainwater_harvesting,
    check_site_completeness,
    check_tn_fsi,
    check_tn_parking,
    check_tn_setbacks,
    check_tn_stair,
    run_tn_advisory,
    _load_rules,
    _load_sources,
)
from app.core.compliance.engine import run_compliance


def _project(prompt="2BHK 30x50 east-facing with 2 bathrooms kitchen 2 floors"):
    p, _ = generate_floorplan(parse_prompt(prompt))
    return p


# ── Source + rule loading ─────────────────────────────────────────────────────

def test_sources_load() -> None:
    sources = _load_sources()
    assert len(sources) > 0
    assert "cmda_dr_2019" in sources


def test_rules_load() -> None:
    rules = _load_rules()
    assert "tn_site_completeness" in rules
    assert "tn_rainwater_harvesting" in rules


# ── Individual checks ─────────────────────────────────────────────────────────

def test_site_completeness_pass() -> None:
    project = _project()
    rules = _load_rules()
    sources = _load_sources()
    result = check_site_completeness(project, road_width_ft=30.0, rules=rules, sources=sources)
    assert result.status == "pass"
    assert result.value is not None


def test_site_completeness_missing_road_width() -> None:
    project = _project()
    rules = _load_rules()
    sources = _load_sources()
    result = check_site_completeness(project, road_width_ft=None, rules=rules, sources=sources)
    assert result.status == "missing_input"
    assert any("road" in m.lower() for m in result.missing_inputs)


def test_tn_setback_missing_road_width() -> None:
    project = _project()
    rules = _load_rules()
    sources = _load_sources()
    result = check_tn_setbacks(project, road_width_ft=None, rules=rules, sources=sources)
    assert result.status == "missing_input"


def test_tn_setback_with_road_width() -> None:
    project = _project()
    rules = _load_rules()
    sources = _load_sources()
    result = check_tn_setbacks(project, road_width_ft=30.0, rules=rules, sources=sources)
    assert result.status in ("advisory", "warn")
    assert result.source_name  # has source attribution


def test_tn_fsi_returns_value() -> None:
    project = _project()
    rules = _load_rules()
    sources = _load_sources()
    result = check_tn_fsi(project, rules=rules, sources=sources)
    assert result.value is not None
    assert result.limit == 1.5


def test_tn_fsi_has_zone_in_missing_inputs() -> None:
    project = _project()
    rules = _load_rules()
    sources = _load_sources()
    result = check_tn_fsi(project, rules=rules, sources=sources)
    assert "zone_classification" in result.missing_inputs


def test_ground_coverage_returns_pct() -> None:
    project = _project()
    rules = _load_rules()
    sources = _load_sources()
    result = check_ground_coverage(project, rules=rules, sources=sources)
    assert result.unit == "%"
    assert result.value is not None
    assert 0 <= result.value <= 100


def test_parking_2bhk_warns_without_parking() -> None:
    project = _project("2BHK 30x50")
    # Remove any parking room for this test
    import copy
    p = copy.copy(project)
    p = p.model_copy(update={"rooms": [r for r in p.rooms if r.type != "parking"]})
    rules = _load_rules()
    sources = _load_sources()
    result = check_tn_parking(p, rules=rules, sources=sources)
    assert result.status == "warn"


def test_parking_skip_for_studio() -> None:
    project = _project("studio 20x25")
    rules = _load_rules()
    sources = _load_sources()
    result = check_tn_parking(project, rules=rules, sources=sources)
    assert result.status == "skip"


def test_rainwater_harvesting_mandatory_large_plot() -> None:
    project = _project("2BHK 60x60")  # 3600 sqft > 2400 sqft threshold
    rules = _load_rules()
    sources = _load_sources()
    result = check_rainwater_harvesting(project, rules=rules, sources=sources)
    assert result.status == "warn"
    assert "MANDATORY" in result.message.upper() or "mandatory" in result.message


def test_rainwater_harvesting_advisory_small_plot() -> None:
    project = _project("studio 20x30")  # 600 sqft < 2400 sqft threshold
    rules = _load_rules()
    sources = _load_sources()
    result = check_rainwater_harvesting(project, rules=rules, sources=sources)
    assert result.status == "advisory"


def test_stair_advisory_multistorey() -> None:
    project = _project("2BHK 30x50 2 floors")
    rules = _load_rules()
    sources = _load_sources()
    result = check_tn_stair(project, rules=rules, sources=sources)
    # Should be advisory or warn (stair room may or may not be present)
    assert result.status in ("advisory", "warn", "skip")


def test_approval_checklist_has_items() -> None:
    project = _project()
    rules = _load_rules()
    sources = _load_sources()
    result = check_approval_checklist(project, rules=rules, sources=sources)
    assert result.status == "advisory"
    assert len(result.advisory_items) >= 5


# ── Full advisory run ─────────────────────────────────────────────────────────

def test_run_tn_advisory_returns_report() -> None:
    project = _project()
    report = run_tn_advisory(project, "test-id")
    assert report.project_id == "test-id"
    assert len(report.results) > 0
    assert report.disclaimer


def test_run_tn_advisory_all_rules_run() -> None:
    project = _project()
    report = run_tn_advisory(project, "test-id")
    rule_ids = {r.rule_id for r in report.results}
    expected = {
        "tn_site_completeness", "tn_setback_advisory", "tn_fsi_advisory",
        "tn_ground_coverage", "tn_parking_advisory",
        "tn_rainwater_harvesting", "tn_stair_advisory", "tn_approval_checklist",
    }
    assert expected == rule_ids


def test_run_tn_advisory_with_road_width() -> None:
    project = _project()
    report = run_tn_advisory(project, "test-id", road_width_ft=30.0)
    site_check = next(r for r in report.results if r.rule_id == "tn_site_completeness")
    assert site_check.status == "pass"


def test_run_tn_advisory_all_results_have_source() -> None:
    project = _project()
    report = run_tn_advisory(project, "test-id")
    for result in report.results:
        assert result.source_name, f"Result '{result.rule_id}' has no source_name"


def test_run_tn_advisory_all_results_have_verification_flag() -> None:
    project = _project()
    report = run_tn_advisory(project, "test-id")
    for result in report.results:
        # All results must explicitly set needs_professional_verification
        assert isinstance(result.needs_professional_verification, bool)


def test_nbc_compliance_unaffected_by_tn() -> None:
    """NBC checks must still pass independently — TN engine must not break existing NBC."""
    project = _project()
    nbc_report = run_compliance(project, "test-id")
    tn_report = run_tn_advisory(project, "test-id")
    assert nbc_report.project_id == "test-id"
    assert tn_report.project_id == "test-id"
    # NBC report still has all the expected keys
    assert hasattr(nbc_report, "passes_review")
    assert hasattr(nbc_report, "rules")


def test_missing_inputs_reported_in_summary() -> None:
    project = _project()
    report = run_tn_advisory(project, "test-id", road_width_ft=None)
    assert len(report.missing_inputs) > 0


def test_summary_not_empty() -> None:
    project = _project()
    report = run_tn_advisory(project, "test-id")
    assert len(report.summary) > 10
