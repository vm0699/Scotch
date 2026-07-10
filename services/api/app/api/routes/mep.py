"""Phase 29 — MEP service layer REST endpoints.

POST /projects/{project_id}/mep           — generate (or regenerate) MEP layers
GET  /projects/{project_id}/mep           — return current MEP plan
PATCH /projects/{project_id}/mep/points/{point_id} — move a service point
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import app.core.chat_tools as mcp_tools
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(prefix="/projects", tags=["mep"])


# ── Request models ────────────────────────────────────────────────────────────


class MepGenerateRequest(BaseModel):
    systems: Optional[list[str]] = None  # None → all four


class MepMovePointRequest(BaseModel):
    x: float
    y: float


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/{project_id}/mep")
def generate_mep(
    project_id: str,
    req: MepGenerateRequest = MepGenerateRequest(),
    store: ProjectStore = Depends(get_project_store),
) -> dict:
    """Generate MEP service points. Specify systems or omit for all four."""
    try:
        store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        return mcp_tools.generate_mep(project_id, systems=req.systems)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{project_id}/mep")
def get_mep(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict:
    """Return the current MEP plan."""
    try:
        store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        return mcp_tools.get_mep_plan(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{project_id}/mep/points/{point_id}")
def move_mep_point(
    project_id: str,
    point_id: str,
    req: MepMovePointRequest,
    store: ProjectStore = Depends(get_project_store),
) -> dict:
    """Move a service point and mark it as user_override."""
    try:
        store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        return mcp_tools.edit_mep_point(project_id, point_id, req.x, req.y)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
