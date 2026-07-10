"""Phase 38 — Scotch standalone MCP server (expanded).

Run:
    cd services/mcp && python server.py          # stdio transport (Claude Desktop)
    cd services/mcp && python server.py --sse    # SSE transport (web clients)

Tools cover:
  Phase 24 — basic project CRUD, generate, intelligence, export, render, restore
  Phase 29 — MEP generation + editing
  Phase 30 — detail drawings (generate / list / delete)
  Phase 31 — BOQ / cost (calculate / edit rate / edit tile spec / get)
  Phase 32 — Tamil Nadu advisory
  Phase 33 — user profile + client brief
  Phase 34 — client change management (create / list / approve / reject / revert / show impact)
  Phase 35 — render prompt generation
  Phase 37 — account mode (profile fields)
  Phase 38 — sync contract pull/push, chat edit, manual version create

Auth:
  Set SCOTCH_MCP_TOKEN env var (in server env and MCP client config) to require
  a token on mutating tools.  Omit to use local trust mode (default).

External agent setup:
  See docs/integrations/mcp-external-agents.md
"""

from __future__ import annotations

import sys
import os

# Ensure services/api is on the Python path when run from services/mcp
_api_root = os.path.join(os.path.dirname(__file__), "..", "api")
if _api_root not in sys.path:
    sys.path.insert(0, _api_root)

from typing import Any

from mcp.server.fastmcp import FastMCP

import tools  # relative import from same directory
from auth import require_token

mcp = FastMCP(
    "Scotch",
    instructions=(
        "You are an architectural design assistant for Scotch. "
        "Use the available tools to read and modify floor plans, MEP layers, "
        "detail drawings, BOQ/cost, Tamil Nadu advisories, client changes, "
        "and exports. Always validate designs before reporting success. "
        "project_id is required for all project-specific tools. "
        "Mutating tools accept an optional _token parameter when the server "
        "is configured with SCOTCH_MCP_TOKEN."
    ),
)


# ── Phase 24 — Read tools ─────────────────────────────────────────────────────


@mcp.tool()
def get_project(project_id: str) -> dict:
    """Get the full ArchitectureProject model for a stored project."""
    return tools.get_project(project_id)


@mcp.tool()
def list_projects() -> list[dict]:
    """List all stored projects with summary info."""
    return tools.list_projects()


@mcp.tool()
def get_program(project_id: str) -> dict:
    """Get the design program: site info, room list with dimensions, area totals."""
    return tools.get_program(project_id)


@mcp.tool()
def list_versions(project_id: str) -> list[dict]:
    """List version history snapshots for a project."""
    return tools.list_versions(project_id)


# ── Phase 24 — Generate / edit tools ─────────────────────────────────────────


@mcp.tool()
def generate_design(project_id: str, prompt: str, mode: str = "deterministic") -> dict:
    """Generate a new floor plan from a natural-language prompt and save it."""
    return tools.generate_design(project_id, prompt, mode)


@mcp.tool()
def add_room(project_id: str, room_type: str, name: str = "") -> dict:
    """Add a room to the floor plan. room_type: bedroom|bathroom|kitchen|living|study|storage|balcony|parking."""
    return tools.add_room(project_id, room_type, name)


@mcp.tool()
def remove_room(project_id: str, room_id: str) -> dict:
    """Remove a room from the floor plan by its stable ID (e.g. 'bed-master', 'bath-1')."""
    return tools.remove_room(project_id, room_id)


@mcp.tool()
def set_parameter(project_id: str, key: str, value: Any, target_id: str = "") -> dict:
    """Edit a parameter. key: site_width|site_depth|orientation|floors|floor_height|style|room_width|room_depth|room_name. target_id required for room-level keys."""
    return tools.set_parameter(project_id, key, value, target_id)


# ── Phase 24 — Intelligence + export tools ───────────────────────────────────


@mcp.tool()
def run_intelligence(project_id: str, vastu: bool = False) -> dict:
    """Run spatial analysis and optional Vastu Shastra checks on the design."""
    return tools.run_intelligence(project_id, vastu)


@mcp.tool()
def export_project(project_id: str, format: str) -> dict:
    """Export the project. format: json|svg|png|dxf|ifc|sketchup|blender|rhino|sheet_svg|sheet_pdf."""
    return tools.export_project(project_id, format)


@mcp.tool()
def render_project(project_id: str, camera_id: str, style: str) -> dict:
    """Render the massing. style: photorealistic_exterior|architectural_sketch|warm_interior|night_render|pencil_line."""
    return tools.render_project(project_id, camera_id, style)


@mcp.tool()
def restore_version(project_id: str, version_id: str) -> dict:
    """Restore the project to a previous version snapshot."""
    return tools.restore_version(project_id, version_id)


# ── Phase 29 — MEP ───────────────────────────────────────────────────────────


@mcp.tool()
def generate_mep(
    project_id: str,
    systems: list[str] | None = None,
) -> dict:
    """Generate MEP service points. systems: list of plumbing|electrical|lighting|ac (default: all four)."""
    return tools.generate_mep(project_id, systems)


@mcp.tool()
def edit_mep_point(project_id: str, point_id: str, x: float, y: float) -> dict:
    """Move a MEP service point to new coordinates. Marks the point as user-override."""
    return tools.edit_mep_point(project_id, point_id, x, y)


@mcp.tool()
def get_mep_plan(project_id: str) -> dict:
    """Return the current MEP plan (all four systems)."""
    return tools.get_mep_plan(project_id)


# ── Phase 30 — Detail Drawings ───────────────────────────────────────────────


@mcp.tool()
def generate_detail(project_id: str, detail_type: str, source_id: str) -> dict:
    """Generate a detail drawing. detail_type: toilet|kitchen|door_window|wall_section|tile_layout|stair. source_id: room/door/window id."""
    return tools.generate_detail(project_id, detail_type, source_id)


@mcp.tool()
def list_details(project_id: str) -> dict:
    """List all detail drawings for a project."""
    return tools.list_details(project_id)


@mcp.tool()
def delete_detail(project_id: str, detail_id: str) -> dict:
    """Remove a detail drawing by id."""
    return tools.delete_detail(project_id, detail_id)


# ── Phase 31 — BOQ / Cost ────────────────────────────────────────────────────


@mcp.tool()
def calculate_boq(project_id: str) -> dict:
    """Calculate the Bill of Quantities and cost plan. Uses room areas, MEP counts, and default INR rates."""
    return tools.calculate_boq(project_id)


@mcp.tool()
def get_boq(project_id: str) -> dict:
    """Return the current cost plan / BOQ for a project."""
    return tools.get_boq(project_id)


@mcp.tool()
def edit_rate(project_id: str, category: str, item: str, rate: float) -> dict:
    """Update a single rate in the project's rate table and recalculate BOQ. category: flooring|paint|plumbing|electrical|doors|windows."""
    return tools.edit_rate(project_id, category, item, rate)


@mcp.tool()
def edit_tile_spec(
    project_id: str,
    tile_spec_id: str,
    size_w: float | None = None,
    size_h: float | None = None,
    rate_per_sqft: float | None = None,
    wastage_pct: float | None = None,
) -> dict:
    """Edit a tile specification and recalculate BOQ. Pass only the fields to update."""
    return tools.edit_tile_spec(project_id, tile_spec_id, size_w, size_h, rate_per_sqft, wastage_pct)


# ── Phase 32 — Tamil Nadu Advisory ───────────────────────────────────────────


@mcp.tool()
def check_tn_rules(project_id: str, road_width_ft: float = 0.0) -> dict:
    """Run Tamil Nadu advisory checks (CMDA/DTCP). Advisory only — not engineering certification. road_width_ft: 0 = not specified."""
    return tools.check_tn_rules(project_id, road_width_ft)


# ── Phase 33 — Profile + Client Brief ────────────────────────────────────────


@mcp.tool()
def get_user_profile() -> dict:
    """Return the stored architect-twin profile for the local user."""
    return tools.get_user_profile()


@mcp.tool()
def update_user_profile(
    role: str | None = None,
    preferred_units: str | None = None,
    default_location: str | None = None,
    default_style: str | None = None,
    explanation_style: str | None = None,
    display_name: str | None = None,
) -> dict:
    """Update the architect-twin profile. role: owner|architect|student|other. preferred_units: feet|meters."""
    return tools.update_user_profile(
        role=role,
        preferred_units=preferred_units,
        default_location=default_location,
        default_style=default_style,
        explanation_style=explanation_style,
        display_name=display_name,
    )


@mcp.tool()
def get_client_brief(project_id: str) -> dict:
    """Return the client brief attached to a project."""
    return tools.get_client_brief(project_id)


@mcp.tool()
def update_client_brief(
    project_id: str,
    family_name: str | None = None,
    family_size: int | None = None,
    lifestyle: str | None = None,
    budget_level: str | None = None,
    style_preference: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update the client brief on a project. budget_level: economy|standard|premium."""
    return tools.update_client_brief(
        project_id,
        family_name=family_name,
        family_size=family_size,
        lifestyle=lifestyle,
        budget_level=budget_level,
        style_preference=style_preference,
        notes=notes,
    )


# ── Phase 34 — Client Change Management ──────────────────────────────────────


@mcp.tool()
def create_client_change(
    project_id: str,
    request_text: str,
    source: str = "client",
    priority: str = "medium",
) -> dict:
    """Create a client change request and compute affected items. priority: low|medium|high|urgent."""
    return tools.create_client_change(project_id, request_text, source, priority)


@mcp.tool()
def list_client_changes(project_id: str) -> dict:
    """List all client change requests for a project with status counts."""
    return tools.list_client_changes(project_id)


@mcp.tool()
def approve_change(project_id: str, change_id: str) -> dict:
    """Approve a pending client change request."""
    return tools.approve_change(project_id, change_id)


@mcp.tool()
def reject_change(project_id: str, change_id: str, reason: str = "") -> dict:
    """Reject a client change request."""
    return tools.reject_change(project_id, change_id, reason)


@mcp.tool()
def revert_change(project_id: str, change_id: str) -> dict:
    """Revert an applied change to the before-change version snapshot."""
    return tools.revert_change(project_id, change_id)


@mcp.tool()
def show_affected_items(project_id: str, change_id: str) -> dict:
    """Return the full affected-item report for a change request."""
    return tools.show_affected_items(project_id, change_id)


# ── Phase 35 — Render Prompt ─────────────────────────────────────────────────


@mcp.tool()
def generate_render_prompt(
    project_id: str,
    camera_name: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict:
    """Generate a context-aware photorealistic render prompt. camera_name: exterior_front|living_room|master_bedroom|kitchen_view|bathroom_view|aerial_view."""
    return tools.generate_render_prompt_tool(project_id, camera_name, extra_tags)


@mcp.tool()
def export_drawing(project_id: str, format: str = "svg") -> dict:
    """Export a drawing file. format: svg|dxf|png|json|sketchup|blender|rhino|ifc|sheet_svg|sheet_pdf."""
    return tools.export_drawing(project_id, format)


# ── Phase 38 — Sync contract, chat edit, manual version ──────────────────────


@mcp.tool()
def get_sync_contract(project_id: str) -> dict:
    """Return the SyncContract projection for a project. Used by SketchUp, Revit, and Rhino plugins to pull canonical geometry."""
    return tools.get_sync_contract(project_id)


@mcp.tool()
def push_sync_update(project_id: str, payload: dict) -> dict:
    """Merge a plugin sync payload into the canonical model. payload: {rooms: [...], source: 'sketchup'|'revit'|'rhino'}."""
    return tools.push_sync_update(project_id, payload)


@mcp.tool()
def chat_edit_project(project_id: str, message: str, _token: str | None = None) -> dict:
    """Run a natural-language chat edit on a project (same as the in-app chat panel). Returns tool-call summary + updated project."""
    return tools.chat_edit_project(project_id, message, token=_token)


@mcp.tool()
def create_version(project_id: str, note: str = "", _token: str | None = None) -> dict:
    """Create a named version snapshot for a project. Returns the version metadata."""
    return tools.create_version(project_id, note, token=_token)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    transport = "sse" if "--sse" in sys.argv else "stdio"
    mcp.run(transport=transport)
