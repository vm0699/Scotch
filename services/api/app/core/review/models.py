"""Phase 41 — Review / QA models (sidecar, not inline in ArchitectureProject)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ReviewCategory = Literal["spatial", "mep", "compliance", "boq", "detail", "export", "general"]
ReviewStatus = Literal["open", "in_progress", "resolved"]
ReviewPriority = Literal["low", "medium", "high"]
QAStatus = Literal["pass", "fail", "warning", "not_checked"]


class ReviewIssue(BaseModel):
    id: str
    object_ref: str | None = None  # room_id / mep_point_id / detail_id / etc.
    category: ReviewCategory = "general"
    title: str
    description: str = ""
    status: ReviewStatus = "open"
    priority: ReviewPriority = "medium"
    assigned_to: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None
    resolution_note: str | None = None
    created_by: str = "local-user"


class QACheckItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    status: QAStatus = "not_checked"
    detail: str = ""


class QAChecklist(BaseModel):
    project_id: str
    items: list[QACheckItem] = []
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    not_checked: int = 0
    completion_pct: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    advisory: str = "QA checklist is advisory — always verify with a licensed architect before construction."
