"""Phase 38 — Expanded MCP tools re-export.

Re-exports every callable tool from services/api/app/core/chat_tools.py so
services/mcp/server.py only needs to import from this module.

Coverage:
  Phase 24 — basic project CRUD, generate, intelligence, export, render
  Phase 29 — MEP generation + editing
  Phase 30 — detail drawings
  Phase 31 — BOQ / cost
  Phase 32 — Tamil Nadu advisory
  Phase 33 — user profile + client brief
  Phase 34 — client change management
  Phase 35 — render prompt generation
  Phase 37 — account mode (profile)
"""

from __future__ import annotations

import sys
import os

# Ensure services/api is importable when running server.py standalone
_api_root = os.path.join(os.path.dirname(__file__), "..", "api")
if os.path.isdir(_api_root) and _api_root not in sys.path:
    sys.path.insert(0, _api_root)

from app.core.chat_tools import (  # noqa: F401  (re-exported)
    # ── Phase 24 — core ──────────────────────────────────────────────────────
    add_room,
    export_project,
    generate_design,
    get_program,
    get_project,
    list_projects,
    list_versions,
    remove_room,
    render_project,
    restore_version,
    run_intelligence,
    set_parameter,
    # ── Phase 29 — MEP ───────────────────────────────────────────────────────
    edit_mep_point,
    generate_mep,
    get_mep_plan,
    # ── Phase 30 — Details ───────────────────────────────────────────────────
    delete_detail,
    generate_detail,
    list_details,
    # ── Phase 31 — BOQ / Cost ────────────────────────────────────────────────
    calculate_boq,
    edit_rate,
    edit_tile_spec,
    get_boq,
    # ── Phase 32 — Tamil Nadu ────────────────────────────────────────────────
    check_tn_rules,
    # ── Phase 33 — Profile + brief ───────────────────────────────────────────
    get_client_brief,
    get_user_profile,
    update_client_brief,
    update_user_profile,
    # ── Phase 34 — Client changes ────────────────────────────────────────────
    approve_change,
    create_client_change,
    list_client_changes,
    reject_change,
    revert_change,
    show_affected_items,
    # ── Phase 35 — Render prompt ─────────────────────────────────────────────
    export_drawing,
    generate_render_prompt_tool,
)


# ── Sync contract (from sync engine, not chat_tools) ─────────────────────────

def get_sync_contract(project_id: str) -> dict:
    """Return the SyncContract projection for a project (pull endpoint).

    Used by SketchUp, Revit, and Rhino plugins to reconstruct geometry.
    """
    from app.core.storage.factory import get_project_store
    from app.core.storage.base import LOCAL_USER_ID, ProjectNotFoundError
    from app.core.sync.engine import project_to_sync_contract

    store = get_project_store()
    try:
        stored = store.get_project(project_id, user_id=LOCAL_USER_ID)
    except ProjectNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    if stored.project is None:
        raise ValueError(f"Project '{project_id}' has no design yet.")
    version_ts = stored.updated_at.isoformat() if stored.updated_at else None
    contract = project_to_sync_contract(stored.project, project_id, version_ts)
    return contract.model_dump()


def push_sync_update(project_id: str, payload: dict) -> dict:
    """Merge a plugin sync payload into the canonical model (push endpoint).

    payload: SyncPayload as dict — { rooms: [...], source: "sketchup"|"revit" }
    Returns: { added, updated, flagged, conflicts, project }
    """
    from app.core.storage.factory import get_project_store
    from app.core.storage.base import LOCAL_USER_ID, ProjectNotFoundError
    from app.core.sync.engine import push_sync
    from app.core.sync.models import SyncPayload
    from app.core.validation.validator import validate_project

    store = get_project_store()
    try:
        stored = store.get_project(project_id, user_id=LOCAL_USER_ID)
    except ProjectNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    if stored.project is None:
        raise ValueError(f"Project '{project_id}' has no design yet.")

    sync_payload = SyncPayload.model_validate(payload)
    try:
        updated, diff = push_sync(stored.project, sync_payload)
    except ValueError as exc:
        raise ValueError(f"Sync merge failed: {exc}") from exc

    result = validate_project(updated)
    if not result.valid:
        raise ValueError(f"Sync result invalid: {'; '.join(result.errors)}")

    store.update_project(
        project_id,
        user_id=LOCAL_USER_ID,
        project=updated,
        change_type="sync",
        version_summary=(
            f"MCP sync from {sync_payload.source}: "
            f"{len(diff.added)} added, {len(diff.updated)} updated"
        ),
    )
    return {
        "added": diff.added,
        "updated": diff.updated,
        "flagged": diff.flagged,
        "conflicts": diff.conflicts,
        "project": updated.model_dump(),
    }


def chat_edit_project(project_id: str, message: str, token: str | None = None) -> dict:
    """Run a natural-language chat edit on a project via the chat engine.

    Equivalent to sending a message in the in-app chat panel — deterministic
    keyword routing + optional Anthropic fallback.

    Returns: { response, tool_calls, project } or error dict.
    """
    import httpx

    from auth import require_token  # noqa: local import
    require_token(token)

    url = f"http://localhost:8000/projects/{project_id}/chat"
    try:
        r = httpx.post(url, json={"message": message}, timeout=60.0)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        raise ValueError("Scotch backend not running — start with: uvicorn app.main:app --reload --port 8000")
    except httpx.HTTPStatusError as exc:
        raise ValueError(f"Chat endpoint returned {exc.response.status_code}: {exc.response.text}") from exc


def create_version(project_id: str, note: str = "", token: str | None = None) -> dict:
    """Create a named version snapshot for a project.

    Returns the version metadata (version_id, created_at, summary).
    """
    from auth import require_token  # noqa: local import
    require_token(token)

    from app.core.storage.factory import get_project_store
    from app.core.storage.base import LOCAL_USER_ID, ProjectNotFoundError

    store = get_project_store()
    try:
        stored = store.get_project(project_id, user_id=LOCAL_USER_ID)
    except ProjectNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    if stored.project is None:
        raise ValueError(f"Project '{project_id}' has no design yet.")

    stored = store.update_project(
        project_id,
        user_id=LOCAL_USER_ID,
        project=stored.project,
        change_type="edit",
        version_summary=note or "Manual version snapshot from MCP",
    )
    # Return latest version meta
    versions = store.list_versions(project_id, user_id=LOCAL_USER_ID)
    if versions:
        return versions[0].model_dump()
    return {"status": "ok", "note": note}
