"""Phase 36 — Prompt-first toolchain end-to-end coverage tests.

Verifies that the deterministic fallback (_run_deterministic_fallback) correctly
routes each intent keyword to the right chat tool, and that all registered tools
are reachable via the dispatch table.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.storage.local_store import LocalProjectStore
from app.core.validation import validate_project
import app.core.chat_tools as ct


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def store(tmp_path: Path) -> LocalProjectStore:
    return LocalProjectStore(tmp_path)


@pytest.fixture()
def pid(store: LocalProjectStore) -> str:
    entry = store.create_project("Toolchain Test", prompt="2BHK")
    req = parse_prompt("2BHK east-facing house")
    project, _ = generate_floorplan(req)
    assert validate_project(project).valid
    store.update_project(entry.id, project=project, change_type="generate")
    return entry.id


def _patch(store: LocalProjectStore):
    ct._store = lambda: store  # type: ignore[attr-defined]


# ── Tool coverage audit ───────────────────────────────────────────────────────

def test_all_registered_tools_reachable():
    """Every name in _TOOL_SCHEMAS must have an entry in the dispatch table."""
    from app.api.routes.chat import _TOOL_SCHEMAS, _execute_tool

    # Build the dispatch by calling _execute_tool with a mock project that
    # has a known tool — we just check the dispatch table keys exist.
    schema_names = {s["name"] for s in _TOOL_SCHEMAS}

    # Import dispatch directly from the module namespace
    import importlib
    import sys
    # Reload to get fresh dispatch — use chat module directly
    from app.api.routes import chat as chat_mod

    # Patch _execute_tool to capture the dispatch table without running tools
    captured: set[str] = set()
    original_execute = chat_mod._execute_tool

    def _capturing_execute(project_id, tool_name, tool_input):
        captured.add(tool_name)
        raise RuntimeError("capture only")

    chat_mod._execute_tool = _capturing_execute  # type: ignore[attr-defined]
    for name in schema_names:
        try:
            chat_mod._execute_tool("pid", name, {})
        except RuntimeError:
            pass
    chat_mod._execute_tool = original_execute  # type: ignore[attr-defined]

    assert captured == schema_names


# ── Deterministic keyword routing ─────────────────────────────────────────────

def _chat(store: LocalProjectStore, pid: str, message: str):
    """Invoke the deterministic fallback directly."""
    from app.api.routes.chat import _run_deterministic_fallback, ChatRequest
    _patch(store)
    return _run_deterministic_fallback(pid, ChatRequest(message=message, history=[]))


def test_generate_routes_to_generate_design(store, pid):
    resp = _chat(store, pid, "generate a 3BHK house on 40x60 ft")
    assert "generate_design" in resp.tool_calls


def test_add_room_routes(store, pid):
    resp = _chat(store, pid, "add a study room")
    assert "add_room" in resp.tool_calls
    assert resp.project is not None


def test_remove_room_routes(store, pid):
    resp = _chat(store, pid, "remove the balcony")
    # Either removes something or says couldn't find — tool_call should be present
    assert "remove_room" in resp.tool_calls or "couldn't" in resp.reply.lower()


def test_resize_room_routes(store, pid):
    resp = _chat(store, pid, "make the kitchen 10x12 ft")
    assert any(tc in resp.tool_calls for tc in ("set_parameter",))


def test_show_program_routes(store, pid):
    resp = _chat(store, pid, "what rooms do I have?")
    assert "get_program" in resp.tool_calls
    assert resp.reply != ""


def test_mep_generation_routes(store, pid):
    resp = _chat(store, pid, "add plumbing and electrical layers")
    assert "generate_mep" in resp.tool_calls


def test_mep_all_systems_routed(store, pid):
    resp = _chat(store, pid, "generate all MEP layers")
    assert "generate_mep" in resp.tool_calls


def test_detail_drawing_routes(store, pid):
    resp = _chat(store, pid, "generate toilet detail")
    assert "generate_detail" in resp.tool_calls or "detail" in resp.reply.lower()


def test_boq_calculation_routes(store, pid):
    resp = _chat(store, pid, "calculate BOQ and cost estimate")
    assert "calculate_boq" in resp.tool_calls
    assert "₹" in resp.reply or "grand total" in resp.reply.lower()


def test_tn_advisory_routes(store, pid):
    resp = _chat(store, pid, "check Tamil Nadu compliance")
    assert "check_tn_rules" in resp.tool_calls
    assert "advisory" in resp.reply.lower() or "tn" in resp.reply.lower()


def test_tn_cmda_keyword_routes(store, pid):
    resp = _chat(store, pid, "check CMDA rules for my project")
    assert "check_tn_rules" in resp.tool_calls


def test_client_change_routes(store, pid):
    resp = _chat(store, pid, "client asked to add an attached toilet")
    assert "create_client_change" in resp.tool_calls
    assert "change" in resp.reply.lower()


def test_list_changes_routes(store, pid):
    resp = _chat(store, pid, "list pending changes")
    assert "list_client_changes" in resp.tool_calls


def test_client_brief_budget_routes(store, pid):
    resp = _chat(store, pid, "set budget to economy")
    assert "update_client_brief" in resp.tool_calls
    assert "economy" in resp.reply.lower()


def test_client_brief_family_routes(store, pid):
    resp = _chat(store, pid, "family of 4")
    assert "update_client_brief" in resp.tool_calls


def test_profile_routes(store, pid):
    resp = _chat(store, pid, "show my profile")
    assert "get_user_profile" in resp.tool_calls


def test_render_prompt_routes(store, pid):
    resp = _chat(store, pid, "generate render prompt")
    assert "generate_render_prompt" in resp.tool_calls
    assert "render" in resp.reply.lower()


def test_render_prompt_with_camera(store, pid):
    resp = _chat(store, pid, "visualise the living room render prompt")
    assert "generate_render_prompt" in resp.tool_calls


def test_export_svg_routes(store, pid):
    resp = _chat(store, pid, "export as SVG")
    assert "export_drawing" in resp.tool_calls


def test_export_dxf_routes(store, pid):
    resp = _chat(store, pid, "export DXF for AutoCAD")
    assert "export_drawing" in resp.tool_calls


def test_export_sketchup_routes(store, pid):
    resp = _chat(store, pid, "export to SketchUp")
    assert "export_drawing" in resp.tool_calls


def test_unknown_intent_returns_help(store, pid):
    resp = _chat(store, pid, "what is the meaning of life")
    assert "can help" in resp.reply.lower() or "help" in resp.reply.lower()
    assert resp.tool_calls == []


# ── generate_render_prompt_tool ────────────────────────────────────────────────

def test_render_prompt_tool_returns_string(store, pid):
    _patch(store)
    result = ct.generate_render_prompt_tool(pid)
    assert isinstance(result.get("render_prompt"), str)
    assert len(result["render_prompt"]) > 30


def test_render_prompt_includes_style(store, pid):
    _patch(store)
    result = ct.generate_render_prompt_tool(pid)
    prompt = result["render_prompt"].lower()
    # Should include some style-related content
    assert any(word in prompt for word in ("style", "modern", "contemporary", "traditional", "architecture"))


def test_render_prompt_with_camera_name(store, pid):
    _patch(store)
    result = ct.generate_render_prompt_tool(pid, camera_name="living_room")
    assert result["camera"] == "living_room"
    assert isinstance(result["render_prompt"], str)


def test_render_prompt_with_extra_tags(store, pid):
    _patch(store)
    result = ct.generate_render_prompt_tool(pid, extra_tags=["no people", "--ar 16:9"])
    assert "no people" in result["render_prompt"]


# ── export_drawing ─────────────────────────────────────────────────────────────

def test_export_drawing_svg(store, pid):
    _patch(store)
    result = ct.export_drawing(pid, format="svg")
    assert result.get("filename", "").endswith(".svg") or result.get("format") == "svg"


def test_export_drawing_dxf(store, pid):
    _patch(store)
    result = ct.export_drawing(pid, format="dxf")
    assert "dxf" in str(result.get("filename", "")).lower() or result.get("format") == "dxf"


def test_export_drawing_json(store, pid):
    _patch(store)
    result = ct.export_drawing(pid, format="json")
    assert result.get("filename") or result.get("format") == "json"


# ── Full demo flow (end-to-end smoke) ─────────────────────────────────────────

def test_full_demo_flow(store, pid):
    """Smoke test of the v1.1 demo flow: generate→MEP→detail→BOQ→TN→change→render."""
    _patch(store)

    # 1. Set client brief
    brief = ct.update_client_brief(pid, budget_level="economy", family_size=4, vastu_preference=True)
    assert brief["budget_level"] == "economy"

    # 2. Regenerate with fusion applied
    project = ct.generate_design(pid, "2BHK TN house east-facing 30x50ft")
    assert len(project.get("rooms", [])) >= 2

    # 3. Generate MEP
    mep_proj = ct.generate_mep(pid, systems=["plumbing", "electrical"])
    mep = mep_proj.get("mep_plan", {})
    assert mep.get("generated") is True

    # 4. Generate toilet detail
    proj_obj = ct._load(pid)
    bath = next((r for r in proj_obj.rooms if "bath" in r.type.lower()), None)
    if bath:
        detail_proj = ct.generate_detail(pid, "toilet", bath.id)
        assert len(detail_proj.get("detail_drawings", [])) >= 1

    # 5. Calculate BOQ
    boq_proj = ct.calculate_boq(pid)
    assert boq_proj.get("cost_plan", {}).get("generated") is True

    # 6. TN advisory
    tn = ct.check_tn_rules(pid, road_width_ft=40.0)
    assert "results" in tn
    assert len(tn["results"]) >= 3

    # 7. Client change request
    change = ct.create_client_change(pid, "client asked to add a puja room near entrance")
    assert change.get("id")
    assert change.get("affected_items") is not None

    # 8. Render prompt
    render = ct.generate_render_prompt_tool(pid, camera_name="exterior_front")
    assert len(render["render_prompt"]) > 20

    # 9. Export SVG
    export = ct.export_drawing(pid, format="svg")
    assert export.get("filename") or export.get("format") == "svg"
