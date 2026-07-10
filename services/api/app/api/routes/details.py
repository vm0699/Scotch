"""Phase 30 — Detail Drawing API routes.

POST /projects/{id}/details           — generate a detail drawing
GET  /projects/{id}/details           — list all details
GET  /projects/{id}/details/{did}     — get one detail (with full primitives)
DELETE /projects/{id}/details/{did}   — remove a detail
GET  /projects/{id}/details/{did}/svg — export detail as SVG bytes
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.architecture.detail_engine import DetailEngine
from app.core.models.project import DetailType
from app.core.storage.base import LOCAL_USER_ID
from app.core.storage.factory import get_project_store
from app.core.validation import validate_project

router = APIRouter(prefix="/projects", tags=["details"])


class DetailGenerateRequest(BaseModel):
    detail_type: DetailType
    source_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_project(project_id: str):
    store = get_project_store()
    stored = store.get_project(project_id, user_id=LOCAL_USER_ID)
    if stored is None or stored.project is None:
        raise HTTPException(status_code=404, detail="Project not found or no design generated yet")
    return stored, store


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/{project_id}/details", status_code=201)
def generate_detail(project_id: str, body: DetailGenerateRequest):
    stored, store = _get_project(project_id)
    project = stored.project
    try:
        drawing = DetailEngine.generate(project, body.detail_type, body.source_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    drawings = DetailEngine.replace_or_add(project.detail_drawings, drawing)
    project = project.model_copy(update={"detail_drawings": drawings})

    result = validate_project(project)
    if not result.valid:
        raise HTTPException(status_code=422, detail="; ".join(result.errors))

    store.update_project(project_id, project=project, change_type="regenerate", user_id=LOCAL_USER_ID)
    return drawing.model_dump()


@router.get("/{project_id}/details")
def list_details(project_id: str):
    stored, _ = _get_project(project_id)
    project = stored.project
    return {
        "detail_drawings": [
            {
                "id": d.id, "name": d.name, "detail_type": d.detail_type,
                "scale": d.scale, "view": d.view, "stale": d.stale,
                "confidence": d.confidence, "needs_review": d.needs_review,
                "source_object_ids": d.source_object_ids,
            }
            for d in project.detail_drawings
        ],
        "count": len(project.detail_drawings),
    }


@router.get("/{project_id}/details/{detail_id}")
def get_detail(project_id: str, detail_id: str):
    stored, _ = _get_project(project_id)
    project = stored.project
    drawing = next((d for d in project.detail_drawings if d.id == detail_id), None)
    if drawing is None:
        raise HTTPException(status_code=404, detail=f"Detail '{detail_id}' not found")
    return drawing.model_dump()


@router.delete("/{project_id}/details/{detail_id}", status_code=204)
def delete_detail(project_id: str, detail_id: str):
    stored, store = _get_project(project_id)
    project = stored.project
    drawings = DetailEngine.remove(project.detail_drawings, detail_id)
    if len(drawings) == len(project.detail_drawings):
        raise HTTPException(status_code=404, detail=f"Detail '{detail_id}' not found")
    project = project.model_copy(update={"detail_drawings": drawings})
    store.update_project(project_id, project=project, change_type="edit", user_id=LOCAL_USER_ID)


@router.get("/{project_id}/details/{detail_id}/svg")
def export_detail_svg(project_id: str, detail_id: str):
    from fastapi.responses import Response
    from app.core.exports.detail_exporter import export_detail_svg as _export

    stored, _ = _get_project(project_id)
    project = stored.project
    drawing = next((d for d in project.detail_drawings if d.id == detail_id), None)
    if drawing is None:
        raise HTTPException(status_code=404, detail=f"Detail '{detail_id}' not found")
    svg_bytes = _export(drawing)
    return Response(content=svg_bytes, media_type="image/svg+xml")
