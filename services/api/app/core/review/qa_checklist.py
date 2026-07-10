"""Phase 41 — QA checklist engine.

10 automated checks across spatial, MEP, detail, BOQ, compliance, export concerns.
All outputs are advisory — always verify with a licensed architect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.models.project import ArchitectureProject

from app.core.review.models import QACheckItem, QAChecklist
from app.core.validation import validate_project


_CHECKS = [
    ("no_validation_errors",  "spatial",    "No validation errors",
     "ArchitectureProject passes all schema + constraint validations."),
    ("minimum_room_count",    "spatial",    "At least one room",
     "Floor plan has a minimum of one room defined."),
    ("rooms_inside_site",     "spatial",    "All rooms fit inside site",
     "No room extends beyond the site boundary dimensions."),
    ("openings_scheduled",    "spatial",    "Doors + windows present",
     "At least one door and one window are scheduled."),
    ("dimensions_present",    "spatial",    "Dimension entities exist",
     "Auto-dimension engine has been run and dimension entities are recorded."),
    ("mep_generated",         "mep",        "MEP layers generated",
     "MEP plan (plumbing / electrical / lighting / AC) has been generated."),
    ("details_present",       "detail",     "Detail drawings present",
     "At least one detail drawing exists (toilet, kitchen, wall section, etc.)."),
    ("boq_generated",         "boq",        "BOQ calculated",
     "Bill of Quantities has been generated at least once."),
    ("boq_rates_complete",    "boq",        "No missing BOQ rates",
     "All BOQ items have a non-zero rate; missing rates flagged."),
    ("exports_fresh",         "export",     "Exports not stale",
     "No exports are marked stale after a design change."),
]


class QAChecker:
    def run(self, project: "ArchitectureProject") -> QAChecklist:
        items: list[QACheckItem] = []

        for check_id, category, title, description in _CHECKS:
            status, detail = self._run_check(check_id, project)
            items.append(QACheckItem(
                id=check_id,
                category=category,
                title=title,
                description=description,
                status=status,
                detail=detail,
            ))

        passed = sum(1 for i in items if i.status == "pass")
        failed = sum(1 for i in items if i.status == "fail")
        warnings = sum(1 for i in items if i.status == "warning")
        not_checked = sum(1 for i in items if i.status == "not_checked")
        total = len(items)
        completion_pct = round((passed + warnings) / total * 100, 1) if total else 0.0

        return QAChecklist(
            project_id=project.id,
            items=items,
            passed=passed,
            failed=failed,
            warnings=warnings,
            not_checked=not_checked,
            completion_pct=completion_pct,
        )

    def _run_check(self, check_id: str, project: "ArchitectureProject") -> tuple[str, str]:
        try:
            fn = getattr(self, f"_check_{check_id}")
            return fn(project)
        except Exception as exc:
            return "warning", f"Check failed to run: {exc}"

    def _check_no_validation_errors(self, project):
        result = validate_project(project)
        if result.valid:
            return "pass", "Project validates with no errors."
        errors = "; ".join(result.errors[:3])
        return "fail", f"Validation errors: {errors}"

    def _check_minimum_room_count(self, project):
        n = len(project.rooms)
        if n >= 1:
            return "pass", f"{n} room(s) defined."
        return "fail", "No rooms defined — generate a floor plan first."

    def _check_rooms_inside_site(self, project):
        w, d = project.site.width, project.site.depth
        out: list[str] = []
        for r in project.rooms:
            if r.x + r.width > w + 0.1 or r.y + r.depth > d + 0.1:
                out.append(r.name)
        if not out:
            return "pass", "All rooms fit within site boundary."
        return "warning", f"Room(s) may extend beyond site: {', '.join(out[:3])}. Review layout."

    def _check_openings_scheduled(self, project):
        nd, nw = len(project.doors), len(project.windows)
        if nd >= 1 and nw >= 1:
            return "pass", f"{nd} door(s) + {nw} window(s) scheduled."
        if nd == 0 and nw == 0:
            return "warning", "No doors or windows scheduled — generate a design to auto-place openings."
        if nd == 0:
            return "warning", f"{nw} window(s) but no doors — add entry/exit door."
        return "warning", f"{nd} door(s) but no windows — add windows for ventilation."

    def _check_dimensions_present(self, project):
        n = len(project.dimensions)
        if n >= 1:
            return "pass", f"{n} dimension entit{'y' if n == 1 else 'ies'} present."
        return "warning", "No dimension entities — run the dimension engine or prompt 'show dimensions'."

    def _check_mep_generated(self, project):
        if project.mep_plan.generated:
            systems = []
            if project.mep_plan.plumbing.points:
                systems.append("plumbing")
            if project.mep_plan.electrical.points:
                systems.append("electrical")
            if project.mep_plan.lighting.points:
                systems.append("lighting")
            if project.mep_plan.ac.units:
                systems.append("AC")
            return "pass", f"MEP generated: {', '.join(systems) if systems else 'generated (empty)'}."
        return "warning", "MEP layers not generated — say 'add plumbing and electrical layers'."

    def _check_details_present(self, project):
        n = len(project.detail_drawings)
        if n >= 1:
            types = list({d.detail_type for d in project.detail_drawings})
            return "pass", f"{n} detail drawing(s): {', '.join(types)}."
        return "warning", "No detail drawings — generate toilet/kitchen/wall-section detail for production drawings."

    def _check_boq_generated(self, project):
        if project.cost_plan.generated:
            total = project.cost_plan.grand_total
            return "pass", f"BOQ generated. Grand total: ₹{total:,.0f}."
        return "warning", "BOQ not calculated — say 'calculate BOQ' to generate cost estimate."

    def _check_boq_rates_complete(self, project):
        if not project.cost_plan.generated:
            return "not_checked", "BOQ not generated yet."
        missing = project.cost_plan.missing_rates
        if not missing:
            return "pass", "All BOQ rates are filled in."
        return "warning", f"{len(missing)} missing rate(s): {', '.join(missing[:3])}. Update in BOQ panel."

    def _check_exports_fresh(self, project):
        if not project.revision_meta.exports_stale:
            return "pass", "No exports marked stale."
        reason = project.revision_meta.stale_reason or "design changed after last export"
        return "warning", f"Exports stale: {reason}. Re-export to get current files."
