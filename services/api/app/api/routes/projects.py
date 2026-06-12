from fastapi import APIRouter, HTTPException

from app.core.architecture.sample_factory import create_sample_project
from app.core.models import ArchitectureProject
from app.core.validation import validate_project

router = APIRouter(prefix="/projects", tags=["projects"])


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
    # Merge validator-generated advisories with the factory's curated warnings.
    existing = {w.id for w in project.warnings}
    project.warnings.extend(w for w in result.warnings if w.id not in existing)
    return project
