"""Phase 24.5 — In-app agentic chat endpoint.

POST /projects/{project_id}/chat
  Request:  {message, history?}
  Response: {reply, project?, tool_calls}

Agentic loop:
  1. Call Claude with the message + available tool schemas + conversation history.
  2. Execute any tool_use blocks (calling services/mcp/tools.py directly).
  3. Feed tool_results back, loop until Claude returns plain text.
  4. Return the final text + any mutated project.

Deterministic fallback (no Anthropic key): keyword-based intent parsing.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import app.core.chat_tools as mcp_tools
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(prefix="/projects", tags=["chat"])

# ── Anthropic tool schemas ────────────────────────────────────────────────────

_TOOL_SCHEMAS = [
    {
        "name": "generate_design",
        "description": "Generate a new floor plan from a natural-language prompt.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Natural language description of the building"},
                "mode": {"type": "string", "enum": ["deterministic", "ai", "hybrid"], "description": "Generation mode (default: deterministic)"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "add_room",
        "description": "Add a new room to the floor plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "room_type": {
                    "type": "string",
                    "enum": ["bedroom", "bathroom", "kitchen", "living", "study", "storage", "balcony", "parking", "stair"],
                    "description": "Type of room to add",
                },
                "name": {"type": "string", "description": "Optional display name for the room"},
            },
            "required": ["room_type"],
        },
    },
    {
        "name": "remove_room",
        "description": "Remove a room from the floor plan by its stable ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "room_id": {"type": "string", "description": "Stable room ID (e.g. 'bed-master', 'bath-1', 'living')"},
            },
            "required": ["room_id"],
        },
    },
    {
        "name": "set_parameter",
        "description": "Edit a project or room parameter. For room dimensions/name, provide target_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "enum": [
                        "site_width", "site_depth", "orientation", "floors",
                        "floor_height", "style", "room_width", "room_depth",
                        "room_name", "room_level",
                    ],
                    "description": "Parameter to change",
                },
                "value": {"description": "New value (number for dimensions, string for orientation/style)"},
                "target_id": {"type": "string", "description": "Room ID — required for room_width / room_depth / room_name / room_level"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "get_program",
        "description": "Get the current design program (site info, all rooms with dimensions, area totals).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_mep",
        "description": "Generate MEP (plumbing, electrical, lighting, AC) service points and advisory routes. Specify systems to target or omit for all four.",
        "input_schema": {
            "type": "object",
            "properties": {
                "systems": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["plumbing", "electrical", "lighting", "ac"]},
                    "description": "Systems to generate (default: all four)",
                },
            },
        },
    },
    {
        "name": "edit_mep_point",
        "description": "Move a MEP service point to new coordinates. The point is then marked user_override and preserved on regeneration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "point_id": {"type": "string", "description": "ID of the service point to move"},
                "x": {"type": "number", "description": "New x coordinate in plan units"},
                "y": {"type": "number", "description": "New y coordinate in plan units"},
            },
            "required": ["point_id", "x", "y"],
        },
    },
    {
        "name": "get_mep_plan",
        "description": "Return the current MEP plan (all service points and routes, with confidence and needs_review flags).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_detail",
        "description": "Generate a detail drawing (toilet plan, kitchen layout, door/window elevation, wall section, tile layout, stair section) from a source object in the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "detail_type": {
                    "type": "string",
                    "enum": ["toilet", "kitchen", "door_window", "wall_section", "tile_layout", "stair"],
                    "description": "Type of detail drawing to generate",
                },
                "source_id": {
                    "type": "string",
                    "description": "ID of the Room, Door, Window, or StairEntity to detail",
                },
            },
            "required": ["detail_type", "source_id"],
        },
    },
    {
        "name": "list_details",
        "description": "List all detail drawings for the current project.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "delete_detail",
        "description": "Remove a detail drawing by its id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "detail_id": {"type": "string", "description": "ID of the detail drawing to remove"},
            },
            "required": ["detail_id"],
        },
    },
    {
        "name": "run_intelligence",
        "description": "Run spatial and Vastu analysis on the current design.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vastu": {"type": "boolean", "description": "Include Vastu Shastra checks"},
            },
        },
    },
    # Phase 31 — BOQ / Cost
    {
        "name": "calculate_boq",
        "description": "Calculate Bill of Quantities and cost plan using room areas, opening counts, MEP fixture counts, and editable rate table.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_boq",
        "description": "Return the current BOQ and cost summary (grand total, category totals, missing rates, assumptions).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "edit_rate",
        "description": "Update a single rate in the BOQ rate table and recalculate costs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Rate category e.g. flooring, paint, plumbing, electrical, doors, windows"},
                "item":     {"type": "string", "description": "Rate item e.g. tile_supply, interior_paint, wc, interior_door"},
                "rate":     {"type": "number", "description": "New rate in INR per unit"},
            },
            "required": ["category", "item", "rate"],
        },
    },
    {
        "name": "edit_tile_spec",
        "description": "Edit a tile specification (size or rate) and recalculate tile quantities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tile_spec_id":  {"type": "string", "description": "ID of the tile spec to edit"},
                "size_w":        {"type": "number", "description": "Tile width in inches"},
                "size_h":        {"type": "number", "description": "Tile height in inches"},
                "rate_per_sqft": {"type": "number", "description": "Supply rate per sqft in INR"},
                "wastage_pct":   {"type": "number", "description": "Wastage percentage (e.g. 10 for 10%)"},
            },
            "required": ["tile_spec_id"],
        },
    },
    {
        "name": "check_tn_rules",
        "description": (
            "Run Tamil Nadu advisory checks (CMDA/DTCP setback, FSI, ground coverage, "
            "parking, rainwater harvesting, stair, approval checklist). "
            "Advisory only — not engineering certification. Returns source-backed results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "road_width_ft": {
                    "type": "number",
                    "description": "Road frontage width in feet (0 or omit if unknown)",
                },
            },
            "required": [],
        },
    },
    # Phase 33 — Profile + client brief
    {
        "name": "get_user_profile",
        "description": "Return the architect-twin profile for the current user (role, style, orientation, location preferences).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_user_profile",
        "description": "Update one or more fields on the user architect-twin profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role":                {"type": "string", "enum": ["owner", "architect", "student", "other"]},
                "preferred_units":     {"type": "string", "enum": ["feet", "meters"]},
                "default_location":    {"type": "string", "description": "Default design location (e.g. 'Tamil Nadu, India')"},
                "default_style":       {"type": "string", "description": "Preferred architectural style (e.g. 'contemporary', 'vernacular')"},
                "default_orientation": {"type": "string", "enum": ["north", "south", "east", "west"]},
                "explanation_style":   {"type": "string", "enum": ["brief", "detailed"]},
            },
        },
    },
    {
        "name": "get_client_brief",
        "description": "Return the client brief attached to the project (family, budget, style, Vastu, parking preferences).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_client_brief",
        "description": "Update the client brief for the project. Budget level influences room sizes on next generation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "family_name":        {"type": "string"},
                "family_size":        {"type": "integer", "description": "Number of family members"},
                "lifestyle":          {"type": "string", "description": "e.g. 'nuclear family', 'joint family', 'young professional'"},
                "budget_level":       {"type": "string", "enum": ["economy", "standard", "premium"]},
                "budget_inr":         {"type": "number", "description": "Total construction budget in INR"},
                "style_preference":   {"type": "string", "description": "e.g. 'contemporary', 'traditional', 'minimal'"},
                "vastu_preference":   {"type": "boolean"},
                "parking_preference": {"type": "string", "enum": ["none", "two_wheeler", "car", "both"]},
                "future_expansion":   {"type": "boolean"},
                "material_preference":{"type": "string"},
                "notes":              {"type": "string"},
            },
        },
    },
    # Phase 34 — Client Change Management
    {
        "name": "create_client_change",
        "description": (
            "Create a client change request and immediately compute affected items — which rooms, MEP, BOQ, "
            "compliance rules, detail drawings, exports, and plugins are impacted. "
            "Use for: 'client asked to add attached toilet', 'reduce budget by 10%', 'make kitchen bigger', "
            "'move bedroom to back', 'show impact of this change'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "request_text": {"type": "string", "description": "Client's change request in natural language"},
                "source": {"type": "string", "enum": ["client", "architect", "chat", "manual"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
            },
            "required": ["request_text"],
        },
    },
    {
        "name": "show_affected_items",
        "description": "Show the full affected-item report for an existing change request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "change_id": {"type": "string", "description": "Change request ID from create_client_change"},
            },
            "required": ["change_id"],
        },
    },
    {
        "name": "list_client_changes",
        "description": "List all client change requests for the current project with status, summary, and affected modules.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_change",
        "description": "Approve a pending client change request so it is ready to be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "change_id": {"type": "string"},
            },
            "required": ["change_id"],
        },
    },
    {
        "name": "reject_change",
        "description": "Reject a client change request with an optional reason.",
        "input_schema": {
            "type": "object",
            "properties": {
                "change_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["change_id"],
        },
    },
    {
        "name": "revert_change",
        "description": "Revert an applied client change — restores the design to the before-change version snapshot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "change_id": {"type": "string"},
            },
            "required": ["change_id"],
        },
    },
    # Phase 35/36 — Render prompt + export
    {
        "name": "generate_render_prompt",
        "description": (
            "Generate a photorealistic render prompt from the current project for use with "
            "Midjourney, Stable Diffusion, DALL-E 3, or Blender. Includes style, materials, "
            "orientation, budget-level mood, and camera view."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "camera_name": {
                    "type": "string",
                    "description": "Camera preset name (e.g. 'exterior_front', 'living_room', 'bedroom_1', 'top_down', 'kitchen'). Defaults to exterior_front.",
                },
                "extra_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional tags to append (e.g. ['no people', '--ar 16:9', 'dusk lighting'])",
                },
            },
        },
    },
    {
        "name": "export_drawing",
        "description": "Export the current design to a file (svg, dxf, png, json, pdf, ifc, sketchup, blender, rhino, sheet_svg, sheet_pdf). Returns a download link.",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["svg", "dxf", "png", "json", "pdf", "ifc", "sketchup", "blender", "rhino", "sheet_svg", "sheet_pdf", "schedule_json", "schedule_csv"],
                    "description": "Export format",
                },
            },
            "required": ["format"],
        },
    },
    # Phase 40 — Feasibility / Yield
    {
        "name": "run_feasibility",
        "description": (
            "Run residential feasibility / yield analysis on the project site. "
            "Returns site area, usable footprint (after TN setbacks), FSI/FAR, buildable area, "
            "parking estimate, and five development options: compact (1BHK), balanced (2BHK), "
            "spacious (3BHK), future-expansion, and rental-friendly. Advisory only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "road_width_ft": {
                    "type": "number",
                    "description": "Road width in feet (0 = use default minimum TN setbacks).",
                },
            },
        },
    },
    {
        "name": "compare_feasibility_options",
        "description": "Compare all feasibility development options (compact/balanced/spacious/future/rental) for the current project. Runs feasibility if not already computed.",
        "input_schema": {"type": "object", "properties": {}},
    },
    # Phase 41 — Review / QA
    {
        "name": "run_qa_checklist",
        "description": (
            "Run the automated QA checklist on the project. Checks: validation, room count, "
            "rooms inside site, openings, dimensions, MEP generated, details present, "
            "BOQ calculated, missing rates, exports fresh. Advisory — verify with a licensed architect."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_review_issue",
        "description": "Add a review comment or issue to the project (spatial / mep / compliance / boq / detail / export / general).",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title for the issue."},
                "category": {
                    "type": "string",
                    "enum": ["spatial", "mep", "compliance", "boq", "detail", "export", "general"],
                },
                "description": {"type": "string"},
                "object_ref": {"type": "string", "description": "ID of the object this issue relates to (room_id, etc.)."},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_review_issues",
        "description": "List all open review issues and comments for the current project.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

_SYSTEM_PROMPT = """You are an expert architectural design assistant for Scotch, an AI-native architecture platform.

You help architects and clients by:
- Generating and editing 2D floor plans from prompts
- Adding, removing, or resizing rooms; adjusting site, orientation, style, floors
- Generating MEP (plumbing, electrical, lighting, AC) service layers
- Creating detail drawings (toilet, kitchen, wall section, tile layout, stair)
- Calculating BOQ and cost estimates; editing rates and tile specs
- Running Tamil Nadu (CMDA/DTCP) advisory compliance checks
- Managing client change requests and computing affected items
- Personalising designs via client brief (budget, vastu, family size) and user profile
- Generating render prompts for Midjourney / Stable Diffusion / Blender
- Exporting to SVG, DXF, PNG, IFC, SketchUp, Blender, Rhino, PDF sheets
- Reading attached reference images (sketches, site photos, inspiration) the user uploads in chat and using them to inform generation or edits

Design rules you always follow:
- Bedrooms ≥ 10×10 ft, bathrooms ≥ 5×5 ft, kitchens ≥ 8×8 ft, living rooms ≥ 12×12 ft
- Site coverage ≤ 80% of site area; every floor plan needs at least one room
- MEP outputs are advisory — not engineering-certified; always note this
- TN advisory outputs are advisory — always note needs_professional_verification

When the user asks to make changes, call the appropriate tool. After any tool call, confirm what changed in a single concise sentence. If asked about the design, use get_program for accurate current data."""


# ── Request / response schema ─────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatImage(BaseModel):
    media_type: str  # e.g. "image/png", "image/jpeg"
    data: str  # base64-encoded image bytes, no "data:" prefix


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    images: list[ChatImage] = []


class ChatResponse(BaseModel):
    reply: str
    project: dict | None = None
    tool_calls: list[str] = []


# ── Agentic loop helpers ──────────────────────────────────────────────────────


def _execute_tool(project_id: str, tool_name: str, tool_input: dict) -> tuple[Any, dict | None]:
    """Call the matching mcp_tool function. Returns (result_str, project_dict | None)."""
    mutating = {
        "generate_design", "add_room", "remove_room", "set_parameter", "restore_version",
        "generate_mep", "edit_mep_point", "generate_detail", "delete_detail",
        "calculate_boq", "edit_rate", "edit_tile_spec",
        # check_tn_rules, get_user_profile, get_client_brief are read-only
        "update_client_brief",  # updates project (returns brief dict not full project — handle below)
        # Phase 34 — change tools are read-only (they don't mutate ArchitectureProject directly)
        # Phase 40 — feasibility persists onto project
        "run_feasibility",
        # Phase 41 — qa/review are read-only; add_review_issue is a sidecar write
    }

    dispatch = {
        "generate_design": lambda: mcp_tools.generate_design(project_id, **tool_input),
        "add_room": lambda: mcp_tools.add_room(project_id, **tool_input),
        "remove_room": lambda: mcp_tools.remove_room(project_id, **tool_input),
        "set_parameter": lambda: mcp_tools.set_parameter(project_id, **tool_input),
        "get_program": lambda: mcp_tools.get_program(project_id),
        "run_intelligence": lambda: mcp_tools.run_intelligence(project_id, **tool_input),
        "export_project": lambda: mcp_tools.export_project(project_id, **tool_input),
        "render_project": lambda: mcp_tools.render_project(project_id, **tool_input),
        "restore_version": lambda: mcp_tools.restore_version(project_id, **tool_input),
        # Phase 29 — MEP
        "generate_mep": lambda: mcp_tools.generate_mep(project_id, **tool_input),
        "edit_mep_point": lambda: mcp_tools.edit_mep_point(project_id, **tool_input),
        "get_mep_plan": lambda: mcp_tools.get_mep_plan(project_id),
        # Phase 30 — Details
        "generate_detail": lambda: mcp_tools.generate_detail(project_id, **tool_input),
        "list_details": lambda: mcp_tools.list_details(project_id),
        "delete_detail": lambda: mcp_tools.delete_detail(project_id, **tool_input),
        # Phase 31 — BOQ
        "calculate_boq":  lambda: mcp_tools.calculate_boq(project_id),
        "get_boq":        lambda: mcp_tools.get_boq(project_id),
        "edit_rate":      lambda: mcp_tools.edit_rate(project_id, **tool_input),
        "edit_tile_spec": lambda: mcp_tools.edit_tile_spec(project_id, **tool_input),
        # Phase 32 — TN advisory
        "check_tn_rules": lambda: mcp_tools.check_tn_rules(project_id, **tool_input),
        # Phase 33 — Profile + brief
        "get_user_profile":    lambda: mcp_tools.get_user_profile(),
        "update_user_profile": lambda: mcp_tools.update_user_profile(**tool_input),
        "get_client_brief":    lambda: mcp_tools.get_client_brief(project_id),
        "update_client_brief": lambda: mcp_tools.update_client_brief(project_id, **tool_input),
        # Phase 34 — Client Change Management
        "create_client_change": lambda: mcp_tools.create_client_change(project_id, **tool_input),
        "show_affected_items":  lambda: mcp_tools.show_affected_items(project_id, **tool_input),
        "list_client_changes":  lambda: mcp_tools.list_client_changes(project_id),
        "approve_change":       lambda: mcp_tools.approve_change(project_id, **tool_input),
        "reject_change":        lambda: mcp_tools.reject_change(project_id, **tool_input),
        "revert_change":        lambda: mcp_tools.revert_change(project_id, **tool_input),
        # Phase 35/36 — render prompt + export drawing
        "generate_render_prompt": lambda: mcp_tools.generate_render_prompt_tool(project_id, **tool_input),
        "export_drawing":          lambda: mcp_tools.export_drawing(project_id, **tool_input),
        # Phase 40 — Feasibility / Yield
        "run_feasibility":              lambda: mcp_tools.run_feasibility(project_id, **tool_input),
        "compare_feasibility_options":  lambda: mcp_tools.compare_feasibility_options(project_id),
        # Phase 41 — Review / QA
        "run_qa_checklist":   lambda: mcp_tools.run_qa_checklist(project_id),
        "add_review_issue":   lambda: mcp_tools.add_review_issue(project_id, **tool_input),
        "list_review_issues": lambda: mcp_tools.list_review_issues(project_id),
    }

    if tool_name not in dispatch:
        return f"Unknown tool '{tool_name}'", None

    result = dispatch[tool_name]()
    # update_client_brief returns a brief dict, not a full project; don't surface as project
    if tool_name in mutating and tool_name != "update_client_brief":
        project_dict = result
    else:
        project_dict = None
    # Summarise large dicts for Claude's tool_result — full project JSON is too long
    summary = _summarise_result(tool_name, result)
    return summary, project_dict


def _summarise_result(tool_name: str, result: Any) -> str:
    if tool_name in ("add_room", "remove_room", "set_parameter", "generate_design", "restore_version"):
        if isinstance(result, dict):
            rooms = result.get("rooms", [])
            return f"Done. Project now has {len(rooms)} rooms."
        return "Done."
    if tool_name == "get_program":
        if isinstance(result, dict):
            rooms = result.get("rooms", [])
            site = result.get("site", {})
            totals = result.get("totals", {})
            lines = [f"Site: {site.get('width')}×{site.get('depth')} ft, {site.get('floors')} floor(s)"]
            for r in rooms:
                lines.append(f"  {r['name']} ({r['type']}): {r['width']}×{r['depth']} ft")
            lines.append(f"Total built-up: {totals.get('built_up_area')} ft²")
            return "\n".join(lines)
        return str(result)
    if tool_name == "run_intelligence":
        if isinstance(result, dict):
            checks = result.get("spatial_checks", [])
            passed = sum(1 for c in checks if c.get("passed"))
            return f"Intelligence: {passed}/{len(checks)} spatial checks passed."
        return str(result)
    if tool_name == "create_client_change":
        if isinstance(result, dict):
            aid = result.get("affected_items") or {}
            total = aid.get("total_count", 0) if isinstance(aid, dict) else 0
            summary = aid.get("summary", "") if isinstance(aid, dict) else result.get("summary", "")
            cost = aid.get("cost_impact", "") if isinstance(aid, dict) else result.get("cost_impact", "")
            return (f"Change request created (id={result.get('id')}). "
                    f"{total} affected items. {summary} {cost}")
        return "Change created."
    if tool_name == "list_client_changes":
        if isinstance(result, dict):
            return (f"{result.get('total', 0)} changes: "
                    f"{result.get('pending', 0)} pending, "
                    f"{result.get('approved', 0)} approved, "
                    f"{result.get('applied', 0)} applied.")
        return str(result)
    if tool_name in ("approve_change", "reject_change", "revert_change"):
        if isinstance(result, dict):
            return result.get("message", "Done.")
        return "Done."
    if tool_name == "show_affected_items":
        if isinstance(result, dict):
            return f"Affected items: {result.get('summary', '')} Cost: {result.get('cost_impact', '')}"
        return str(result)
    if tool_name == "generate_render_prompt":
        if isinstance(result, dict):
            prompt = result.get("render_prompt", "")
            camera = result.get("camera", "exterior")
            return f"Render prompt ({camera}):\n{prompt[:400]}\n[Copy and paste into your render tool]"
        return str(result)
    if tool_name == "export_drawing":
        if isinstance(result, dict):
            fn = result.get("filename", "")
            fmt = result.get("format", "")
            return f"Export ready: {fn} ({fmt}). Download from the Exports panel."
        return str(result)
    if tool_name in ("run_feasibility", "compare_feasibility_options"):
        if isinstance(result, dict):
            opts = result.get("options", [])
            site = result.get("site_area", 0)
            bua = result.get("buildable_area", 0)
            n_opts = len(opts)
            return (
                f"Feasibility: site {site:.0f} sq ft, buildable area {bua:.0f} sq ft, "
                f"{n_opts} options generated (compact / balanced / spacious / future / rental)."
            )
        return str(result)
    if tool_name == "run_qa_checklist":
        if isinstance(result, dict):
            passed = result.get("passed", 0)
            total = len(result.get("items", []))
            pct = result.get("completion_pct", 0)
            failed_items = [i for i in result.get("items", []) if i.get("status") in ("fail", "warning")]
            fail_str = "; ".join(i["title"] for i in failed_items[:3]) if failed_items else "all checks passed"
            return f"QA: {passed}/{total} checks passed ({pct:.0f}%). Issues: {fail_str}."
        return str(result)
    if tool_name in ("add_review_issue", "list_review_issues"):
        if isinstance(result, dict):
            if tool_name == "list_review_issues":
                return (
                    f"{result.get('total', 0)} review issue(s) — "
                    f"{result.get('open', 0)} open, "
                    f"{result.get('resolved', 0)} resolved."
                )
            return f"Review issue added: '{result.get('title', '')}' (ID: {result.get('id', '')})."
        return str(result)
    return str(result)[:500]


def _run_anthropic_loop(project_id: str, req: ChatRequest) -> ChatResponse:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _run_deterministic_fallback(project_id, req)

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = [
        {"role": m.role, "content": m.content} for m in req.history
    ]
    if req.images:
        content: list[dict] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": img.media_type, "data": img.data},
            }
            for img in req.images
        ]
        content.append({"type": "text", "text": req.message})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": req.message})

    final_reply = ""
    tool_calls: list[str] = []
    last_project: dict | None = None

    # Agentic loop: keep going until Claude returns only text
    for _ in range(8):  # safety cap
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            tools=_TOOL_SCHEMAS,
            messages=messages,
        )

        # Collect text and tool_use blocks
        text_parts: list[str] = []
        tool_uses: list[dict] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append({"id": block.id, "name": block.name, "input": block.input})

        if text_parts:
            final_reply = " ".join(text_parts)

        if not tool_uses or response.stop_reason == "end_turn":
            break

        # Append Claude's response (including tool_use blocks) to messages
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool and build tool_result list
        tool_results = []
        for tu in tool_uses:
            tool_calls.append(tu["name"])
            try:
                result_str, project_dict = _execute_tool(project_id, tu["name"], tu["input"])
                if project_dict:
                    last_project = project_dict
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": result_str,
                })
            except Exception as exc:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": f"Error: {exc}",
                    "is_error": True,
                })

        messages.append({"role": "user", "content": tool_results})

    return ChatResponse(
        reply=final_reply or "Done.",
        project=last_project,
        tool_calls=tool_calls,
    )


def _run_deterministic_fallback(project_id: str, req: ChatRequest) -> ChatResponse:
    """Keyword-based intent parser — works with no API key."""
    msg = req.message.lower()
    tool_calls: list[str] = []
    last_project: dict | None = None

    _ROOM_TYPES = ["bedroom", "bathroom", "kitchen", "living", "study", "storage", "balcony", "parking"]
    _ALIASES = {
        "bath": "bathroom", "bed": "bedroom", "study room": "study",
        "powder room": "bathroom", "toilet": "bathroom", "wc": "bathroom",
        "hall": "living", "lounge": "living", "drawing room": "living",
        "store": "storage", "utility": "storage",
    }

    def _detect_room_type(text: str) -> str | None:
        for alias, rtype in _ALIASES.items():
            if alias in text:
                return rtype
        for rt in _ROOM_TYPES:
            if rt in text:
                return rt
        return None

    reply = ""

    # ── intent branches — specific intents FIRST to avoid substring collisions ──
    # Order rationale:
    #   client_changes before add_room  ("client asked to add" has "add")
    #   client_brief   before set_param ("set budget" has "set"; "changes" has "change")
    #   profile        before show_prog  ("show my profile" has "show")
    #   mep            before add_room  ("add plumbing" has "add")
    #   render_prompt  before generate  ("generate render prompt" has "generate")

    # 1. Client changes ────────────────────────────────────────────────────────
    if any(kw in msg for kw in (
        "client asked", "client wants", "client change", "client request",
        "list changes", "pending changes", "show changes", "show impact", "impact of",
        "revert last", "revert change", "approve change", "reject change",
        "change request", "revision request",
    )):
        if any(kw in msg for kw in ("list", "show changes", "pending", "all changes")):
            try:
                result = mcp_tools.list_client_changes(project_id)
                tool_calls.append("list_client_changes")
                changes_list = result.get("changes", [])
                if not changes_list:
                    reply = "No client change requests yet. Say 'client asked to ...' to create one."
                else:
                    lines = [f"**{result['total']} change request(s)** ({result['pending']} pending, {result['applied']} applied):"]
                    for c in changes_list[:5]:
                        lines.append(f"• [{c['status'].upper()}] {c['request_text'][:60]} — {c['summary'][:60]}")
                    reply = "\n".join(lines)
            except Exception as exc:
                reply = f"Couldn't list changes: {exc}"
        elif any(kw in msg for kw in ("revert", "undo change")):
            try:
                result = mcp_tools.list_client_changes(project_id)
                applied = [c for c in result.get("changes", []) if c["status"] == "applied"]
                if applied:
                    rev = mcp_tools.revert_change(project_id, applied[0]["id"])
                    tool_calls.append("revert_change")
                    last_project = rev.get("project")
                    reply = rev.get("message", "Change reverted.")
                else:
                    reply = "No applied changes found to revert."
            except Exception as exc:
                reply = f"Couldn't revert change: {exc}"
        else:
            change_text = req.message.strip()
            for prefix in ("client asked to ", "client asked ", "client wants ", "client change: "):
                if msg.startswith(prefix):
                    change_text = req.message[len(prefix):]
                    break
            try:
                result = mcp_tools.create_client_change(project_id, change_text)
                tool_calls.append("create_client_change")
                affected = result.get("affected_items") or {}
                summary = affected.get("summary", result.get("summary", "")) if isinstance(affected, dict) else ""
                cost = affected.get("cost_impact", result.get("cost_impact", "")) if isinstance(affected, dict) else ""
                total = affected.get("total_count", 0) if isinstance(affected, dict) else 0
                reply = (
                    f"**Change request created** (ID: {result['id']})\n"
                    f"*{result['request_text'][:80]}*\n\n"
                    f"{summary}\n"
                    f"**{total} items** affected across plan, MEP, BOQ, exports.\n"
                    f"Cost impact: {cost}\n\n"
                    f"Say 'approve change {result['id']}' to approve, or 'reject change {result['id']}' to reject."
                )
            except Exception as exc:
                reply = f"Couldn't create change request: {exc}"

    # 2. Client brief ── before set_parameter ("set budget" has "set") ─────────
    elif any(kw in msg for kw in (
        "client brief", "family size", "family of", "budget", "vastu",
        "client preference", "brief", "client info",
    )):
        import re as _re2
        budget_match = _re2.search(r"budget\s+(?:to\s+|is\s+)?(economy|standard|premium)", msg)
        family_match = _re2.search(r"family\s+(?:size|of)\s+(\d+)", msg)
        if budget_match or family_match:
            kwargs: dict = {}
            if budget_match:
                kwargs["budget_level"] = budget_match.group(1)
            if family_match:
                kwargs["family_size"] = int(family_match.group(1))
            try:
                brief = mcp_tools.update_client_brief(project_id, **kwargs)
                tool_calls.append("update_client_brief")
                reply = (
                    f"Client brief updated. "
                    f"Budget: {brief.get('budget_level')} · "
                    f"Family size: {brief.get('family_size')} · "
                    f"Style: {brief.get('style_preference') or 'not set'}.\n"
                    "Regenerate the design to apply these preferences."
                )
            except Exception as exc:
                reply = f"Couldn't update brief: {exc}"
        else:
            try:
                brief = mcp_tools.get_client_brief(project_id)
                tool_calls.append("get_client_brief")
                reply = (
                    f"**Client brief:**\n"
                    f"Family: {brief.get('family_name') or 'not set'} · "
                    f"Size: {brief.get('family_size')} · "
                    f"Budget: {brief.get('budget_level')} · "
                    f"Style: {brief.get('style_preference') or 'not set'} · "
                    f"Vastu: {'yes' if brief.get('vastu_preference') else 'no'}\n"
                    "Update via: 'set budget to economy', 'family of 4', or the Client Brief panel."
                )
            except Exception as exc:
                reply = f"Couldn't read brief: {exc}"

    # 3. Profile ── before show_program ("show my profile" has "show") ─────────
    elif any(kw in msg for kw in (
        "profile", "my preference", "architect twin", "default style",
        "preferred units", "update profile", "my style", "set orientation", "set location",
    )):
        try:
            profile = mcp_tools.get_user_profile()
            tool_calls.append("get_user_profile")
            reply = (
                f"**Your architect-twin profile:**\n"
                f"Role: {profile.get('role')} · Units: {profile.get('preferred_units')} · "
                f"Location: {profile.get('default_location')} · Style: {profile.get('default_style')} · "
                f"Orientation: {profile.get('default_orientation')}-facing\n"
                "Update via: 'set my default style to contemporary' or use the Profile panel."
            )
        except Exception as exc:
            reply = f"Couldn't read profile: {exc}"

    # 4. MEP ── before add_room ("add plumbing" has "add") ────────────────────
    elif any(kw in msg for kw in ("plumbing", "electrical", "lighting", "mep", "wiring", "pipes")):
        systems: list[str] = []
        if any(kw in msg for kw in ("plumbing", "pipe", "drain", "water", "sanitary")):
            systems.append("plumbing")
        if any(kw in msg for kw in ("electrical", "wiring", "socket", "switch", "circuit")):
            systems.append("electrical")
        if any(kw in msg for kw in ("lighting", "light", "lamp", "ceiling light")):
            systems.append("lighting")
        if any(kw in msg for kw in ("ac", "air conditioning", "hvac", "split")):
            systems.append("ac")
        if "mep" in msg or "all" in msg or not systems:
            systems = ["plumbing", "electrical", "lighting", "ac"]
        try:
            last_project = mcp_tools.generate_mep(project_id, systems=systems)
            tool_calls.append("generate_mep")
            reply = (
                f"Generated {', '.join(systems)} layers. Service points placed based on room types. "
                "All outputs are advisory — review with a licensed engineer before construction."
            )
        except Exception as exc:
            reply = f"Couldn't generate MEP: {exc}"

    # 5. Detail drawings ───────────────────────────────────────────────────────
    elif any(kw in msg for kw in (
        "detail", "section", "tile layout", "tile plan", "floor section",
        "wall section", "stair detail", "stair section",
    )):
        detail_type = "wall_section"
        if any(kw in msg for kw in ("toilet", "bathroom", "wc", "bath")):
            detail_type = "toilet"
        elif any(kw in msg for kw in ("kitchen", "counter", "cabinet")):
            detail_type = "kitchen"
        elif any(kw in msg for kw in ("door", "window", "elevation")):
            detail_type = "door_window"
        elif any(kw in msg for kw in ("tile", "floor plan", "tile layout")):
            detail_type = "tile_layout"
        elif any(kw in msg for kw in ("stair", "step", "riser", "tread")):
            detail_type = "stair"
        try:
            proj = mcp_tools._load(project_id)
            source_id: str | None = None
            if detail_type == "toilet":
                room = next((r for r in proj.rooms if r.type in ("bathroom", "master_bathroom")), None)
                if room:
                    source_id = room.id
            elif detail_type == "kitchen":
                room = next((r for r in proj.rooms if r.type == "kitchen"), None)
                if room:
                    source_id = room.id
            elif detail_type in ("tile_layout", "wall_section"):
                room = next((r for r in proj.rooms if r.type not in ("stair", "parking")), None)
                if room:
                    source_id = room.id
            elif detail_type == "stair":
                if proj.stairs:
                    source_id = proj.stairs[0].id
            elif detail_type == "door_window":
                if proj.doors:
                    source_id = proj.doors[0].id
            if source_id is None:
                reply = f"I need a specific room or object to generate a {detail_type} detail — please say which room (e.g. 'toilet detail for bath-1')."
            else:
                last_project = mcp_tools.generate_detail(project_id, detail_type, source_id)
                tool_calls.append("generate_detail")
                reply = (
                    f"Generated {detail_type.replace('_', ' ')} detail. "
                    "All dimensions are advisory — verify on site before construction."
                )
        except Exception as exc:
            reply = f"Couldn't generate detail: {exc}"

    # 6. Tamil Nadu advisory ───────────────────────────────────────────────────
    elif any(kw in msg for kw in (
        "tamil nadu", "tn compliance", "tn advisory", "cmda", "dtcp",
        "tn setback", "tn fsi", "tn parking", "rainwater harvesting",
        "approval checklist", "building approval", "plan approval", "tn rules",
        "tamil", "check tn", "tamilnadu",
    )):
        try:
            import re as _re
            rw_match = _re.search(r"(\d+(?:\.\d+)?)\s*ft\s*road|road\s*(?:width\s*)?(\d+(?:\.\d+)?)", msg)
            road_width = 0.0
            if rw_match:
                road_width = float(rw_match.group(1) or rw_match.group(2))
            report = mcp_tools.check_tn_rules(project_id, road_width_ft=road_width)
            tool_calls.append("check_tn_rules")
            warns = report.get("warn_count", 0)
            missing = report.get("missing_inputs", [])
            missing_str = f"\n⚠ Missing: {', '.join(missing[:3])}." if missing else ""
            disclaimer = "Advisory only — consult a licensed architect/CMDA-registered engineer."
            reply = (
                f"**TN Advisory:** {report.get('summary', '')}\n"
                f"{warns} advisory warning(s).{missing_str}\n"
                f"{disclaimer}"
            )
        except Exception as exc:
            reply = f"Couldn't run TN advisory: {exc}"

    # 7. Render prompt ── before generate ("generate render prompt" has "generate") ─
    elif any(kw in msg for kw in (
        "render prompt", "render image", "visualise", "visualize",
        "midjourney", "stable diffusion", "blender render", "dall-e",
        "generate render", "render this", "render the",
    )):
        import re as _re3
        camera = None
        for view in ("exterior", "living", "bedroom", "kitchen", "toilet", "bathroom", "top down", "aerial"):
            if view in msg:
                camera = view.replace(" ", "_")
                break
        try:
            result = mcp_tools.generate_render_prompt_tool(project_id, camera_name=camera)
            tool_calls.append("generate_render_prompt")
            reply = (
                f"**Render Prompt ({result.get('camera', 'exterior')})**\n\n"
                f"`{result.get('render_prompt', '')}`\n\n"
                "Paste this into Midjourney, Stable Diffusion, DALL-E 3, or Blender."
            )
        except Exception as exc:
            reply = f"Couldn't generate render prompt: {exc}"

    # 8. Export drawing ────────────────────────────────────────────────────────
    elif any(kw in msg for kw in (
        "export", "download", "save as", "export to",
        "dxf", "dwg", "ifc", "sketchup", "rhino", "blender file", "pdf sheet", "save pdf",
    )):
        _EXPORT_MAP = {
            "dxf": "dxf", "dwg": "dxf", "autocad": "dxf",
            "ifc": "ifc", "bim": "ifc",
            "sketchup": "sketchup", ".rb": "sketchup",
            "rhino": "rhino", "grasshopper": "rhino",
            "blender": "blender", ".py": "blender",
            "pdf sheet": "sheet_pdf", "sheet pdf": "sheet_pdf", "presentation": "sheet_svg",
            "svg": "svg", "png": "png", "json": "json",
        }
        fmt = "svg"
        for kw, f in _EXPORT_MAP.items():
            if kw in msg:
                fmt = f
                break
        tool_calls.append("export_drawing")
        try:
            result = mcp_tools.export_drawing(project_id, format=fmt)
            fn = result.get("filename", f"export.{fmt}")
            reply = (
                f"Export complete: **{fn}**. "
                "Download from the Exports panel in the right sidebar."
            )
        except Exception as exc:
            reply = f"Couldn't export: {exc}"

    # 9. Feasibility / yield ── before generate ("generate feasibility" has "generate") ─
    elif any(kw in msg for kw in (
        "feasibility", "yield", "buildable area", "unit count", "how many units",
        "maximize built", "rental option", "rental friendly", "rental-friendly",
        "compare options", "development options", "fsI", "far ", "setback",
        "compact option", "balanced option", "spacious option",
    )):
        import re as _re4
        rw_match = _re4.search(r"(\d+(?:\.\d+)?)\s*ft\s*road|road\s*(?:width\s*)?(\d+(?:\.\d+)?)", msg)
        road_width = 0.0
        if rw_match:
            road_width = float(rw_match.group(1) or rw_match.group(2))
        if any(kw in msg for kw in ("compare", "options", "which option", "show option")):
            try:
                result = mcp_tools.compare_feasibility_options(project_id)
                tool_calls.append("compare_feasibility_options")
                opts = result.get("options", [])
                lines = [
                    f"**Feasibility options** for {result.get('site_area', 0):.0f} sq ft site "
                    f"({result.get('buildable_area', 0):.0f} sq ft buildable, FSI {result.get('fsi_far', 1.5)}):\n"
                ]
                for opt in opts:
                    lines.append(
                        f"• **{opt['label']}** — {opt['unit_count']}× {opt['unit_type']}, "
                        f"{opt['built_up_area']:.0f} sq ft BUA, {opt['parking_slots']} parking slot(s)."
                    )
                if result.get("warnings"):
                    lines.append(f"\n⚠ {result['warnings'][0]}")
                lines.append("\nAll figures advisory — verify with a licensed architect and CMDA/DTCP.")
                reply = "\n".join(lines)
            except Exception as exc:
                reply = f"Couldn't compare options: {exc}"
        else:
            try:
                result = mcp_tools.run_feasibility(project_id, road_width_ft=road_width)
                tool_calls.append("run_feasibility")
                opts = result.get("options", [])
                balanced = next((o for o in opts if o["name"] == "balanced"), opts[0] if opts else {})
                warn_str = "\n⚠ " + result["warnings"][0] if result.get("warnings") else ""
                missing_str = (
                    "\n🔍 Missing: " + ", ".join(result["missing_inputs"][:2]) + "."
                ) if result.get("missing_inputs") else ""
                reply = (
                    f"**Feasibility Analysis**\n\n"
                    f"Site area: {result['site_area']:.0f} sq ft · "
                    f"Usable footprint: {result['usable_footprint']:.0f} sq ft · "
                    f"Coverage: {result['coverage_pct']:.1f}%\n"
                    f"FSI/FAR: {result['fsi_far']} · Buildable area: {result['buildable_area']:.0f} sq ft\n\n"
                    f"**Recommended (balanced):** {balanced.get('label', 'N/A')} — "
                    f"{balanced.get('unit_count', 0)}× {balanced.get('unit_type', '2BHK')}, "
                    f"{balanced.get('built_up_area', 0):.0f} sq ft BUA.\n\n"
                    f"{len(opts)} options available — say 'compare feasibility options' for full comparison."
                    f"{warn_str}{missing_str}\n\n"
                    "Advisory — verify with a licensed architect and CMDA/DTCP."
                )
            except Exception as exc:
                reply = f"Couldn't run feasibility analysis: {exc}"

    # 9a. Generate design ── after render_prompt/export/feasibility ────────────
    elif any(kw in msg for kw in ("generate", "design", "create", "build a", "plan a")):
        try:
            last_project = mcp_tools.generate_design(project_id, req.message)
            tool_calls.append("generate_design")
            rooms = last_project.get("rooms", [])
            reply = f"Generated a new floor plan with {len(rooms)} rooms based on your prompt."
        except Exception as exc:
            reply = f"Couldn't generate design: {exc}"

    # 10. BOQ / cost ── after generate so "generate" never matches "rate" ──────
    elif any(kw in msg for kw in (
        "boq", "bill of quantities", "cost estimate", "cost plan", "quantity",
        "tile count", "tile quantity", "tile rate", "tile size",
        "set rate", "edit rate", "update rate", "change rate",
        "material cost", "pricing", "estimate cost", "grand total", "missing rate",
    )) or (
        "cost" in msg and not any(kw in msg for kw in ("client", "generate", "design", "create", "build"))
    ):
        if any(kw in msg for kw in ("set rate", "change rate", "update rate", "rate to", "per sqft", "per nos")):
            reply = (
                "To update a rate, say for example: 'set tile supply rate to 90'. "
                "I need a category (flooring/paint/plumbing/electrical/doors/windows), "
                "item name, and new rate. Configure ANTHROPIC_API_KEY for natural-language rate edits."
            )
        elif any(kw in msg for kw in ("tile size", "tile spec", "600x600", "300x300", "12x12", "24x24")):
            reply = (
                "To change tile size, use the Material Plan editor in the BOQ tab. "
                "Configure ANTHROPIC_API_KEY for natural-language tile spec edits."
            )
        else:
            try:
                last_project = mcp_tools.calculate_boq(project_id)
                tool_calls.append("calculate_boq")
                cp = last_project.get("cost_plan", {})
                grand = cp.get("grand_total", 0)
                missing = cp.get("missing_rates", [])
                cats = [f"{c['category']}: ₹{c['total']:,.0f}"
                        for c in cp.get("category_totals", [])]
                cat_str = ", ".join(cats[:5]) if cats else "no items"
                missing_str = f" ⚠ {len(missing)} missing rates." if missing else ""
                reply = (
                    f"BOQ calculated. Grand total: ₹{grand:,.0f}.{missing_str}\n"
                    f"Breakdown: {cat_str}.\n"
                    "All quantities are estimates — verify before procurement."
                )
            except Exception as exc:
                reply = f"Couldn't calculate BOQ: {exc}"

    # 11. QA checklist + review ── before add_room ("add issue" has "add") ────────
    elif any(kw in msg for kw in (
        "qa checklist", "quality check", "run qa", "check qa",
        "review issue", "add issue", "list issue", "open issues", "review comment",
        "design review", "check all", "ready to submit", "production ready",
    )):
        if any(kw in msg for kw in ("list issue", "show issue", "open issue", "all issue", "list review")):
            try:
                result = mcp_tools.list_review_issues(project_id)
                tool_calls.append("list_review_issues")
                total = result["total"]
                if total == 0:
                    reply = "No review issues yet. Say 'add review issue: ...' to log a comment."
                else:
                    lines = [f"**{total} review issue(s)** ({result['open']} open, {result['resolved']} resolved):"]
                    for issue in result["issues"][:5]:
                        icon = "✓" if issue["status"] == "resolved" else "○"
                        lines.append(f"  {icon} [{issue['priority'].upper()}] {issue['title']} ({issue['category']})")
                    reply = "\n".join(lines)
            except Exception as exc:
                reply = f"Couldn't list issues: {exc}"
        elif any(kw in msg for kw in ("add issue", "add review", "review comment", "log issue")):
            import re as _re5
            title_match = _re5.search(r"(?:issue:|comment:|review:)\s*(.+)", msg)
            title = title_match.group(1).strip() if title_match else req.message.strip()
            try:
                result = mcp_tools.add_review_issue(project_id, title=title[:120])
                tool_calls.append("add_review_issue")
                reply = f"Review issue added (ID: {result['id']}): '{result['title']}'. Say 'list review issues' to see all."
            except Exception as exc:
                reply = f"Couldn't add issue: {exc}"
        else:
            try:
                result = mcp_tools.run_qa_checklist(project_id)
                tool_calls.append("run_qa_checklist")
                passed = result["passed"]
                total = len(result["items"])
                pct = result["completion_pct"]
                lines = [f"**QA Checklist: {passed}/{total} checks passed ({pct:.0f}%)**\n"]
                for item in result["items"]:
                    icon = {"pass": "✓", "fail": "✗", "warning": "⚠", "not_checked": "–"}[item["status"]]
                    lines.append(f"  {icon} {item['title']}")
                    if item["status"] != "pass" and item.get("detail"):
                        lines.append(f"    → {item['detail']}")
                lines.append(f"\n{result['advisory']}")
                reply = "\n".join(lines)
            except Exception as exc:
                reply = f"Couldn't run QA checklist: {exc}"

    # 12. Add room ── after all specific intents above ─────────────────────────
    elif any(kw in msg for kw in ("add", "include", "put a", "need a", "want a", "create a")):
        rt = _detect_room_type(msg)
        if rt:
            try:
                last_project = mcp_tools.add_room(project_id, rt)
                tool_calls.append("add_room")
                count = len(last_project.get("rooms", []))
                reply = f"Added a {rt} to the floor plan. The design now has {count} rooms."
            except Exception as exc:
                reply = f"Couldn't add {rt}: {exc}"

    # 12. Remove room ──────────────────────────────────────────────────────────
    elif any(kw in msg for kw in ("remove", "delete", "take out", "drop")):
        try:
            prog = mcp_tools.get_program(project_id)
            rt = _detect_room_type(msg)
            target = None
            if rt:
                target = next((r for r in reversed(prog["rooms"]) if r["type"] == rt), None)
            if target:
                last_project = mcp_tools.remove_room(project_id, target["id"])
                tool_calls.append("remove_room")
                reply = f"Removed {target['name']} from the floor plan."
            else:
                reply = "I couldn't identify which room to remove. Please specify the room name or type."
        except Exception as exc:
            reply = f"Couldn't remove room: {exc}"

    # 13. Dimension changes ── after client_brief ("set budget" must not reach here) ─
    elif any(kw in msg for kw in ("make", "set", "change", "resize", "widen", "enlarge", "shrink")):
        import re
        rt = _detect_room_type(msg)
        dim_match = re.search(r"(\d+(?:\.\d+)?)\s*[x×by]\s*(\d+(?:\.\d+)?)", msg)
        if rt and dim_match:
            try:
                prog = mcp_tools.get_program(project_id)
                target = next((r for r in prog["rooms"] if r["type"] == rt), None)
                if target:
                    w, d = float(dim_match.group(1)), float(dim_match.group(2))
                    mcp_tools.set_parameter(project_id, "room_width", w, target["id"])
                    last_project = mcp_tools.set_parameter(project_id, "room_depth", d, target["id"])
                    tool_calls.extend(["set_parameter", "set_parameter"])
                    reply = f"Resized {target['name']} to {w}×{d} ft."
                else:
                    reply = f"No {rt} found in the current design."
            except Exception as exc:
                reply = f"Couldn't resize: {exc}"
        elif "floor" in msg or "storey" in msg or "story" in msg:
            n_match = re.search(r"(\d+)", msg)
            if n_match:
                n = int(n_match.group(1))
                try:
                    last_project = mcp_tools.set_parameter(project_id, "floors", n)
                    tool_calls.append("set_parameter")
                    reply = f"Updated floor count to {n}."
                except Exception as exc:
                    reply = f"Couldn't change floors: {exc}"
        else:
            reply = "I can help with room dimensions. Try: 'make the kitchen 10×12 ft' or 'add a bedroom'."

    # 14. Show program ── after qa/review so "list issues" doesn't fall here ────
    # "what room" (not bare "what") to avoid matching unrelated "what is X" questions
    elif any(kw in msg for kw in ("show", "list", "what room", "describe", "tell me", "how many", "summary", "program")):
        try:
            prog = mcp_tools.get_program(project_id)
            tool_calls.append("get_program")
            site = prog["site"]
            totals = prog["totals"]
            room_lines = "\n".join(
                f"• {r['name']} ({r['type']}): {r['width']}×{r['depth']} ft"
                for r in prog["rooms"]
            )
            reply = (
                f"Site: {site['width']}×{site['depth']} ft, {site['floors']} floor(s), "
                f"{site['orientation'].capitalize()}-facing\n\n"
                f"{room_lines}\n\n"
                f"Total built-up area: {totals['built_up_area']} ft² ({totals['coverage_pct']}% coverage)"
            )
        except Exception as exc:
            reply = f"Couldn't read the design: {exc}"

    else:
        reply = (
            "I can help you with:\n"
            "• **Add rooms** — 'add a bedroom' or 'include a study'\n"
            "• **Remove rooms** — 'remove the balcony'\n"
            "• **Resize** — 'make the kitchen 10×12 ft'\n"
            "• **Floor count** — 'change to 2 floors'\n"
            "• **Show design** — 'what rooms do I have?'\n"
            "• **MEP layers** — 'add plumbing and electrical'\n"
            "• **Detail drawings** — 'generate toilet detail' or 'wall section'\n"
            "• **BOQ / cost** — 'calculate BOQ' or 'cost estimate'\n"
            "• **TN advisory** — 'check Tamil Nadu compliance' or 'check CMDA rules'\n"
            "• **Client changes** — 'client asked to add attached toilet' or 'reduce budget by 10%'\n"
            "• **List changes** — 'list pending changes' or 'show all changes'\n"
            "• **Revert** — 'revert last client change'\n"
            "• **Client brief** — 'set budget to economy' or 'family of 4'\n"
            "• **My profile** — 'show my profile' or 'update profile'\n"
            "• **Feasibility** — 'run feasibility analysis' or 'compare development options'\n"
            "• **QA checklist** — 'run QA checklist' or 'is this design production ready?'\n"
            "• **Review issues** — 'add review issue: ...' or 'list review issues'\n\n"
            "Configure ANTHROPIC_API_KEY for full natural-language understanding."
        )

    if req.images and reply:
        reply += (
            f"\n\n(Note: {len(req.images)} image(s) attached — image analysis needs an "
            "AI mode; configure ANTHROPIC_API_KEY to have Claude look at them.)"
        )

    return ChatResponse(
        reply=reply,
        project=last_project,
        tool_calls=tool_calls,
    )


# ── Route ─────────────────────────────────────────────────────────────────────


@router.post("/{project_id}/chat", response_model=ChatResponse)
def chat_message(
    project_id: str,
    req: ChatRequest,
    store: ProjectStore = Depends(get_project_store),
) -> ChatResponse:
    """Process a chat message in the context of a project. Runs an agentic tool-use loop."""
    try:
        store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        import anthropic as _anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key:
            return _run_anthropic_loop(project_id, req)
    except ImportError:
        pass

    return _run_deterministic_fallback(project_id, req)
