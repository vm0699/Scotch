"""Export API — Phase 7 + 11 (software adapters) + 12 (presentation sheets) + 13 (schedule).

POST /projects/{id}/exports/{format}  → run exporter, save file, append manifest,
                                        return ExportManifest entry.
GET  /projects/{id}/exports           → list manifest entries.
GET  /projects/{id}/exports/{filename}→ FileResponse download.

format ∈ json | svg | png | dxf | sketchup | blender | sheet_svg | sheet_pdf
        | schedule_json | schedule_csv
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.exports import (
    export_blender,
    export_dxf,
    export_json,
    export_png,
    export_schedule_csv,
    export_schedule_json,
    export_sheet_pdf,
    export_sheet_svg,
    export_sketchup,
    export_svg,
)
from app.core.models import ExportManifest
from app.core.storage import (
    ProjectNotFoundError,
    ProjectStore,
    get_project_store,
)
from app.core.validation import validate_project

ExportFormat = Literal[
    "json", "svg", "png", "dxf",
    "sketchup", "blender",
    "sheet_svg", "sheet_pdf",
    "schedule_json", "schedule_csv",
]

_MIME = {
    "json":      "application/json",
    "svg":       "image/svg+xml",
    "png":       "image/png",
    "dxf":       "application/dxf",
    "sketchup":  "text/plain",
    "blender":   "text/x-python",
    "rb":        "text/plain",
    "py":        "text/x-python",
    "pdf":       "application/pdf",
    "csv":       "text/csv",
}

router = APIRouter(prefix="/projects", tags=["exports"])


_EXT = {
    "json":          "json",
    "svg":           "svg",
    "png":           "png",
    "dxf":           "dxf",
    "sketchup":      "rb",
    "blender":       "py",
    "sheet_svg":     "svg",
    "sheet_pdf":     "pdf",
    "schedule_json": "json",
    "schedule_csv":  "csv",
}

_BASENAME = {
    "sheet_svg":     "presentation_sheet",
    "sheet_pdf":     "presentation_sheet",
    "schedule_json": "room_schedule",
    "schedule_csv":  "room_schedule",
}


def _export_filename(project_id: str, fmt: str) -> str:
    ext  = _EXT.get(fmt, fmt)
    base = _BASENAME.get(fmt, "floor_plan")
    return f"{base}.{ext}"


@router.post("/{project_id}/exports/{fmt}", response_model=ExportManifest, status_code=201)
def trigger_export(
    project_id: str,
    fmt: ExportFormat,
    store: ProjectStore = Depends(get_project_store),
) -> ExportManifest:
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
    result = validate_project(project)
    if not result.valid:
        raise HTTPException(
            status_code=422,
            detail={"message": "Project failed validation", "errors": result.errors},
        )

    filename = _export_filename(project_id, fmt)
    output_path: Path = store.get_export_path(project_id, filename)

    if fmt == "json":
        export_json(project, output_path)
    elif fmt == "svg":
        export_svg(project, output_path)
    elif fmt == "png":
        export_png(project, output_path)
    elif fmt == "dxf":
        export_dxf(project, output_path)
    elif fmt == "sketchup":
        export_sketchup(project, output_path)
    elif fmt == "blender":
        export_blender(project, output_path)
    elif fmt == "sheet_svg":
        export_sheet_svg(project, output_path)
    elif fmt == "sheet_pdf":
        export_sheet_pdf(project, output_path)
    elif fmt == "schedule_json":
        export_schedule_json(project, output_path)
    elif fmt == "schedule_csv":
        export_schedule_csv(project, output_path)

    manifest = ExportManifest(
        filename=filename,
        format=fmt,
        path=str(output_path),
        created_at=datetime.now(timezone.utc),
    )
    store.save_export_manifest(project_id, manifest)
    return manifest


@router.get("/{project_id}/exports", response_model=list[ExportManifest])
def list_exports(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> list[ExportManifest]:
    try:
        return store.list_export_manifests(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/exports/{filename}")
def download_export(
    project_id: str,
    filename: str,
    store: ProjectStore = Depends(get_project_store),
) -> FileResponse:
    try:
        path = store.get_export_path(project_id, filename)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"Export file '{filename}' not found."
        )

    ext = filename.rsplit(".", 1)[-1].lower()
    media_type = _MIME.get(ext, "application/octet-stream")
    return FileResponse(path=str(path), media_type=media_type, filename=filename)
