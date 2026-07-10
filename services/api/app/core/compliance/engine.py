"""Compliance engine — Phase 27.1.

run_compliance(project, *, front, side, rear, max_fsi) → ComplianceReport
"""

from __future__ import annotations

from app.core.compliance.models import ComplianceReport, RuleResult
from app.core.compliance.rules import (
    DEFAULT_FRONT_SETBACK,
    DEFAULT_MAX_FSI,
    DEFAULT_REAR_SETBACK,
    DEFAULT_SIDE_SETBACK,
    check_fsi,
    check_parking,
    check_room_areas,
    check_setbacks,
    check_stair_width,
    check_ventilation,
)
from app.core.models.project import ArchitectureProject


def run_compliance(
    project: ArchitectureProject,
    project_id: str,
    *,
    front_setback: float = DEFAULT_FRONT_SETBACK,
    side_setback:  float = DEFAULT_SIDE_SETBACK,
    rear_setback:  float = DEFAULT_REAR_SETBACK,
    max_fsi:       float = DEFAULT_MAX_FSI,
    zone: str = "urban_residential",
) -> ComplianceReport:
    rules: list[RuleResult] = []

    rules.append(check_fsi(project, max_fsi))
    rules.extend(check_setbacks(project, front_setback, side_setback, rear_setback))
    rules.extend(check_room_areas(project))
    rules.extend(check_ventilation(project))
    rules.extend(check_stair_width(project))
    rules.extend(check_parking(project))

    fails = [r for r in rules if r.status == "fail"]
    warns = [r for r in rules if r.status == "warn"]
    passes_review = len(fails) == 0

    if passes_review:
        if warns:
            summary = (
                f"Design passes NBC review with {len(warns)} advisory warning"
                f"{'s' if len(warns) != 1 else ''} (no hard failures)."
            )
        else:
            summary = "Design passes all NBC compliance checks — no violations found."
    else:
        summary = (
            f"{len(fails)} NBC compliance violation{'s' if len(fails) != 1 else ''} found. "
            f"Review the flagged items before submission."
        )

    return ComplianceReport(
        project_id=project_id,
        zone=zone,
        passes_review=passes_review,
        summary=summary,
        rules=rules,
        front_setback_ft=front_setback,
        side_setback_ft=side_setback,
        rear_setback_ft=rear_setback,
        max_fsi=max_fsi,
    )
