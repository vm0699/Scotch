from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.architecture.sample_factory import create_sample_project
from app.core.models import ArchitectureProject, DesignOption
from app.core.storage import (
    ProjectNotFoundError,
    ProjectStore,
    ProjectSummary,
    StoredProject,
    get_project_store,
)
from app.core.validation import validate_project

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    prompt: str | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    prompt: str | None = None
    project: ArchitectureProject | None = None
    options: list[DesignOption] | None = None


def _validated(project: ArchitectureProject | None) -> ArchitectureProject | None:
    """Reject invalid design data; merge validator advisories into warnings."""
    if project is None:
        return None
    result = validate_project(project)
    if not result.valid:
        raise HTTPException(
            status_code=422,
            detail={"message": "Project failed validation", "errors": result.errors},
        )
    existing = {w.id for w in project.warnings}
    project.warnings.extend(w for w in result.warnings if w.id not in existing)
    return project


@router.get("/sample", response_model=ArchitectureProject)
def get_sample_project() -> ArchitectureProject:
    """Return the canonical sample project, validated and annotated."""
    project = create_sample_project()
    result = validate_project(project)
    if not result.valid:
        raise HTTPException(
            status_code=500,
            detail={"message": "Sample project failed validation", "errors": result.errors},
        )
    existing = {w.id for w in project.warnings}
    project.warnings.extend(w for w in result.warnings if w.id not in existing)
    return project


@router.post("", response_model=StoredProject, status_code=201)
def create_project(
    body: CreateProjectRequest,
    store: ProjectStore = Depends(get_project_store),
) -> StoredProject:
    return store.create_project(name=body.name, prompt=body.prompt)


@router.get("", response_model=list[ProjectSummary])
def list_projects(
    store: ProjectStore = Depends(get_project_store),
) -> list[ProjectSummary]:
    return store.list_projects()


@router.get("/{project_id}", response_model=StoredProject)
def get_project(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> StoredProject:
    try:
        return store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}", response_model=StoredProject)
def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    store: ProjectStore = Depends(get_project_store),
) -> StoredProject:
    try:
        return store.update_project(
            project_id,
            name=body.name,
            prompt=body.prompt,
            project=_validated(body.project),
            options=body.options,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> None:
    try:
        store.delete_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
