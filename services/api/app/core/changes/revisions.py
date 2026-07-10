"""Phase 34.6 — Revision metadata utilities.

Manages revision_number incrementing and exports_stale tracking on
ArchitectureProject.revision_meta.

exports_stale is set True any time the design changes after exports have been
generated; it is cleared when the user triggers a fresh export run.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.models.project import RevisionMeta


def bump_revision(meta: RevisionMeta, note: str = "", affected_sheets: list[str] | None = None) -> RevisionMeta:
    """Increment revision number and record the change date."""
    return RevisionMeta(
        revision_number=meta.revision_number + 1,
        note=note or meta.note,
        date=datetime.now(timezone.utc),
        affected_sheets=affected_sheets or meta.affected_sheets,
        exports_stale=True,
        stale_reason=f"Client change applied (revision {meta.revision_number + 1})",
    )


def mark_exports_stale(meta: RevisionMeta, reason: str = "Design changed after export") -> RevisionMeta:
    """Mark exports as stale without bumping revision number."""
    return RevisionMeta(
        revision_number=meta.revision_number,
        note=meta.note,
        date=meta.date,
        affected_sheets=meta.affected_sheets,
        exports_stale=True,
        stale_reason=reason,
    )


def mark_exports_fresh(meta: RevisionMeta) -> RevisionMeta:
    """Clear stale flag after exports have been re-generated."""
    return RevisionMeta(
        revision_number=meta.revision_number,
        note=meta.note,
        date=datetime.now(timezone.utc),
        affected_sheets=meta.affected_sheets,
        exports_stale=False,
        stale_reason="",
    )


def format_revision_label(meta: RevisionMeta) -> str:
    """Return display string like 'Rev 3 — 2026-06-22'."""
    if meta.revision_number == 0:
        return "Initial design"
    date_str = meta.date.strftime("%Y-%m-%d")
    return f"Rev {meta.revision_number} — {date_str}"
