# Phase 38 — External MCP + Software Control: Current State Recon

*Inspected 2026-06-22 before implementation.*

## Objective

Expose all Scotch production tools to external agents (Claude Desktop, Cursor, local scripts) via the standalone MCP server; extend Revit/Rhino bridge docs; add auth/safety layer.

## What already exists (Phase 24)

`services/mcp/server.py` — standalone FastMCP server, 12 tools:

| Tool | Source function |
|---|---|
| `get_project` | `chat_tools.get_project` |
| `list_projects` | `chat_tools.list_projects` |
| `get_program` | `chat_tools.get_program` |
| `list_versions` | `chat_tools.list_versions` |
| `generate_design` | `chat_tools.generate_design` |
| `add_room` | `chat_tools.add_room` |
| `remove_room` | `chat_tools.remove_room` |
| `set_parameter` | `chat_tools.set_parameter` |
| `run_intelligence` | `chat_tools.run_intelligence` |
| `export_project` | `chat_tools.export_project` |
| `render_project` | `chat_tools.render_project` |
| `restore_version` | `chat_tools.restore_version` |

`services/mcp/tools.py` — thin re-export from `app.core.chat_tools`.  
`services/mcp/__init__.py` — empty package marker.

## Gaps that Phase 38 fills

1. **Missing Phase 29-35 tools** — MEP generation, detail generation, BOQ/cost, TN compliance, client change management, sync contract, render prompt — not exposed to external MCP.
2. **No auth/safety layer** — any local process can call the MCP server; needs `SCOTCH_MCP_TOKEN` env var guard.
3. **No setup docs** — no guide for Claude Desktop or Cursor to connect to the server.
4. **Revit/Rhino bridge docs** — gap: conflict handling, validation-result display, MCP bridge approach not documented.
5. **No MCP smoke tests** — no pytest coverage of the tools layer.

## Seam inventory (verified)

All production tools are already in `chat_tools.py`:
- Phase 29: `generate_mep`, `edit_mep_point`, `get_mep_plan`
- Phase 30: `generate_detail`, `list_details`, `delete_detail`
- Phase 31: `calculate_boq`, `edit_rate`, `get_boq`, `edit_tile_spec`
- Phase 32: `check_tn_rules`
- Phase 33: `get_user_profile`, `update_user_profile`, `get_client_brief`, `update_client_brief`
- Phase 34: `create_client_change`, `show_affected_items`, `list_client_changes`, `approve_change`, `reject_change`, `revert_change`
- Phase 35: `generate_render_prompt_tool`, `export_drawing`
- Sync: `app.api.routes.sync` → `project_to_sync_contract`, `push_sync`

MCP only needs: re-export in `tools.py` + registration in `server.py`.
