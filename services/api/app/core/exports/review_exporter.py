"""Phase 41 — Review / QA export: JSON summary + plain-text report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.review.models import QAChecklist, ReviewIssue


def export_review_json(
    project_id: str,
    issues: "list[ReviewIssue]",
    qa: "QAChecklist",
) -> bytes:
    payload = {
        "project_id": project_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "qa_summary": {
            "passed": qa.passed,
            "failed": qa.failed,
            "warnings": qa.warnings,
            "completion_pct": qa.completion_pct,
            "advisory": qa.advisory,
            "items": [item.model_dump() for item in qa.items],
        },
        "issues": [issue.model_dump() for issue in issues],
        "issue_summary": {
            "total": len(issues),
            "open": sum(1 for i in issues if i.status == "open"),
            "in_progress": sum(1 for i in issues if i.status == "in_progress"),
            "resolved": sum(1 for i in issues if i.status == "resolved"),
        },
    }
    return json.dumps(payload, default=str, ensure_ascii=False, indent=2).encode()


def export_review_text(
    project_id: str,
    issues: "list[ReviewIssue]",
    qa: "QAChecklist",
) -> bytes:
    lines: list[str] = [
        "=" * 60,
        f"SCOTCH REVIEW REPORT — Project {project_id}",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "QA CHECKLIST",
        "-" * 40,
        f"Score: {qa.passed}/{len(qa.items)} passed ({qa.completion_pct:.0f}% complete)",
        "",
    ]

    _ICON = {"pass": "✓", "fail": "✗", "warning": "⚠", "not_checked": "–"}
    for item in qa.items:
        icon = _ICON.get(item.status, "–")
        lines.append(f"  {icon} [{item.status.upper():^11}] {item.title}")
        if item.detail:
            lines.append(f"             {item.detail}")
    lines += [
        "",
        f"Advisory: {qa.advisory}",
        "",
        "=" * 60,
        f"REVIEW ISSUES ({len(issues)} total)",
        "-" * 40,
    ]

    if not issues:
        lines.append("  No issues recorded.")
    else:
        by_status: dict[str, list] = {"open": [], "in_progress": [], "resolved": []}
        for issue in issues:
            by_status.get(issue.status, []).append(issue)

        for status_label, status_issues in [
            ("OPEN", by_status["open"]),
            ("IN PROGRESS", by_status["in_progress"]),
            ("RESOLVED", by_status["resolved"]),
        ]:
            if status_issues:
                lines += ["", f"  {status_label} ({len(status_issues)})"]
                for issue in status_issues:
                    ref = f" [{issue.object_ref}]" if issue.object_ref else ""
                    lines.append(f"  • [{issue.priority.upper()}] {issue.title}{ref}")
                    if issue.description:
                        lines.append(f"    {issue.description[:120]}")
                    if issue.resolution_note:
                        lines.append(f"    Resolution: {issue.resolution_note}")

    lines += [
        "",
        "=" * 60,
        "This report is advisory. Verify all items with a licensed",
        "architect and CMDA/DTCP-registered engineer before construction.",
        "=" * 60,
    ]
    return "\n".join(lines).encode("utf-8")
