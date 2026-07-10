"""Phase 23.4 — Render route.

POST /projects/{project_id}/render  — generate a render from a massing capture.
GET  /render/styles                 — list the 5 built-in style presets.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.ai.provider import get_render_provider
from app.core.render.prompt_generator import generate_all_render_prompts, generate_render_prompt
from app.core.render.styles import RenderStyle, list_styles, get_style
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(tags=["render"])


# ── Schema ────────────────────────────────────────────────────────────────────


class RenderRequest(BaseModel):
    camera_id: str
    style: str = "photorealistic_exterior"
    conditioning_image_b64: str | None = None
    # Phase 35 — camera_name drives the context-aware render prompt
    camera_name: str | None = None


class RenderPromptItem(BaseModel):
    name: str
    label: str
    view: str
    prompt: str


class RenderResponse(BaseModel):
    render_b64: str
    style: str
    camera_id: str


class StyleInfo(BaseModel):
    id: str
    name: str
    description: str
    swatch_color: str


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/projects/{project_id}/render/prompts", response_model=list[RenderPromptItem])
def get_render_prompts(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> list[RenderPromptItem]:
    """Return context-aware render prompts for all standard camera views."""
    try:
        stored = store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(status_code=409, detail="Project has no design — generate first.")
    prompts = generate_all_render_prompts(stored.project)
    return [RenderPromptItem(**p) for p in prompts]


@router.get("/render/styles", response_model=list[StyleInfo])
def get_render_styles() -> list[StyleInfo]:
    """Return the 5 built-in render style presets."""
    return [
        StyleInfo(
            id=s.id,
            name=s.name,
            description=s.description,
            swatch_color=s.swatch_color,
        )
        for s in list_styles()
    ]


@router.post("/projects/{project_id}/render", response_model=RenderResponse)
def create_render(
    project_id: str,
    req: RenderRequest,
    store: ProjectStore = Depends(get_project_store),
) -> RenderResponse:
    """Render the massing capture with the given camera preset and style."""
    if not req.camera_id:
        raise HTTPException(status_code=422, detail="camera_id is required")

    try:
        stored = store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if stored.project is None:
        raise HTTPException(
            status_code=409,
            detail="Project has no design data — generate a floor plan first.",
        )

    provider = get_render_provider()
    try:
        img_bytes = provider.render_image(
            stored.project,
            req.camera_id,
            req.style,
            req.conditioning_image_b64,
            prompt_override=generate_render_prompt(stored.project, req.camera_name) if req.camera_name else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Render failed: {exc}") from exc

    return RenderResponse(
        render_b64=base64.b64encode(img_bytes).decode(),
        style=req.style,
        camera_id=req.camera_id,
    )
