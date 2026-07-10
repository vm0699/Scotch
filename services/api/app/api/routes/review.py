"""Phase 41 — Collaboration / Review / QA API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user_id
from app.core.exports.review_exporter import export_review_json, export_review_text
from app.core.review.models import QAChecklist, ReviewIssue
from app.core.review.qa_checklist import QAChecker
from app.core.review.store import ReviewStore
from app.core.review.store import get_review_store as _get_review_store


def get_review_store() -> ReviewStore:
    return _get_review_store()
from app.core.storage.factory import get_project_store
from app.core.storage import ProjectNotFoundError, ProjectStore

router = APIRouter(prefix="/projects", tags=["review"])


def _load_project(project_id: str, store: ProjectStore):
    try:
        stored = store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.project is None:
        raise HTTPException(status_code=422, detail="Project has no design — generate first.")
    return stored.project


# ── Issue CRUD ────────────────────────────────────────────────────────────────


class IssueCreate(BaseModel):
    title: str
    category: str = "general"
    description: str = ""
    object_ref: str | None = None
    priority: str = "medium"


class IssueUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    resolution_note: str | None = None


class IssueListResponse(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    issues: list[ReviewIssue]


@router.get("/{project_id}/review/issues", response_model=IssueListResponse)
def list_issues(
    project_id: str,
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    store: ProjectStore = Depends(get_project_store),
    rs: ReviewStore = Depends(get_review_store),
    _user: str = Depends(get_current_user_id),
) -> IssueListResponse:
    # Validate project exists
    try:
        store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    issues = rs.list(project_id)
    if category:
        issues = [i for i in issues if i.category == category]
    if status:
        issues = [i for i in issues if i.status == status]
    return IssueListResponse(
        total=len(issues),
        open=sum(1 for i in issues if i.status == "open"),
        in_progress=sum(1 for i in issues if i.status == "in_progress"),
        resolved=sum(1 for i in issues if i.status == "resolved"),
        issues=issues,
    )


@router.post("/{project_id}/review/issues", response_model=ReviewIssue, status_code=201)
def create_issue(
    project_id: str,
    body: IssueCreate,
    store: ProjectStore = Depends(get_project_store),
    rs: ReviewStore = Depends(get_review_store),
    user_id: str = Depends(get_current_user_id),
) -> ReviewIssue:
    try:
        store.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return rs.create(
        project_id,
        title=body.title,
        category=body.category,
        description=body.description,
        object_ref=body.object_ref,
        priority=body.priority,
        created_by=user_id,
    )


@router.get("/{project_id}/review/issues/{issue_id}", response_model=ReviewIssue)
def get_issue(
    project_id: str,
    issue_id: str,
    rs: ReviewStore = Depends(get_review_store),
    _user: str = Depends(get_current_user_id),
) -> ReviewIssue:
    try:
        return rs.get(project_id, issue_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}/review/issues/{issue_id}", response_model=ReviewIssue)
def update_issue(
    project_id: str,
    issue_id: str,
    body: IssueUpdate,
    rs: ReviewStore = Depends(get_review_store),
    _user: str = Depends(get_current_user_id),
) -> ReviewIssue:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        return rs.update(project_id, issue_id, **updates)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{project_id}/review/issues/{issue_id}")
def delete_issue(
    project_id: str,
    issue_id: str,
    rs: ReviewStore = Depends(get_review_store),
    _user: str = Depends(get_current_user_id),
) -> dict:
    try:
        rs.delete(project_id, issue_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": issue_id}


# ── QA Checklist ──────────────────────────────────────────────────────────────


@router.get("/{project_id}/review/qa", response_model=QAChecklist)
def run_qa(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    _user: str = Depends(get_current_user_id),
) -> QAChecklist:
    """Run the automated QA checklist against the project.

    Checks spatial validity, MEP, details, BOQ completeness, and export freshness.
    Advisory only.
    """
    project = _load_project(project_id, store)
    checker = QAChecker()
    return checker.run(project)


# ── Review export ─────────────────────────────────────────────────────────────


@router.get("/{project_id}/review/export")
def export_review(
    project_id: str,
    fmt: str = Query(default="json", pattern="^(json|text)$"),
    store: ProjectStore = Depends(get_project_store),
    rs: ReviewStore = Depends(get_review_store),
    _user: str = Depends(get_current_user_id),
) -> Response:
    """Export a review report as JSON or plain text."""
    project = _load_project(project_id, store)
    issues = rs.list(project_id)
    checker = QAChecker()
    qa = checker.run(project)

    if fmt == "text":
        content = export_review_text(project_id, issues, qa)
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="review_{project_id}.txt"'},
        )
    content = export_review_json(project_id, issues, qa)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="review_{project_id}.json"'},
    )
