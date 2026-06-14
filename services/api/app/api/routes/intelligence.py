"""Intelligence API — Phase 13.

GET /projects/{id}/intelligence?vastu=false  → IntelligenceReport
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.intelligence import (
    IntelligenceReport,
    compute_areas,
    run_spatial_checks,
    run_vastu_checks,
)
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(prefix="/projects", tags=["intelligence"])


@router.get("/{project_id}/intelligence", response_model=IntelligenceReport)
def get_intelligence(
    project_id: str,
    vastu: bool = Query(False, description="Include Vastu Shastra suggestions"),
    store: ProjectStore = Depends(get_project_store),
) -> IntelligenceReport:
    try:
        stored = store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if stored.project is None:
        raise HTTPException(
            status_code=409,
            detail="Project has no design data — generate a floor plan first.",
        )

    project = stored.project
    return IntelligenceReport(
        project_id=project_id,
        spatial_checks=run_spatial_checks(project),
        area_summary=compute_areas(project),
        vastu_suggestions=run_vastu_checks(project) if vastu else None,
    )
