"""Tests for TN advisory chat tool — Phase 32.5."""

from __future__ import annotations
from pathlib import Path

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.storage.local_store import LocalProjectStore
import app.core.chat_tools as ct


# ── Fixtures (same pattern as test_boq_chat.py) ───────────────────────────────

@pytest.fixture(autouse=True)
def _tmp_store(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    orig = ct._store
    ct._store = lambda: store
    yield store
    ct._store = orig


@pytest.fixture()
def pid(_tmp_store):
    project, _ = generate_floorplan(
        parse_prompt("2BHK 30x50 east-facing kitchen 2 bathrooms 2 floors")
    )
    stored = _tmp_store.create_project("TN Test", prompt="2BHK")
    _tmp_store.update_project(stored.id, project=project)
    return stored.id


# ── check_tn_rules ────────────────────────────────────────────────────────────

def test_check_tn_rules_returns_dict(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert isinstance(result, dict)


def test_check_tn_rules_has_type_field(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert result.get("type") == "tn_advisory"


def test_check_tn_rules_has_summary(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert isinstance(result.get("summary"), str)
    assert len(result["summary"]) > 5


def test_check_tn_rules_has_results_list(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert isinstance(result.get("results"), list)
    assert len(result["results"]) > 0


def test_check_tn_rules_has_disclaimer(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert isinstance(result.get("disclaimer"), str)
    assert len(result["disclaimer"]) > 10


def test_check_tn_rules_has_passes_advisory(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert isinstance(result.get("passes_advisory"), bool)


def test_check_tn_rules_has_missing_inputs(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert isinstance(result.get("missing_inputs"), list)


def test_check_tn_rules_with_road_width(pid) -> None:
    result = ct.check_tn_rules(pid, road_width_ft=30.0)
    results_list = result.get("results", [])
    site_check = next((r for r in results_list if r["rule_id"] == "tn_site_completeness"), None)
    assert site_check is not None
    assert site_check["status"] == "pass"


def test_check_tn_rules_without_road_width_has_missing_inputs(pid) -> None:
    result = ct.check_tn_rules(pid, road_width_ft=0.0)
    missing = result.get("missing_inputs", [])
    assert len(missing) > 0


def test_check_tn_rules_result_count_matches(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert result["result_count"] == len(result["results"])


def test_check_tn_rules_warn_count_is_int(pid) -> None:
    result = ct.check_tn_rules(pid)
    assert isinstance(result.get("warn_count"), int)
    assert result["warn_count"] >= 0


def test_check_tn_rules_all_results_have_source(pid) -> None:
    result = ct.check_tn_rules(pid)
    for r in result["results"]:
        assert r.get("source_name"), f"Result '{r['rule_id']}' has no source_name"


def test_check_tn_rules_does_not_mutate_project(pid, _tmp_store) -> None:
    before = _tmp_store.get_project(pid)
    ct.check_tn_rules(pid)
    after = _tmp_store.get_project(pid)
    assert before.project == after.project
