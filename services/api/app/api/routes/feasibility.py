"""Phase 40 — Feasibility / Yield Analysis API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user_id
from app.core.feasibility.engine import FeasibilityEngine
from app.core.models.project import Feasibility
from app.core.storage.factory import get_project_store
from app.core.storage import ProjectNotFoundError, ProjectStore

router = APIRouter(prefix="/projects", tags=["feasibility"])


def _load(project_id: str, store: ProjectStore):
    try:
        stored = store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(status_code=422, detail="Project has no design — generate a floor plan first.")
    return stored.project


@router.get("/{project_id}/feasibility", response_model=Feasibility)
def run_feasibility(
    project_id: str,
    road_width_ft: float = Query(default=0.0, ge=0, description="Road-facing width in feet (0 = use default TN setbacks)"),
    store: ProjectStore = Depends(get_project_store),
    _user_id: str = Depends(get_current_user_id),
) -> Feasibility:
    """Run residential feasibility analysis on the project site.

    Returns site area, usable footprint after TN setbacks, FSI/FAR envelope,
    and five development options (compact/balanced/spacious/future-ready/rental-friendly).
    Advisory only — verify with a licensed architect and CMDA/DTCP.
    """
    project = _load(project_id, store)
    engine = FeasibilityEngine()
    feasibility = engine.compute(project, road_width_ft=road_width_ft)

    # Persist the feasibility onto the project so it shows in the frontend
    updated = project.model_copy(update={"feasibility": feasibility})
    store.update_project(project_id, project=updated, change_type="edit")

    return feasibility
