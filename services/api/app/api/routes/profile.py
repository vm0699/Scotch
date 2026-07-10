"""Phase 33/37 — User profile + client brief + account-mode API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.chat_tools import (
    get_client_brief,
    get_user_profile,
    update_client_brief,
    update_user_profile,
)

router = APIRouter(prefix="/profile", tags=["profile"])


# ── User profile ──────────────────────────────────────────────────────────────


class ProfileUpdate(BaseModel):
    role: str | None = None
    preferred_units: str | None = None
    default_location: str | None = None
    default_style: str | None = None
    default_orientation: str | None = None
    explanation_style: str | None = None
    # Phase 37 — account-mode fields
    account_mode: str | None = None
    display_name: str | None = None
    cloud_email: str | None = None
    cloud_user_id: str | None = None


@router.get("", summary="Get user architect-twin profile")
def get_profile():
    return get_user_profile("local-user")


@router.put("", summary="Update user architect-twin profile")
def put_profile(body: ProfileUpdate):
    return update_user_profile(
        "local-user",
        role=body.role,
        preferred_units=body.preferred_units,
        default_location=body.default_location,
        default_style=body.default_style,
        default_orientation=body.default_orientation,
        explanation_style=body.explanation_style,
        account_mode=body.account_mode,
        display_name=body.display_name,
        cloud_email=body.cloud_email,
        cloud_user_id=body.cloud_user_id,
    )


# ── Client brief (per project) ────────────────────────────────────────────────


class ClientBriefUpdate(BaseModel):
    family_name: str | None = None
    family_size: int | None = None
    lifestyle: str | None = None
    budget_level: str | None = None
    budget_inr: float | None = None
    style_preference: str | None = None
    vastu_preference: bool | None = None
    parking_preference: str | None = None
    future_expansion: bool | None = None
    material_preference: str | None = None
    notes: str | None = None


@router.get("/projects/{project_id}/brief", summary="Get client brief for a project")
def get_brief(project_id: str):
    try:
        return get_client_brief(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/projects/{project_id}/brief", summary="Update client brief for a project")
def put_brief(project_id: str, body: ClientBriefUpdate):
    try:
        return update_client_brief(
            project_id,
            family_name=body.family_name,
            family_size=body.family_size,
            lifestyle=body.lifestyle,
            budget_level=body.budget_level,
            budget_inr=body.budget_inr,
            style_preference=body.style_preference,
            vastu_preference=body.vastu_preference,
            parking_preference=body.parking_preference,
            future_expansion=body.future_expansion,
            material_preference=body.material_preference,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
