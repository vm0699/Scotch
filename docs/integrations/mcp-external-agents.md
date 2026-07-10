# Scotch MCP — External Agent Setup Guide

*Phase 38 · Updated 2026-06-22*

The Scotch standalone MCP server exposes 40+ architectural design tools to any
MCP-compatible agent: **Claude Desktop**, **Cursor**, **Continue.dev**, and local
scripts. This guide covers installation, configuration, and usage.

---

## Prerequisites

1. Scotch backend running: `cd services/api && uvicorn app.main:app --reload --port 8000`
2. Python 3.11+ with dependencies: `cd services/mcp && pip install mcp httpx`
3. MCP installed: `pip install mcp` (or included in `requirements.txt`)

---

## Claude Desktop

### 1. Find the config file

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/claude/claude_desktop_config.json` |

### 2. Add the Scotch MCP server

```json
{
  "mcpServers": {
    "scotch": {
      "command": "python",
      "args": ["C:/SAVRO/RARCH/services/mcp/server.py"],
      "env": {
        "SCOTCH_MCP_TOKEN": "your-optional-local-secret"
      }
    }
  }
}
```

Replace the path with the absolute path to `server.py` on your machine.  
`SCOTCH_MCP_TOKEN` is optional — omit it for local trust mode.

### 3. Restart Claude Desktop

The Scotch toolset will appear in the tool picker as **"Scotch"**.

### 4. Example prompts

```
List my Scotch projects.

Generate a 3BHK floor plan for project proj-abc123.

Add MEP (plumbing, electrical, AC) to project proj-abc123.

Generate a toilet detail for bathroom bath-1 in project proj-abc123.

Calculate the BOQ for project proj-abc123.

Check Tamil Nadu compliance for project proj-abc123.

Create a client change: "client wants attached toilet added to master bedroom"
for project proj-abc123.

Export the floor plan as DXF for project proj-abc123.

Generate a render prompt for the exterior view of project proj-abc123.
```

---

## Cursor

### 1. Open Cursor settings → MCP

Add a new server entry:

```json
{
  "name": "scotch",
  "transport": "stdio",
  "command": "python",
  "args": ["/absolute/path/to/services/mcp/server.py"]
}
```

### 2. Use tools in Cursor chat

Cursor discovers all available tools automatically.  Use `@scotch` to scope
your chat message to Scotch tools, or reference them naturally:

```
@scotch get the program for project proj-abc123

@scotch add a bedroom to the floor plan of proj-abc123

@scotch check Tamil Nadu compliance for proj-abc123
```

---

## SSE transport (web clients / custom agents)

Start the server in SSE mode:

```bash
cd services/mcp
python server.py --sse
```

The SSE endpoint is `http://localhost:8001/sse` (FastMCP default).  
Connect your MCP client to this URL.

---

## Tool reference (summary)

### Read tools
| Tool | Description |
|---|---|
| `get_project` | Full ArchitectureProject JSON |
| `list_projects` | All projects with summary |
| `get_program` | Site + room program table |
| `list_versions` | Version history |
| `get_mep_plan` | Current MEP (all systems) |
| `list_details` | Detail drawing list |
| `get_boq` | Current BOQ / cost plan |
| `get_user_profile` | Architect-twin profile |
| `get_client_brief` | Client brief for a project |
| `list_client_changes` | Client change requests |
| `get_sync_contract` | SyncContract projection (for plugins) |

### Generate / mutate tools
| Tool | Description |
|---|---|
| `generate_design` | Text-to-floor-plan |
| `add_room` | Add a room |
| `remove_room` | Remove a room |
| `set_parameter` | Edit project/room parameter |
| `generate_mep` | Generate MEP service points |
| `edit_mep_point` | Move a MEP point |
| `generate_detail` | Generate a detail drawing |
| `delete_detail` | Remove a detail |
| `calculate_boq` | Calculate BOQ and cost |
| `edit_rate` | Update rate and recalculate |
| `edit_tile_spec` | Edit tile spec |
| `check_tn_rules` | Tamil Nadu advisory |
| `update_user_profile` | Update architect-twin profile |
| `update_client_brief` | Update project client brief |
| `create_client_change` | Create change request |
| `approve_change` | Approve a change |
| `reject_change` | Reject a change |
| `revert_change` | Revert an applied change |
| `show_affected_items` | Impact analysis for a change |
| `chat_edit_project` | Natural-language project edit |

### Export / render tools
| Tool | Description |
|---|---|
| `export_project` | Export (json/svg/png/dxf/ifc/sketchup/blender/rhino/…) |
| `export_drawing` | Alias for export_project |
| `render_project` | Render massing image |
| `generate_render_prompt` | Context-aware render prompt (Midjourney/SD) |
| `run_intelligence` | Spatial checks + Vastu |

### Sync + version tools
| Tool | Description |
|---|---|
| `push_sync_update` | Merge plugin sync payload |
| `restore_version` | Restore version snapshot |
| `create_version` | Manual version snapshot |

---

## Auth (optional)

Set `SCOTCH_MCP_TOKEN` in the server environment:

```bash
export SCOTCH_MCP_TOKEN=my-local-secret
python server.py
```

Pass the same token in mutating tool calls via the `_token` parameter
(`chat_edit_project`, `create_version`).

In local-only mode (default), leave `SCOTCH_MCP_TOKEN` unset — all tools
are accessible without a token.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: mcp` | `pip install mcp` inside the correct venv |
| `Backend unreachable` from `chat_edit_project` | Start the FastAPI backend first |
| Tool calls time out | Increase agent timeout; check backend load |
| `SCOTCH_MCP_TOKEN mismatch` | Match the token in server env and tool call |
| `Project not found` | Use `list_projects` to find the correct `project_id` |
