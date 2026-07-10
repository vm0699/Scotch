"""Phase 34 — Client Change Management models.

ClientChangeRequest tracks a client revision request through its lifecycle:
  pending → approved/rejected → applied/reverted.

AffectedItems is the computed impact report for a change request, enumerating
exactly which rooms, MEP points, BOQ lines, compliance rules, detail drawings,
export files, and plugin syncs are touched.

RevisionMeta lives in app.core.models.project to avoid circular imports.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ChangeStatus = Literal["pending", "approved", "applied", "rejected", "reverted"]
ChangeSource = Literal["chat", "manual", "client", "architect"]
ChangePriority = Literal["low", "medium", "high", "urgent"]
AffectedSeverity = Literal["info", "warning", "action_needed"]


class AffectedItem(BaseModel):
    module: str
    object_id: str | None = None
    description: str
    severity: AffectedSeverity = "info"
    action: str = ""


class AffectedItems(BaseModel):
    change_id: str
    rooms: list[AffectedItem] = []
    mep: list[AffectedItem] = []
    boq: list[AffectedItem] = []
    compliance: list[AffectedItem] = []
    details: list[AffectedItem] = []
    exports: list[AffectedItem] = []
    plugins: list[AffectedItem] = []
    total_count: int = 0
    summary: str = ""
    cost_impact: str = ""


class ClientChangeRequest(BaseModel):
    id: str
    request_text: str
    source: ChangeSource = "client"
    status: ChangeStatus = "pending"
    priority: ChangePriority = "medium"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    affected_modules: list[str] = Field(default_factory=list)
    before_version: str | None = None
    after_version: str | None = None
    summary: str = ""
    cost_impact: str = ""
    drawing_impact: list[str] = Field(default_factory=list)
    mep_impact: list[str] = Field(default_factory=list)
    detail_impact: list[str] = Field(default_factory=list)
    export_impact: list[str] = Field(default_factory=list)
    affected_items: AffectedItems | None = None
