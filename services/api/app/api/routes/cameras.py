"""Stage 17.3 — Camera suggestions API.

GET /projects/{project_id}/cameras → list[CameraSuggestion]

Derives 5 camera presets from site dimensions and room positions.
No storage needed — presets are computed on every request from the project.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.architecture.cameras import derive_cameras
from app.core.models import CameraSuggestion
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(prefix="/projects", tags=["cameras"])


@router.get("/{project_id}/cameras", response_model=list[CameraSuggestion])
def get_cameras(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> list[CameraSuggestion]:
    try:
        stored = store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if stored.project is None:
        raise HTTPException(
            status_code=409,
            detail="Project has no design data — generate a floor plan first.",
        )

    return derive_cameras(stored.project)
