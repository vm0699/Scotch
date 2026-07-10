"""Tests for Detail Drawing chat/tool integration (Phase 30.5)."""

from pathlib import Path

import pytest

import app.core.chat_tools as ct
from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.chat_tools import delete_detail, generate_detail, list_details
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
    project, _ = generate_floorplan(parse_prompt("2BHK 30x50 east-facing with 2 bathrooms kitchen 2 floors"))
    stored = store.create_project("Detail Test Project")
    store.update_project(stored.id, project=project)
    return stored.id, project


def test_generate_toilet_detail(project_id) -> None:
    pid, project = project_id
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    result = generate_detail(pid, "toilet", bath.id)
    # Returns updated project dict
    drawings = result.get("detail_drawings", [])
    assert any(d["detail_type"] == "toilet" for d in drawings)


def test_generate_tile_layout_detail(project_id) -> None:
    pid, project = project_id
    room = next(r for r in project.rooms if r.type != "stair")
    result = generate_detail(pid, "tile_layout", room.id)
    drawings = result.get("detail_drawings", [])
    assert any(d["detail_type"] == "tile_layout" for d in drawings)


def test_list_details_empty(project_id) -> None:
    pid, _ = project_id
    result = list_details(pid)
    assert result["count"] == 0
    assert result["detail_drawings"] == []


def test_list_details_after_generate(project_id) -> None:
    pid, project = project_id
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    generate_detail(pid, "toilet", bath.id)
    result = list_details(pid)
    assert result["count"] == 1
    assert result["detail_drawings"][0]["detail_type"] == "toilet"


def test_multiple_details_accumulate(project_id) -> None:
    pid, project = project_id
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    room = next(r for r in project.rooms if r.type != "stair")
    generate_detail(pid, "toilet", bath.id)
    generate_detail(pid, "tile_layout", room.id)
    result = list_details(pid)
    assert result["count"] >= 1  # tile_layout may reuse same id if same room


def test_delete_detail(project_id) -> None:
    pid, project = project_id
    bath = next(r for r in project.rooms if r.type in ("bathroom", "master_bathroom"))
    generate_detail(pid, "toilet", bath.id)
    detail_id = list_details(pid)["detail_drawings"][0]["id"]
    delete_detail(pid, detail_id)
    result = list_details(pid)
    assert result["count"] == 0


def test_delete_nonexistent_raises(project_id) -> None:
    pid, _ = project_id
    with pytest.raises(ValueError):
        delete_detail(pid, "nonexistent-id")


def test_invalid_source_id_raises(project_id) -> None:
    pid, _ = project_id
    with pytest.raises(ValueError):
        generate_detail(pid, "toilet", "no-such-room")


def test_generate_detail_nonexistent_project() -> None:
    with pytest.raises(Exception):
        generate_detail("no-such-project", "toilet", "any-room")
