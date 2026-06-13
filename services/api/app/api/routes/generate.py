from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.ai.factory import get_provider
from app.core.architecture.options_generator import generate_options as _generate_options
from app.core.architecture.regenerate import ChangeError, ParameterChange, apply_changes
from app.core.models import ArchitectureProject, ProjectWarning
from app.core.models.project import DesignOption
from app.core.validation import validate_project

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    prompt: str = Field(default="", max_length=2000)
    # If omitted, falls back to SCOTCH_GENERATION_MODE env setting (default: deterministic).
    mode: Literal["deterministic", "ai", "hybrid"] | None = None


class GenerateResponse(BaseModel):
    project: ArchitectureProject
    summary: str
    warnings: list[ProjectWarning]


class RegenerateRequest(BaseModel):
    project: ArchitectureProject
    changes: list[ParameterChange] = Field(min_length=1)


@router.post("/from-prompt", response_model=GenerateResponse)
def generate_from_prompt(body: GenerateRequest) -> GenerateResponse:
    settings = get_settings()
    effective_mode = body.mode or settings.generation_mode

    try:
        provider = get_provider(effective_mode, settings)
        project, summary = provider.generate_project(body.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result = validate_project(project)
    if not result.valid:
        raise HTTPException(
            status_code=500,
            detail={"message": "Generated layout failed validation", "errors": result.errors},
        )
    existing = {w.id for w in project.warnings}
    project.warnings.extend(w for w in result.warnings if w.id not in existing)

    return GenerateResponse(project=project, summary=summary, warnings=project.warnings)


class OptionsRequest(BaseModel):
    prompt: str = Field(default="", max_length=2000)
    mode: Literal["deterministic", "ai", "hybrid"] | None = None


class OptionsResponse(BaseModel):
    options: list[DesignOption]
    prompt: str


@router.post("/options", response_model=OptionsResponse)
def generate_options_endpoint(body: OptionsRequest) -> OptionsResponse:
    """Generate compact / balanced / spacious design variants from a prompt."""
    settings = get_settings()
    effective_mode = body.mode or settings.generation_mode
    try:
        options = _generate_options(body.prompt, effective_mode, settings)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return OptionsResponse(options=options, prompt=body.prompt)


@router.post("/regenerate", response_model=GenerateResponse)
def regenerate(body: RegenerateRequest) -> GenerateResponse:
    """Apply parameter/room changes to a project and re-pack the layout."""
    try:
        project, summary = apply_changes(body.project, body.changes)
    except ChangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = validate_project(project)
    if not result.valid:
        raise HTTPException(
            status_code=500,
            detail={"message": "Regenerated layout failed validation", "errors": result.errors},
        )
    existing = {w.id for w in project.warnings}
    project.warnings.extend(w for w in result.warnings if w.id not in existing)

    return GenerateResponse(project=project, summary=summary, warnings=project.warnings)
