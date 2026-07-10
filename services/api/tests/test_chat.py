"""Phase 24.7 — Chat route + MCP tool contract tests.

Covers:
- MCP tool: get_project, list_projects, get_program, list_versions (read)
- MCP tool: generate_design, add_room, remove_room, set_parameter (generate/edit)
- MCP tool: run_intelligence, export_project (intelligence/export)
- Validator gate: invalid room size rejected before commit
- Chat route: deterministic fallback (no API key) — add / remove / resize / show / generate
- Chat route: 404 for missing project
- Chat route: help text when no intent matched
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.sample_factory import create_sample_project
from app.core.chat_tools import (
    add_room,
    generate_design,
    get_program,
    get_project,
    list_projects,
    list_versions,
    remove_room,
    run_intelligence,
    set_parameter,
)
from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def store_path(tmp_path: Path):
    return tmp_path


@pytest.fixture(autouse=True)
def _override_store(tmp_path: Path):
    """Redirect the lru_cache store to a clean tmp_path for every test."""
    get_project_store.cache_clear()
    orig = app.dependency_overrides.copy()
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    # Also patch the module-level factory used by chat_tools
    import app.core.chat_tools as ct
    _orig_store = ct._store
    ct._store = lambda: LocalProjectStore(tmp_path)
    yield
    ct._store = _orig_store
    app.dependency_overrides.clear()
    app.dependency_overrides.update(orig)
    get_project_store.cache_clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def project_id(client: TestClient) -> str:
    """Stored project that has a generated design."""
    proj = client.post("/projects", json={"name": "Chat Test"}).json()
    pid = proj["id"]
    sample = client.get("/projects/sample").json()
    client.patch(f"/projects/{pid}", json={"project": sample})
    return pid


@pytest.fixture
def empty_project_id(client: TestClient) -> str:
    """Stored project with NO design."""
    proj = client.post("/projects", json={"name": "Empty"}).json()
    return proj["id"]


# ── Stage 24.2 — Read tool tests ─────────────────────────────────────────────


def test_get_project_returns_rooms(project_id: str) -> None:
    result = get_project(project_id)
    assert "rooms" in result
    assert len(result["rooms"]) > 0


def test_list_projects_returns_list(project_id: str) -> None:
    projects = list_projects()
    assert isinstance(projects, list)
    assert any(p.get("id") == project_id for p in projects)


def test_get_program_structure(project_id: str) -> None:
    prog = get_program(project_id)
    assert "site" in prog and "rooms" in prog and "totals" in prog
    assert prog["site"]["width"] > 0
    assert len(prog["rooms"]) > 0
    assert prog["totals"]["room_count"] == len(prog["rooms"])
    for r in prog["rooms"]:
        assert r["area"] == pytest.approx(r["width"] * r["depth"], rel=1e-3)


def test_list_versions_returns_list(project_id: str) -> None:
    versions = list_versions(project_id)
    assert isinstance(versions, list)


def test_get_project_missing_raises(project_id: str) -> None:
    with pytest.raises(ValueError, match="not found|no design"):
        get_project("nonexistent-project-xyz")


# ── Stage 24.3 — Generate / edit tool tests ───────────────────────────────────


def test_generate_design_produces_valid_project(project_id: str) -> None:
    result = generate_design(project_id, "2BHK apartment on a 30x50 ft site")
    assert "rooms" in result
    assert len(result["rooms"]) > 0


def test_add_room_increases_count(project_id: str) -> None:
    before = get_program(project_id)["totals"]["room_count"]
    result = add_room(project_id, "bedroom")
    after_count = len(result["rooms"])
    assert after_count == before + 1


def test_add_room_correct_type(project_id: str) -> None:
    result = add_room(project_id, "study")
    types = [r["type"] for r in result["rooms"]]
    assert "study" in types


def test_add_room_with_name(project_id: str) -> None:
    result = add_room(project_id, "bathroom", name="Guest Bath")
    names = [r["name"] for r in result["rooms"]]
    assert "Guest Bath" in names


def test_remove_room_decreases_count(project_id: str) -> None:
    prog = get_program(project_id)
    initial_count = prog["totals"]["room_count"]
    # remove balcony if it exists, else last room
    target = next((r for r in prog["rooms"] if r["type"] == "balcony"), prog["rooms"][-1])
    result = remove_room(project_id, target["id"])
    assert len(result["rooms"]) == initial_count - 1


def test_set_parameter_site_width(project_id: str) -> None:
    result = set_parameter(project_id, "site_width", 35)
    assert result["site"]["width"] == 35


def test_set_parameter_room_width(project_id: str) -> None:
    prog = get_program(project_id)
    living = next(r for r in prog["rooms"] if r["type"] == "living")
    result = set_parameter(project_id, "room_width", 15, target_id=living["id"])
    updated_living = next(r for r in result["rooms"] if r["id"] == living["id"])
    assert updated_living["width"] == 15


def test_validator_gate_rejects_oversized_room(project_id: str) -> None:
    """Setting a room dimension beyond site bounds must raise (validator gate)."""
    prog = get_program(project_id)
    living = next(r for r in prog["rooms"] if r["type"] == "living")
    with pytest.raises((ValueError, Exception)):
        set_parameter(project_id, "room_width", 999, target_id=living["id"])


def test_validator_gate_rejects_invalid_key(project_id: str) -> None:
    with pytest.raises(Exception):
        set_parameter(project_id, "wall_color", "red")


# ── Stage 24.4 — Intelligence + export tools ─────────────────────────────────


def test_run_intelligence_returns_checks(project_id: str) -> None:
    report = run_intelligence(project_id)
    assert "spatial_checks" in report or "area_summary" in report


def test_run_intelligence_vastu(project_id: str) -> None:
    report = run_intelligence(project_id, vastu=True)
    assert isinstance(report, dict)


# ── Stage 24.5 — Chat route (deterministic fallback, no API key) ──────────────


def test_chat_add_room_via_keyword(client: TestClient, project_id: str) -> None:
    before = get_program(project_id)["totals"]["room_count"]
    resp = client.post(
        f"/projects/{project_id}/chat",
        json={"message": "add a study room"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "add_room" in data["tool_calls"]
    assert data["project"] is not None
    assert len(data["project"]["rooms"]) == before + 1


def test_chat_remove_room_via_keyword(client: TestClient, project_id: str) -> None:
    # Add a balcony first so we can remove it
    add_room(project_id, "balcony")
    before = get_program(project_id)["totals"]["room_count"]
    resp = client.post(
        f"/projects/{project_id}/chat",
        json={"message": "remove the balcony"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project"] is not None
    assert len(data["project"]["rooms"]) == before - 1


def test_chat_resize_via_keyword(client: TestClient, project_id: str) -> None:
    resp = client.post(
        f"/projects/{project_id}/chat",
        json={"message": "make the kitchen 10x10"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project"] is not None
    kitchen = next(r for r in data["project"]["rooms"] if r["type"] == "kitchen")
    assert kitchen["width"] == 10


def test_chat_show_program(client: TestClient, project_id: str) -> None:
    resp = client.post(
        f"/projects/{project_id}/chat",
        json={"message": "what rooms do I have?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "get_program" in data["tool_calls"]
    assert len(data["reply"]) > 0


def test_chat_floors_change(client: TestClient, project_id: str) -> None:
    resp = client.post(
        f"/projects/{project_id}/chat",
        json={"message": "change to 2 floors"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "set_parameter" in data["tool_calls"]
    assert data["project"]["building"]["floors"] == 2


def test_chat_help_when_no_intent(client: TestClient, project_id: str) -> None:
    resp = client.post(
        f"/projects/{project_id}/chat",
        json={"message": "xkcd random gibberish zzz"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_calls"] == []
    assert len(data["reply"]) > 0


def test_chat_404_on_missing_project(client: TestClient) -> None:
    resp = client.post(
        "/projects/does-not-exist/chat",
        json={"message": "add a bedroom"},
    )
    assert resp.status_code == 404


def test_chat_history_passed_through(client: TestClient, project_id: str) -> None:
    """History field is accepted without error."""
    resp = client.post(
        f"/projects/{project_id}/chat",
        json={
            "message": "add a study",
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "Hi! How can I help?"},
            ],
        },
    )
    assert resp.status_code == 200
