"""Tests for MEP chat/tool integration (Phase 29.5)."""

from pathlib import Path

import pytest

import app.core.chat_tools as ct
from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.chat_tools import edit_mep_point, generate_mep, get_mep_plan
from app.core.storage.local_store import LocalProjectStore


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    orig = ct._store
    ct._store = lambda: store
    yield store
    ct._store = orig


@pytest.fixture()
def stored_project_id(_tmp_store):
    store = _tmp_store
    project, _ = generate_floorplan(parse_prompt("2BHK 30x50 east-facing with 2 bathrooms kitchen"))
    stored = store.create_project("Test MEP Project")
    store.update_project(stored.id, project=project)
    return stored.id


def test_generate_mep_tool_sets_generated(stored_project_id) -> None:
    result = generate_mep(stored_project_id)
    # _save returns project.model_dump() — check mep_plan.generated
    assert result.get("mep_plan", {}).get("generated") is True


def test_generate_mep_tool_specific_systems(stored_project_id) -> None:
    result = generate_mep(stored_project_id, systems=["lighting"])
    mep = result.get("mep_plan", {})
    assert len(mep.get("lighting", {}).get("points", [])) > 0
    # Plumbing not generated — should be empty
    assert mep.get("plumbing", {}).get("points", []) == []


def test_generate_mep_all_systems_have_points(stored_project_id) -> None:
    result = generate_mep(stored_project_id)
    mep = result.get("mep_plan", {})
    assert len(mep.get("lighting", {}).get("points", [])) > 0
    assert len(mep.get("electrical", {}).get("points", [])) > 0


def test_get_mep_plan_tool(stored_project_id) -> None:
    generate_mep(stored_project_id)
    mep_data = get_mep_plan(stored_project_id)
    # Returns mep_plan.model_dump()
    assert "plumbing" in mep_data
    assert "electrical" in mep_data
    assert "lighting" in mep_data
    assert "ac" in mep_data
    assert mep_data["generated"] is True


def test_edit_mep_point_tool(stored_project_id, _tmp_store) -> None:
    generate_mep(stored_project_id)
    mep_data = get_mep_plan(stored_project_id)
    # Pick the first lighting point
    pt = mep_data["lighting"]["points"][0]
    result = edit_mep_point(stored_project_id, pt["id"], 3.0, 4.0)
    mep_after = result.get("mep_plan", {})
    moved = next(p for p in mep_after["lighting"]["points"] if p["id"] == pt["id"])
    assert moved["user_override"] is True
    assert moved["x"] == 3.0
    assert moved["y"] == 4.0


def test_edit_mep_point_invalid_id_raises(stored_project_id) -> None:
    generate_mep(stored_project_id)
    with pytest.raises(ValueError):
        edit_mep_point(stored_project_id, "bad-id-xyz", 0.0, 0.0)


def test_generate_mep_nonexistent_project_raises() -> None:
    with pytest.raises(Exception):
        generate_mep("nonexistent-project-id")


def test_override_preserved_after_regen(stored_project_id) -> None:
    generate_mep(stored_project_id)
    mep_data = get_mep_plan(stored_project_id)
    pt = mep_data["plumbing"]["points"][0]
    # Move the point (marks user_override=True)
    edit_mep_point(stored_project_id, pt["id"], 99.0, 99.0)
    # Regen plumbing only
    result2 = generate_mep(stored_project_id, systems=["plumbing"])
    plumbing_pts = result2["mep_plan"]["plumbing"]["points"]
    overrides = [p for p in plumbing_pts if p["user_override"]]
    assert any(p["id"] == pt["id"] for p in overrides)
    moved = next(p for p in plumbing_pts if p["id"] == pt["id"])
    assert moved["x"] == 99.0 and moved["y"] == 99.0
