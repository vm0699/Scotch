"""Phase 34 — Client Change Management API routes.

POST   /projects/{id}/changes              — create a change request
GET    /projects/{id}/changes              — list all change requests
GET    /projects/{id}/changes/{cid}        — get one change request
PATCH  /projects/{id}/changes/{cid}        — update status / summary
GET    /projects/{id}/changes/{cid}/affected — compute affected items
DELETE /projects/{id}/changes/{cid}        — delete a change
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.core.changes.affected_items import compute_affected_items
from app.core.changes.models import AffectedItems, ChangeStatus, ClientChangeRequest
from app.core.changes.store import ChangeStore, get_change_store
from app.core.storage import LOCAL_USER_ID, ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(prefix="/projects", tags=["changes"])


# ── Request / response schemas ────────────────────────────────────────────────

class CreateChangeRequest(BaseModel):
    request_text: str
    source: str = "client"
    priority: str = "medium"
    compute_affected: bool = True


class UpdateChangeRequest(BaseModel):
    status: ChangeStatus | None = None
    summary: str | None = None
    cost_impact: str | None = None
    note: str | None = None
    before_version: str | None = None
    after_version: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_project(project_id: str, store: ProjectStore):
    try:
        return store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/changes", response_model=ClientChangeRequest, status_code=201)
def create_change(
    project_id: str,
    body: CreateChangeRequest,
    store: ProjectStore = Depends(get_project_store),
    changes: ChangeStore = Depends(get_change_store),
) -> ClientChangeRequest:
    stored = _get_project(project_id, store)
    change = changes.create(LOCAL_USER_ID, project_id, body.request_text, body.source, body.priority)

    # Optionally compute affected items immediately
    if body.compute_affected and stored.project is not None:
        affected = compute_affected_items(change.id, body.request_text, stored.project)
        change.affected_items = affected
        change.affected_modules = list({item.module for items in [
            affected.rooms, affected.mep, affected.boq,
            affected.compliance, affected.details, affected.exports, affected.plugins
        ] for item in items})
        change.summary = affected.summary
        change.cost_impact = affected.cost_impact
        change = changes.update(LOCAL_USER_ID, project_id, change)

    return change


@router.get("/{project_id}/changes", response_model=list[ClientChangeRequest])
def list_changes(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    changes: ChangeStore = Depends(get_change_store),
) -> list[ClientChangeRequest]:
    _get_project(project_id, store)
    return changes.list(LOCAL_USER_ID, project_id)


@router.get("/{project_id}/changes/{change_id}", response_model=ClientChangeRequest)
def get_change(
    project_id: str,
    change_id: str,
    store: ProjectStore = Depends(get_project_store),
    changes: ChangeStore = Depends(get_change_store),
) -> ClientChangeRequest:
    _get_project(project_id, store)
    try:
        return changes.get(LOCAL_USER_ID, project_id, change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}/changes/{change_id}", response_model=ClientChangeRequest)
def update_change(
    project_id: str,
    change_id: str,
    body: UpdateChangeRequest,
    store: ProjectStore = Depends(get_project_store),
    changes: ChangeStore = Depends(get_change_store),
) -> ClientChangeRequest:
    _get_project(project_id, store)
    try:
        change = changes.get(LOCAL_USER_ID, project_id, change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if body.status is not None:
        change.status = body.status
        # When applying a change, bump the project revision metadata
        if body.status == "applied" and store.get_project(project_id).project is not None:
            stored = store.get_project(project_id)
            if stored.project is not None:
                from app.core.changes.revisions import bump_revision
                stored.project.revision_meta = bump_revision(
                    stored.project.revision_meta,
                    note=change.request_text[:100],
                )
                store.update_project(project_id, project=stored.project, change_type="client_change",
                                     version_summary=f"Client change: {change.request_text[:80]}")
    if body.summary is not None:
        change.summary = body.summary
    if body.cost_impact is not None:
        change.cost_impact = body.cost_impact
    if body.before_version is not None:
        change.before_version = body.before_version
    if body.after_version is not None:
        change.after_version = body.after_version

    return changes.update(LOCAL_USER_ID, project_id, change)


@router.get("/{project_id}/changes/{change_id}/affected", response_model=AffectedItems)
def get_affected_items(
    project_id: str,
    change_id: str,
    store: ProjectStore = Depends(get_project_store),
    changes: ChangeStore = Depends(get_change_store),
) -> AffectedItems:
    stored = _get_project(project_id, store)
    try:
        change = changes.get(LOCAL_USER_ID, project_id, change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if stored.project is None:
        raise HTTPException(status_code=409, detail="Project has no design — generate a floor plan first.")

    return compute_affected_items(change.id, change.request_text, stored.project)


@router.delete("/{project_id}/changes/{change_id}")
def delete_change(
    project_id: str,
    change_id: str,
    store: ProjectStore = Depends(get_project_store),
    changes: ChangeStore = Depends(get_change_store),
) -> Response:
    _get_project(project_id, store)
    try:
        changes.get(LOCAL_USER_ID, project_id, change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    changes.delete(LOCAL_USER_ID, project_id, change_id)
    return Response(status_code=204)
