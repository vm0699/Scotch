"""Phase 41 — File-based sidecar store for review issues.

Layout: data/users/{user_id}/projects/{project_id}/reviews/issues.json
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.review.models import ReviewIssue
from app.core.storage.base import LOCAL_USER_ID

_DATA_ROOT = Path(__file__).parent.parent.parent / "data"


def _reviews_dir(user_id: str, project_id: str) -> Path:
    d = _DATA_ROOT / "users" / user_id / "projects" / project_id / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _issues_path(user_id: str, project_id: str) -> Path:
    return _reviews_dir(user_id, project_id) / "issues.json"


def _load_all(user_id: str, project_id: str) -> list[ReviewIssue]:
    p = _issues_path(user_id, project_id)
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [ReviewIssue.model_validate(item) for item in raw]


def _save_all(user_id: str, project_id: str, issues: list[ReviewIssue]) -> None:
    p = _issues_path(user_id, project_id)
    p.write_text(
        json.dumps([i.model_dump() for i in issues], default=str, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class ReviewStore:
    def __init__(self, user_id: str = LOCAL_USER_ID):
        self._user_id = user_id

    def list(self, project_id: str) -> list[ReviewIssue]:
        return _load_all(self._user_id, project_id)

    def get(self, project_id: str, issue_id: str) -> ReviewIssue:
        issues = _load_all(self._user_id, project_id)
        for issue in issues:
            if issue.id == issue_id:
                return issue
        raise KeyError(f"Issue '{issue_id}' not found in project '{project_id}'.")

    def create(
        self,
        project_id: str,
        title: str,
        category: str = "general",
        description: str = "",
        object_ref: str | None = None,
        priority: str = "medium",
        created_by: str = "local-user",
    ) -> ReviewIssue:
        issues = _load_all(self._user_id, project_id)
        issue = ReviewIssue(
            id=str(uuid.uuid4())[:8],
            title=title,
            category=category,  # type: ignore[arg-type]
            description=description,
            object_ref=object_ref,
            priority=priority,  # type: ignore[arg-type]
            created_by=created_by,
        )
        issues.append(issue)
        _save_all(self._user_id, project_id, issues)
        return issue

    def update(self, project_id: str, issue_id: str, **kwargs) -> ReviewIssue:
        issues = _load_all(self._user_id, project_id)
        updated = []
        found = None
        for issue in issues:
            if issue.id == issue_id:
                issue = issue.model_copy(update=kwargs)
                found = issue
            updated.append(issue)
        if found is None:
            raise KeyError(f"Issue '{issue_id}' not found.")
        _save_all(self._user_id, project_id, updated)
        return found

    def resolve(self, project_id: str, issue_id: str, resolution_note: str = "") -> ReviewIssue:
        return self.update(
            project_id,
            issue_id,
            status="resolved",
            resolved_at=datetime.now(timezone.utc).isoformat(),
            resolution_note=resolution_note,
        )

    def delete(self, project_id: str, issue_id: str) -> None:
        issues = _load_all(self._user_id, project_id)
        remaining = [i for i in issues if i.id != issue_id]
        if len(remaining) == len(issues):
            raise KeyError(f"Issue '{issue_id}' not found.")
        _save_all(self._user_id, project_id, remaining)


_instance: ReviewStore | None = None


def get_review_store() -> ReviewStore:
    global _instance
    if _instance is None:
        _instance = ReviewStore()
    return _instance
