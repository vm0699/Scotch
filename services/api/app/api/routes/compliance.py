"""Compliance API — Phase 27.3 (NBC) + Phase 32 (TN advisory).

GET /projects/{id}/compliance               → ComplianceReport (NBC)
GET /projects/{id}/compliance/tn            → TNAdvisoryReport
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.context import get_current_user_id
from app.core.compliance import (
    ComplianceReport,
    DEFAULT_FRONT_SETBACK,
    DEFAULT_MAX_FSI,
    DEFAULT_REAR_SETBACK,
    DEFAULT_SIDE_SETBACK,
    TNAdvisoryReport,
    run_compliance,
    run_tn_advisory,
)
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(prefix="/projects", tags=["compliance"])


@router.get("/{project_id}/compliance", response_model=ComplianceReport)
def get_compliance(
    project_id: str,
    front: float = Query(DEFAULT_FRONT_SETBACK, description="Front setback in feet (default 3 m = 9.84 ft)"),
    side:  float = Query(DEFAULT_SIDE_SETBACK,  description="Side setback per side in feet (default 1.5 m = 4.92 ft)"),
    rear:  float = Query(DEFAULT_REAR_SETBACK,  description="Rear setback in feet (default 3 m = 9.84 ft)"),
    max_fsi: float = Query(DEFAULT_MAX_FSI,     description="Allowed FSI/FAR (default 1.5 for urban residential)"),
    zone: str = Query("urban_residential",       description="NBC zone context for the report"),
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> ComplianceReport:
    try:
        stored = store.get_project(project_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if stored.project is None:
        raise HTTPException(
            status_code=409,
            detail="Project has no design data — generate a floor plan first.",
        )

    return run_compliance(
        stored.project,
        project_id,
        front_setback=front,
        side_setback=side,
        rear_setback=rear,
        max_fsi=max_fsi,
        zone=zone,
    )


@router.get("/{project_id}/compliance/tn", response_model=TNAdvisoryReport)
def get_tn_advisory(
    project_id: str,
    road_width: float = Query(0.0, description="Road frontage width in feet (0 = not specified)"),
    zone: str = Query("residential_basic", description="CMDA/DTCP zone classification"),
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> TNAdvisoryReport:
    """Run Tamil Nadu advisory checks (CMDA/DTCP). Advisory only — not engineering certification."""
    try:
        stored = store.get_project(project_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(
            status_code=409,
            detail="Project has no design data — generate a floor plan first.",
        )
    return run_tn_advisory(
        stored.project,
        project_id,
        road_width_ft=road_width if road_width > 0 else None,
        zone=zone,
    )
