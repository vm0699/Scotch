"""BOQ / Cost endpoints — Phase 31.

POST /projects/{id}/boq/calculate  → run QuantityEngine, return updated project
GET  /projects/{id}/boq            → return CostPlan summary
POST /projects/{id}/boq/rates      → update a rate entry and recalculate
GET  /projects/{id}/boq/export     → download BOQ as CSV or JSON
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.auth.context import get_current_user_id
from app.core.boq.quantity_engine import QuantityEngine
from app.core.models.project import RateEntry
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store
from app.core.validation import validate_project

router = APIRouter(prefix="/projects", tags=["boq"])


class RateUpdateRequest(BaseModel):
    category: str
    item: str
    rate: float
    unit: str = ""
    source: str = "manual"


@router.post("/{project_id}/boq/calculate")
def calculate_boq(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Run QuantityEngine and persist the updated cost_plan + material_plan."""
    try:
        stored = store.get_project(project_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(status_code=409, detail="No design data — generate first.")
    project = stored.project
    engine = QuantityEngine(project)
    updated_mat, cost = engine.build_boq()
    project = project.model_copy(update={"material_plan": updated_mat, "cost_plan": cost})
    result = validate_project(project)
    if not result.valid:
        raise HTTPException(status_code=422, detail={"errors": result.errors})
    store.update_project(project_id, project=project, user_id=user_id, change_type="regenerate")
    return project.model_dump()


@router.get("/{project_id}/boq")
def get_boq(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Return the current cost plan summary for a project."""
    try:
        stored = store.get_project(project_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(status_code=409, detail="No design data — generate first.")
    cp = stored.project.cost_plan
    return {
        "generated": cp.generated,
        "grand_total": cp.grand_total,
        "category_totals": [ct.model_dump() for ct in cp.category_totals],
        "missing_rates": cp.missing_rates,
        "assumptions": cp.assumptions,
        "confidence": cp.confidence,
        "needs_review": cp.needs_review,
        "boq_items": [item.model_dump() for item in cp.boq_items],
    }


@router.post("/{project_id}/boq/rates")
def update_rate(
    project_id: str,
    req: RateUpdateRequest,
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Update a rate entry and recalculate BOQ."""
    try:
        stored = store.get_project(project_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(status_code=409, detail="No design data — generate first.")
    project = stored.project
    rates = list(project.material_plan.editable_rates)
    rates = [r for r in rates if not (r.category == req.category and r.item == req.item)]
    rates.append(RateEntry(category=req.category, item=req.item,
                           unit=req.unit, rate=req.rate, source=req.source))
    mat = project.material_plan.model_copy(update={"editable_rates": rates})
    project = project.model_copy(update={"material_plan": mat})
    engine = QuantityEngine(project)
    updated_mat, cost = engine.build_boq()
    project = project.model_copy(update={"material_plan": updated_mat, "cost_plan": cost})
    result = validate_project(project)
    if not result.valid:
        raise HTTPException(status_code=422, detail={"errors": result.errors})
    store.update_project(project_id, project=project, user_id=user_id, change_type="edit")
    return project.model_dump()


@router.get("/{project_id}/boq/export")
def export_boq(
    project_id: str,
    format: Literal["csv", "json"] = "csv",
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> FileResponse:
    """Download BOQ as CSV or JSON."""
    from app.core.exports.boq_exporter import export_boq_csv, export_boq_json
    try:
        stored = store.get_project(project_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(status_code=409, detail="No design — generate first.")
    project = stored.project
    if not project.cost_plan.generated:
        raise HTTPException(status_code=409, detail="BOQ not calculated — run /boq/calculate first.")
    ext = format
    out = store.get_export_path(project_id, f"boq.{ext}", user_id=user_id)
    if format == "csv":
        export_boq_csv(project, out)
        media_type = "text/csv"
    else:
        export_boq_json(project, out)
        media_type = "application/json"
    return FileResponse(path=str(out), media_type=media_type, filename=f"boq.{ext}")
