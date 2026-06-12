from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models import ArchitectureProject, ProjectWarning
from app.core.validation import validate_project

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    prompt: str = Field(default="", max_length=2000)


class GenerateResponse(BaseModel):
    project: ArchitectureProject
    summary: str
    warnings: list[ProjectWarning]


@router.post("/from-prompt", response_model=GenerateResponse)
def generate_from_prompt(body: GenerateRequest) -> GenerateResponse:
    requirements = parse_prompt(body.prompt)
    project, summary = generate_floorplan(requirements)

    result = validate_project(project)
    if not result.valid:
        # The deterministic generator must always produce a valid layout;
        # reaching this branch is a generator bug, not a user error.
        raise HTTPException(
            status_code=500,
            detail={"message": "Generated layout failed validation", "errors": result.errors},
        )
    existing = {w.id for w in project.warnings}
    project.warnings.extend(w for w in result.warnings if w.id not in existing)

    return GenerateResponse(project=project, summary=summary, warnings=project.warnings)
