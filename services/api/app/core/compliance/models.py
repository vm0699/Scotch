"""Compliance report models — Phase 27.1 + Phase 32 (TN advisory)."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

RuleStatus = Literal["pass", "fail", "warn", "skip"]
TNStatus = Literal["pass", "fail", "warn", "skip", "advisory", "missing_input"]


class RuleResult(BaseModel):
    rule_id: str
    category: str          # "fsi" | "setback" | "room_area" | "ventilation" | "parking" | "stair"
    description: str       # human-readable rule description
    status: RuleStatus
    value: float | None = None      # actual measured value
    limit: float | None = None      # code-mandated limit
    unit: str | None = None         # "ft²" | "m²" | "ft" | "%" | None
    message: str = ""               # plain-English finding


class ComplianceReport(BaseModel):
    project_id: str
    zone: str = "urban_residential"   # NBC zone context
    passes_review: bool
    summary: str
    rules: list[RuleResult]
    # Setback context used for this check
    front_setback_ft: float
    side_setback_ft: float
    rear_setback_ft: float
    max_fsi: float


# ── Tamil Nadu Advisory models (Phase 32) ────────────────────────────────────

class TNRuleResult(BaseModel):
    rule_id: str
    category: str
    title: str
    status: TNStatus
    source_name: str
    source_section: str = ""
    source_url_or_path: str = ""
    confidence: float = 0.75
    needs_professional_verification: bool = True
    is_placeholder: bool = True
    value: float | None = None
    limit: float | None = None
    unit: str | None = None
    message: str = ""
    missing_inputs: list[str] = Field(default_factory=list)
    advisory_items: list[str] = Field(default_factory=list)


_TN_DISCLAIMER = (
    "These are advisory outputs generated from placeholder regulation values. "
    "They do NOT constitute legal compliance certification. "
    "Consult a licensed architect/engineer and verify against the current "
    "CMDA/DTCP regulations before submission."
)


class TNAdvisoryReport(BaseModel):
    project_id: str
    jurisdiction: str = "Tamil Nadu, India"
    passes_advisory: bool
    summary: str
    results: list[TNRuleResult]
    missing_inputs: list[str] = Field(default_factory=list)
    disclaimer: str = _TN_DISCLAIMER
