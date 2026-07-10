"""User preference + client brief models — Phase 33/37."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

AccountMode = Literal["local", "cloud"]


# ── User preference profile (sidecar, per-user) ───────────────────────────────

class UserProfile(BaseModel):
    """Architect-twin preference profile. Stored as sidecar JSON per user."""
    role: Literal["owner", "architect", "student", "other"] = "architect"
    preferred_units: Literal["feet", "meters"] = "feet"
    default_location: str = "India"                   # e.g. "Tamil Nadu, India"
    default_style: str = "modern minimal"
    default_orientation: str = "east"
    # Per-room-type size multipliers (1.0 = standard, 0.85 = compact, 1.2 = spacious)
    preferred_room_sizes: dict[str, float] = Field(default_factory=dict)
    material_preferences: list[str] = Field(default_factory=list)
    # Workspace layer preferences
    output_preferences: list[str] = Field(default_factory=list)
    explanation_style: Literal["brief", "detailed"] = "brief"
    common_project_types: list[str] = Field(default_factory=list)
    # Phase 37 — cloud/auth readiness fields
    account_mode: AccountMode = "local"
    display_name: str = ""
    cloud_email: str | None = None
    cloud_user_id: str | None = None


# ── Client brief (inline in ArchitectureProject) ──────────────────────────────

BudgetLevel = Literal["economy", "standard", "premium"]
ParkingPreference = Literal["none", "two_wheeler", "car", "both"]


class ClientBrief(BaseModel):
    """Client brief — inline in ArchitectureProject, versions with the design."""
    family_name: str = ""
    family_size: int = 0                               # 0 = not specified
    lifestyle: str = ""                                # "nuclear", "joint family", etc.
    budget_level: BudgetLevel = "standard"
    budget_inr: float = 0.0                            # rough total budget; 0 = not specified
    style_preference: str = ""
    vastu_preference: bool = False
    parking_preference: ParkingPreference = "car"
    future_expansion: bool = False
    special_needs: list[str] = Field(default_factory=list)
    material_preference: str = ""
    notes: str = ""
