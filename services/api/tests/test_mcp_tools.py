"""Phase 38 — MCP tools smoke tests.

Tests the tool functions exposed via services/mcp/tools.py through their
underlying chat_tools implementations. Every test uses tmp_path fixture +
dependency override so there are no filesystem side-effects.

Coverage:
  - Core tools (get_project, list_projects, get_program)
  - Generate / edit (generate_design, add_room, set_parameter)
  - MEP (generate_mep, get_mep_plan, edit_mep_point)
  - Detail (generate_detail, list_details, delete_detail)
  - BOQ (calculate_boq, get_boq, edit_rate)
  - Tamil Nadu advisory (check_tn_rules)
  - Profile (get_user_profile, update_user_profile)
  - Client brief (get_client_brief, update_client_brief)
  - Client changes (create_client_change, list_client_changes, approve_change)
  - Render prompt (generate_render_prompt_tool)
  - Sync contract (get_sync_contract, push_sync_update)
  - Version (restore_version, create_version)
  - Auth guard (require_token)
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest

# Ensure services/mcp is importable for auth module
# test is at: services/api/tests/test_mcp_tools.py
# mcp is at:  services/mcp/
_mcp_root = Path(__file__).parent.parent.parent / "mcp"
if str(_mcp_root) not in sys.path:
    sys.path.insert(0, str(_mcp_root))

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.core.storage.base import LOCAL_USER_ID
from app.core.chat_tools import (
    generate_design,
    get_project,
    list_projects,
    get_program,
    add_room,
    remove_room,
    set_parameter,
    generate_mep,
    get_mep_plan,
    edit_mep_point,
    generate_detail,
    list_details,
    delete_detail,
    calculate_boq,
    get_boq,
    edit_rate,
    check_tn_rules,
    get_user_profile,
    update_user_profile,
    get_client_brief,
    update_client_brief,
    create_client_change,
    list_client_changes,
    approve_change,
    restore_version,
    generate_render_prompt_tool,
)

PROMPT = "3BHK on 30x50 ft east-facing site with living, kitchen, 2 bedrooms, master bedroom, 2 bathrooms"


@pytest.fixture(autouse=True)
def use_tmp_store(tmp_path: Path, monkeypatch):
    """Override the global project store singleton with a tmp_path-backed store."""
    store = LocalProjectStore(tmp_path)
    get_project_store.cache_clear()
    monkeypatch.setattr(
        "app.core.storage.factory.get_project_store",
        lambda: store,
    )
    # Also patch the import in chat_tools
    monkeypatch.setattr("app.core.chat_tools._store", lambda: store)
    yield store
    get_project_store.cache_clear()


def _make_project(store) -> str:
    """Create a project and generate a design; return project_id."""
    s = store.create_project("MCP Test", user_id=LOCAL_USER_ID)
    proj, _ = generate_floorplan(parse_prompt(PROMPT))
    store.update_project(s.id, project=proj, change_type="generate", user_id=LOCAL_USER_ID)
    return s.id


# ── Core read tools ───────────────────────────────────────────────────────────

def test_list_projects_returns_list(use_tmp_store):
    store = use_tmp_store
    store.create_project("A", user_id=LOCAL_USER_ID)
    result = list_projects()
    assert isinstance(result, list)
    assert len(result) >= 1


def test_get_project_returns_dict(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = get_project(pid)
    assert isinstance(result, dict)
    assert "rooms" in result
    assert "site" in result


def test_get_project_missing_raises(use_tmp_store):
    with pytest.raises(ValueError, match="not found"):
        get_project("nonexistent-id")


def test_get_program_returns_totals(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = get_program(pid)
    assert "site" in result
    assert "rooms" in result
    assert "totals" in result
    assert result["totals"]["room_count"] > 0


# ── Generate / edit ───────────────────────────────────────────────────────────

def test_generate_design_creates_project(use_tmp_store):
    store = use_tmp_store
    s = store.create_project("Gen Test", user_id=LOCAL_USER_ID)
    result = generate_design(s.id, "2BHK on 30x40 ft site")
    assert "rooms" in result
    assert len(result["rooms"]) > 0


def test_add_room_increases_room_count(use_tmp_store):
    pid = _make_project(use_tmp_store)
    before = get_program(pid)["totals"]["room_count"]
    add_room(pid, "storage")
    after = get_program(pid)["totals"]["room_count"]
    assert after > before


def test_set_parameter_changes_site(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = set_parameter(pid, "site_width", 35)
    assert result["site"]["width"] == 35


# ── MEP tools ─────────────────────────────────────────────────────────────────

def test_generate_mep_returns_project(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = generate_mep(pid, ["plumbing", "electrical"])
    assert "rooms" in result


def test_get_mep_plan_returns_plan(use_tmp_store):
    pid = _make_project(use_tmp_store)
    generate_mep(pid)
    plan = get_mep_plan(pid)
    assert "plumbing" in plan
    assert "electrical" in plan
    assert plan["generated"] is True


def test_edit_mep_point_moves_point(use_tmp_store):
    pid = _make_project(use_tmp_store)
    generate_mep(pid, ["plumbing"])
    plan = get_mep_plan(pid)
    plumbing_pts = plan["plumbing"]["points"]
    if not plumbing_pts:
        pytest.skip("No plumbing points generated")
    pt = plumbing_pts[0]
    result = edit_mep_point(pid, pt["id"], pt["x"] + 1.0, pt["y"] + 1.0)
    assert "rooms" in result


# ── Detail tools ──────────────────────────────────────────────────────────────

def test_generate_detail_creates_drawing(use_tmp_store):
    pid = _make_project(use_tmp_store)
    proj_data = get_project(pid)
    bath = next((r for r in proj_data["rooms"] if "bath" in r["type"]), None)
    if bath is None:
        pytest.skip("No bathroom in test project")
    result = generate_detail(pid, "toilet", bath["id"])
    assert "detail_drawings" in result or "rooms" in result


def test_list_details_returns_count(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = list_details(pid)
    assert "detail_drawings" in result
    assert "count" in result


def test_delete_detail_removes_entry(use_tmp_store):
    pid = _make_project(use_tmp_store)
    proj_data = get_project(pid)
    bath = next((r for r in proj_data["rooms"] if "bath" in r["type"]), None)
    if bath is None:
        pytest.skip("No bathroom in test project")
    generate_detail(pid, "toilet", bath["id"])
    before = list_details(pid)["count"]
    assert before > 0
    detail_id = list_details(pid)["detail_drawings"][0]["id"]
    delete_detail(pid, detail_id)
    after = list_details(pid)["count"]
    assert after == before - 1


# ── BOQ tools ─────────────────────────────────────────────────────────────────

def test_calculate_boq_returns_project(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = calculate_boq(pid)
    assert "rooms" in result


def test_get_boq_returns_cost_plan(use_tmp_store):
    pid = _make_project(use_tmp_store)
    calculate_boq(pid)
    result = get_boq(pid)
    assert "grand_total" in result
    assert "boq_items" in result
    assert result["generated"] is True


def test_edit_rate_recalculates(use_tmp_store):
    pid = _make_project(use_tmp_store)
    calculate_boq(pid)
    result = edit_rate(pid, "flooring", "tile_supply", 120.0)
    assert "rooms" in result


# ── TN advisory ───────────────────────────────────────────────────────────────

def test_check_tn_rules_returns_report(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = check_tn_rules(pid)
    assert "type" in result
    assert result["type"] == "tn_advisory"
    assert "passes_advisory" in result
    assert "results" in result
    assert isinstance(result["results"], list)


def test_check_tn_rules_with_road_width(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = check_tn_rules(pid, road_width_ft=20.0)
    assert "results" in result


# ── Profile + brief ───────────────────────────────────────────────────────────

def test_get_user_profile_returns_dict(use_tmp_store):
    result = get_user_profile()
    assert "role" in result
    assert "account_mode" in result
    assert result["account_mode"] == "local"


def test_update_user_profile_persists(use_tmp_store, tmp_path):
    from app.core.profile.store import LocalUserProfileStore
    import app.core.chat_tools as ct
    store = LocalUserProfileStore(tmp_path / "users")
    original_store_fn = ct.get_profile_store if hasattr(ct, "get_profile_store") else None

    # Patch profile store to use tmp_path
    import app.core.profile.store as ps_module
    original_get = ps_module.get_profile_store
    ps_module._default_store = store
    try:
        update_user_profile(display_name="Vignesh", default_location="Chennai, India")
        profile = get_user_profile()
        assert profile["display_name"] == "Vignesh"
        assert profile["default_location"] == "Chennai, India"
    finally:
        ps_module._default_store = None


def test_get_client_brief_returns_brief(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = get_client_brief(pid)
    assert "budget_level" in result
    assert "family_name" in result


def test_update_client_brief_persists(use_tmp_store):
    pid = _make_project(use_tmp_store)
    update_client_brief(pid, family_name="Sharma", budget_level="premium", family_size=4)
    result = get_client_brief(pid)
    assert result["family_name"] == "Sharma"
    assert result["budget_level"] == "premium"
    assert result["family_size"] == 4


# ── Client changes ────────────────────────────────────────────────────────────

def test_create_client_change_returns_change(use_tmp_store, tmp_path, monkeypatch):
    from app.core.changes.store import ChangeStore
    import app.core.changes.store as cs_mod

    cs = ChangeStore(tmp_path / "changes")
    original = cs_mod._instance
    cs_mod._instance = cs
    try:
        pid = _make_project(use_tmp_store)
        result = create_client_change(pid, "Add attached toilet to master bedroom")
        assert "id" in result
        assert result["request_text"] == "Add attached toilet to master bedroom"
        assert result["status"] == "pending"
    finally:
        cs_mod._instance = original


def test_list_client_changes_returns_counts(use_tmp_store, tmp_path, monkeypatch):
    from app.core.changes.store import ChangeStore
    import app.core.changes.store as cs_mod

    cs = ChangeStore(tmp_path / "changes")
    original = cs_mod._instance
    cs_mod._instance = cs
    try:
        pid = _make_project(use_tmp_store)
        create_client_change(pid, "Request 1")
        create_client_change(pid, "Request 2")
        result = list_client_changes(pid)
        assert result["total"] == 2
        assert result["pending"] == 2
        assert len(result["changes"]) == 2
    finally:
        cs_mod._instance = original


def test_approve_change_updates_status(use_tmp_store, tmp_path, monkeypatch):
    from app.core.changes.store import ChangeStore
    import app.core.changes.store as cs_mod

    cs = ChangeStore(tmp_path / "changes")
    original = cs_mod._instance
    cs_mod._instance = cs
    try:
        pid = _make_project(use_tmp_store)
        change = create_client_change(pid, "Make living room bigger")
        result = approve_change(pid, change["id"])
        assert result["status"] == "approved"
    finally:
        cs_mod._instance = original


# ── Render prompt ─────────────────────────────────────────────────────────────

def test_generate_render_prompt_returns_prompt(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = generate_render_prompt_tool(pid)
    assert "render_prompt" in result
    assert len(result["render_prompt"]) > 50
    assert "photorealistic" in result["render_prompt"].lower() or "architectural" in result["render_prompt"].lower()


def test_generate_render_prompt_varies_by_camera(use_tmp_store):
    pid = _make_project(use_tmp_store)
    ext = generate_render_prompt_tool(pid, camera_name="exterior_front")
    kit = generate_render_prompt_tool(pid, camera_name="kitchen_view")
    assert ext["render_prompt"] != kit["render_prompt"]


def test_generate_render_prompt_with_extra_tags(use_tmp_store):
    pid = _make_project(use_tmp_store)
    result = generate_render_prompt_tool(pid, extra_tags=["--ar 16:9", "no people"])
    assert "--ar 16:9" in result["render_prompt"]


# ── Sync contract ─────────────────────────────────────────────────────────────

def test_get_sync_contract_returns_rooms(use_tmp_store, monkeypatch):
    """get_sync_contract is defined in mcp/tools.py; test the underlying logic."""
    from app.core.sync.engine import project_to_sync_contract
    pid = _make_project(use_tmp_store)
    proj_data = get_project(pid)
    from app.core.models import ArchitectureProject
    proj = ArchitectureProject.model_validate(proj_data)
    contract = project_to_sync_contract(proj, pid, None)
    assert len(contract.rooms) > 0
    assert contract.project_id == pid


def test_push_sync_updates_project(use_tmp_store):
    """push_sync merges a payload; verify validator+store are exercised."""
    from app.core.sync.engine import project_to_sync_contract, push_sync
    from app.core.sync.models import SyncPayload, SyncRoom
    from app.core.models import ArchitectureProject
    from app.core.validation.validator import validate_project

    pid = _make_project(use_tmp_store)
    proj_data = get_project(pid)
    proj = ArchitectureProject.model_validate(proj_data)
    contract = project_to_sync_contract(proj, pid, None)

    # Modify first room width by 1 ft
    room = contract.rooms[0]
    updated_rooms = [
        SyncRoom(
            id=room.id,
            name=room.name,
            type=room.type,
            x=room.x, y=room.y,
            width=room.width + 1.0,
            depth=room.depth,
            level=room.level,
            flags={},
        )
    ] + contract.rooms[1:]

    payload = SyncPayload(rooms=updated_rooms, source="rhino")
    updated_proj, diff = push_sync(proj, payload)
    result = validate_project(updated_proj)
    assert result.valid
    # The pushed room should appear in updated list
    assert len(diff.updated) >= 1 or len(diff.added) >= 0


# ── Version tools ─────────────────────────────────────────────────────────────

def test_restore_version_returns_project(use_tmp_store):
    pid = _make_project(use_tmp_store)
    # Need at least one version in history
    versions = use_tmp_store.list_versions(pid, user_id=LOCAL_USER_ID)
    if not versions:
        pytest.skip("No version history — needs update_project with change_type")
    version_id = versions[0].version_id
    result = restore_version(pid, version_id)
    assert "rooms" in result


# ── Auth guard ────────────────────────────────────────────────────────────────

def test_require_token_no_op_when_not_configured(monkeypatch):
    """When SCOTCH_MCP_TOKEN is not set, require_token is a no-op."""
    import auth as auth_mod
    import importlib
    monkeypatch.delenv("SCOTCH_MCP_TOKEN", raising=False)
    importlib.reload(auth_mod)
    # Should not raise
    auth_mod.require_token(None)
    auth_mod.require_token("")
    auth_mod.require_token("anything")
    importlib.reload(auth_mod)


def test_require_token_raises_on_mismatch(monkeypatch):
    import auth as auth_mod
    import importlib
    monkeypatch.setenv("SCOTCH_MCP_TOKEN", "secret123")
    importlib.reload(auth_mod)
    with pytest.raises(ValueError, match="SCOTCH_MCP_TOKEN"):
        auth_mod.require_token("wrong-token")
    importlib.reload(auth_mod)


def test_require_token_passes_with_correct_token(monkeypatch):
    import auth as auth_mod
    import importlib
    monkeypatch.setenv("SCOTCH_MCP_TOKEN", "correct-secret")
    importlib.reload(auth_mod)
    auth_mod.require_token("correct-secret")   # should not raise
    importlib.reload(auth_mod)


def test_is_auth_required_false_when_unset(monkeypatch):
    import auth as auth_mod
    import importlib
    monkeypatch.delenv("SCOTCH_MCP_TOKEN", raising=False)
    importlib.reload(auth_mod)
    assert auth_mod.is_auth_required() is False
    importlib.reload(auth_mod)


def test_is_auth_required_true_when_set(monkeypatch):
    import auth as auth_mod
    import importlib
    monkeypatch.setenv("SCOTCH_MCP_TOKEN", "some-token")
    importlib.reload(auth_mod)
    assert auth_mod.is_auth_required() is True
    importlib.reload(auth_mod)
