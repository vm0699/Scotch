"""Phase 39 — Reference / scan-to-plan ingestion API.

POST   /projects/{id}/references                      — upload a reference file
GET    /projects/{id}/references                      — list reference assets
GET    /projects/{id}/references/{ref_id}             — get asset metadata
DELETE /projects/{id}/references/{ref_id}             — delete asset + file
GET    /projects/{id}/references/{ref_id}/file        — serve the binary file
PATCH  /projects/{id}/references/{ref_id}/calibrate  — set scale calibration
PATCH  /projects/{id}/references/{ref_id}/notes      — update notes / type
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.references.models import ReferenceAsset, ReferenceType, ScaleCalibration
from app.core.references.scale import compute_scale
from app.core.references.store import ReferenceStore, get_reference_store
from app.core.storage import LOCAL_USER_ID, ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(prefix="/projects", tags=["references"])

_ALLOWED_MIME: set[str] = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "image/svg+xml", "application/pdf",
}
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


def _check_project(project_id: str, store: ProjectStore) -> None:
    try:
        store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _get_asset(project_id: str, ref_id: str, refs: ReferenceStore) -> ReferenceAsset:
    try:
        return refs.get(LOCAL_USER_ID, project_id, ref_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post(
    "/{project_id}/references",
    response_model=ReferenceAsset,
    status_code=201,
    summary="Upload a reference image or PDF",
)
async def upload_reference(
    project_id: str,
    file: UploadFile = File(...),
    reference_type: str = Form(default="reference_image"),
    notes: str = Form(default=""),
    store: ProjectStore = Depends(get_project_store),
    refs: ReferenceStore = Depends(get_reference_store),
) -> ReferenceAsset:
    _check_project(project_id, store)
    mime = file.content_type or "application/octet-stream"
    if mime not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{mime}'. Allowed: {sorted(_ALLOWED_MIME)}",
        )
    data = await file.read()
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_FILE_BYTES // 1024 // 1024} MB limit")
    return refs.create(
        LOCAL_USER_ID,
        project_id,
        data,
        file.filename or "upload",
        mime,
        reference_type=reference_type,
        notes=notes,
    )


# ── List ──────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/references",
    response_model=list[ReferenceAsset],
    summary="List reference assets for a project",
)
def list_references(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    refs: ReferenceStore = Depends(get_reference_store),
) -> list[ReferenceAsset]:
    _check_project(project_id, store)
    return refs.list(LOCAL_USER_ID, project_id)


# ── Get metadata ──────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/references/{ref_id}",
    response_model=ReferenceAsset,
    summary="Get reference asset metadata",
)
def get_reference(
    project_id: str,
    ref_id: str,
    store: ProjectStore = Depends(get_project_store),
    refs: ReferenceStore = Depends(get_reference_store),
) -> ReferenceAsset:
    _check_project(project_id, store)
    return _get_asset(project_id, ref_id, refs)


# ── Serve binary file ─────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/references/{ref_id}/file",
    summary="Download the raw reference file",
)
def get_reference_file(
    project_id: str,
    ref_id: str,
    store: ProjectStore = Depends(get_project_store),
    refs: ReferenceStore = Depends(get_reference_store),
) -> FileResponse:
    _check_project(project_id, store)
    asset = _get_asset(project_id, ref_id, refs)
    file_path = refs.get_file_path(LOCAL_USER_ID, project_id, ref_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Reference file not found on disk")
    return FileResponse(
        path=str(file_path),
        media_type=asset.mime_type,
        filename=asset.file_name,
    )


# ── Scale calibration ─────────────────────────────────────────────────────────

class CalibrateRequest(BaseModel):
    p1_x: float
    p1_y: float
    p2_x: float
    p2_y: float
    known_distance_ft: float
    origin_x_ft: float = 0.0
    origin_y_ft: float = 0.0


@router.patch(
    "/{project_id}/references/{ref_id}/calibrate",
    response_model=ReferenceAsset,
    summary="Set scale calibration: two pixel points + known distance in feet",
)
def calibrate_reference(
    project_id: str,
    ref_id: str,
    body: CalibrateRequest,
    store: ProjectStore = Depends(get_project_store),
    refs: ReferenceStore = Depends(get_reference_store),
) -> ReferenceAsset:
    _check_project(project_id, store)
    _get_asset(project_id, ref_id, refs)
    try:
        calibration = compute_scale(
            body.p1_x, body.p1_y,
            body.p2_x, body.p2_y,
            body.known_distance_ft,
            body.origin_x_ft,
            body.origin_y_ft,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return refs.set_calibration(LOCAL_USER_ID, project_id, ref_id, calibration)


# ── Update notes / type ───────────────────────────────────────────────────────

class UpdateReferenceRequest(BaseModel):
    notes: str | None = None
    reference_type: str | None = None
    needs_review: bool | None = None


@router.patch(
    "/{project_id}/references/{ref_id}",
    response_model=ReferenceAsset,
    summary="Update reference notes, type, or review status",
)
def update_reference(
    project_id: str,
    ref_id: str,
    body: UpdateReferenceRequest,
    store: ProjectStore = Depends(get_project_store),
    refs: ReferenceStore = Depends(get_reference_store),
) -> ReferenceAsset:
    _check_project(project_id, store)
    asset = _get_asset(project_id, ref_id, refs)
    if body.notes is not None:
        asset.notes = body.notes
    if body.reference_type is not None:
        asset.reference_type = body.reference_type  # type: ignore[assignment]
    if body.needs_review is not None:
        asset.needs_review = body.needs_review
    return refs.update(LOCAL_USER_ID, project_id, asset)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete(
    "/{project_id}/references/{ref_id}",
    status_code=204,
    summary="Delete a reference asset and its file",
)
def delete_reference(
    project_id: str,
    ref_id: str,
    store: ProjectStore = Depends(get_project_store),
    refs: ReferenceStore = Depends(get_reference_store),
) -> Response:
    _check_project(project_id, store)
    try:
        refs.delete(LOCAL_USER_ID, project_id, ref_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)
