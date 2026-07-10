"""Phase 25 — Round-trip sync routes.

GET  /projects/{project_id}/sync  → SyncContract  (pull: plugin reads canonical model)
POST /projects/{project_id}/sync  → SyncResponse  (push: plugin writes edits back)

The push path:
  1. Loads the current project from the store.
  2. Calls engine.push_sync() to merge the payload and detect conflicts.
  3. Validates the merged model (validator gate).
  4. Auto-snapshots with change_type="sync" via update_project().
  5. Returns the updated project + diff.

The pull path:
  1. Loads the current project.
  2. Projects it into the minimal SyncContract representation.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.models import ArchitectureProject
from app.core.storage import get_project_store
from app.core.storage.base import LOCAL_USER_ID, ProjectNotFoundError, ProjectStore
from app.core.sync.engine import project_to_sync_contract, push_sync
from app.core.sync.models import SyncContract, SyncDiff, SyncPayload
from app.core.validation.validator import validate_project

router = APIRouter(tags=["sync"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load(store: ProjectStore, project_id: str) -> ArchitectureProject:
    """Return the ArchitectureProject or raise 404/409."""
    try:
        stored = store.get_project(project_id, user_id=LOCAL_USER_ID)
    except ProjectNotFoundError:
        raise HTTPException(404, f"Project '{project_id}' not found")
    if stored.project is None:
        raise HTTPException(409, "Project exists but has no generated design yet")
    return stored.project


# ── Pull route ────────────────────────────────────────────────────────────────


@router.get("/projects/{project_id}/sync", response_model=SyncContract)
def pull_sync(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> SyncContract:
    """Return the canonical SyncContract projection for the requested project.

    Plugins call this to reconstruct or update local geometry without
    downloading the full ArchitectureProject JSON.
    """
    try:
        stored = store.get_project(project_id, user_id=LOCAL_USER_ID)
    except ProjectNotFoundError:
        raise HTTPException(404, f"Project '{project_id}' not found")
    if stored.project is None:
        raise HTTPException(409, "Project exists but has no generated design yet")
    version_ts = stored.updated_at.isoformat() if stored.updated_at else None
    return project_to_sync_contract(stored.project, project_id, version_ts)


# ── Push route ────────────────────────────────────────────────────────────────


class SyncPushResponse(SyncDiff):
    """Response to a push — the diff plus the updated project."""

    project: ArchitectureProject


@router.post("/projects/{project_id}/sync", response_model=SyncPushResponse)
def push_sync_route(
    project_id: str,
    payload: SyncPayload,
    store: ProjectStore = Depends(get_project_store),
) -> SyncPushResponse:
    """Merge a plugin's SyncPayload into the canonical model.

    On success: auto-snapshots with change_type="sync"; returns the merged
    ArchitectureProject plus a SyncDiff describing every change.
    On validation failure: 422 with detail listing the errors.
    """
    project = _load(store, project_id)

    # Merge — may raise ValueError for sub-MIN_ROOM_DIM dimensions.
    try:
        updated, diff = push_sync(project, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    # Validator gate — structural errors bubble as 422.
    result = validate_project(updated)
    if not result.valid:
        raise HTTPException(422, "; ".join(result.errors))

    # Persist with an automatic version snapshot.
    store.update_project(
        project_id,
        user_id=LOCAL_USER_ID,
        project=updated,
        change_type="sync",
        version_summary=(
            f"Sync from {payload.source}: "
            f"{len(diff.added)} added, {len(diff.updated)} updated, "
            f"{len(diff.flagged)} flagged"
        ),
    )

    return SyncPushResponse(
        added=diff.added,
        updated=diff.updated,
        flagged=diff.flagged,
        conflicts=diff.conflicts,
        project=updated,
    )
