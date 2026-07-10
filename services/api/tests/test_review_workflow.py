"""Phase 41 — Collaboration / Review / QA workflow tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.exports.review_exporter import export_review_json, export_review_text
from app.core.review.models import QAChecklist, ReviewIssue
from app.core.review.qa_checklist import QAChecker
from app.core.review.store import ReviewStore
from app.core.storage.local_store import LocalProjectStore
import app.core.chat_tools as ct


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def store(tmp_path: Path) -> LocalProjectStore:
    return LocalProjectStore(tmp_path)


@pytest.fixture()
def pid(store: LocalProjectStore) -> str:
    entry = store.create_project("Review Test", prompt="2BHK")
    req = parse_prompt("2BHK east-facing 30x50ft")
    project, _ = generate_floorplan(req)
    store.update_project(entry.id, project=project, change_type="generate")
    return entry.id


@pytest.fixture()
def rs(tmp_path: Path) -> ReviewStore:
    return ReviewStore(user_id="local-user")


def _patch(store: LocalProjectStore):
    ct._store = lambda: store  # type: ignore[attr-defined]


def _make_project():
    req = parse_prompt("2BHK east-facing 30x50ft")
    project, _ = generate_floorplan(req)
    return project


# ── ReviewStore ───────────────────────────────────────────────────────────────


def test_store_create_issue(tmp_path):
    rs = ReviewStore(user_id="local-user")
    # Use a temp project id to avoid file collisions
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    issue = rs.create(pid, title="Missing toilet door swing")
    assert issue.id
    assert issue.title == "Missing toilet door swing"
    assert issue.status == "open"
    assert issue.priority == "medium"


def test_store_list_issues(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    rs.create(pid, title="Issue 1")
    rs.create(pid, title="Issue 2")
    issues = rs.list(pid)
    assert len(issues) == 2


def test_store_get_issue(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    created = rs.create(pid, title="Check kitchen layout")
    fetched = rs.get(pid, created.id)
    assert fetched.id == created.id
    assert fetched.title == "Check kitchen layout"


def test_store_get_issue_not_found(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    with pytest.raises(KeyError):
        rs.get(pid, "nonexistent")


def test_store_update_issue(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    issue = rs.create(pid, title="Verify setbacks")
    updated = rs.update(pid, issue.id, status="in_progress", priority="high")
    assert updated.status == "in_progress"
    assert updated.priority == "high"


def test_store_resolve_issue(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    issue = rs.create(pid, title="Check MEP")
    resolved = rs.resolve(pid, issue.id, resolution_note="MEP reviewed and approved.")
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None
    assert "approved" in resolved.resolution_note


def test_store_delete_issue(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    issue = rs.create(pid, title="Temp issue")
    rs.delete(pid, issue.id)
    issues = rs.list(pid)
    assert all(i.id != issue.id for i in issues)


def test_store_delete_not_found(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    with pytest.raises(KeyError):
        rs.delete(pid, "nonexistent")


def test_store_issue_category_default(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    issue = rs.create(pid, title="General issue")
    assert issue.category == "general"


def test_store_issue_all_categories(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    for cat in ("spatial", "mep", "compliance", "boq", "detail", "export", "general"):
        issue = rs.create(pid, title=f"{cat} issue", category=cat)
        assert issue.category == cat


def test_store_issue_object_ref(tmp_path):
    rs = ReviewStore(user_id="local-user")
    import uuid
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    issue = rs.create(pid, title="Room too small", object_ref="room-1")
    assert issue.object_ref == "room-1"


# ── QA Checklist ──────────────────────────────────────────────────────────────


def test_qa_checker_returns_checklist():
    proj = _make_project()
    checker = QAChecker()
    qa = checker.run(proj)
    assert isinstance(qa, QAChecklist)


def test_qa_checker_has_ten_items():
    proj = _make_project()
    checker = QAChecker()
    qa = checker.run(proj)
    assert len(qa.items) == 10


def test_qa_checker_room_count_passes():
    proj = _make_project()
    checker = QAChecker()
    qa = checker.run(proj)
    item = next(i for i in qa.items if i.id == "minimum_room_count")
    assert item.status == "pass"


def test_qa_checker_rooms_inside_site():
    proj = _make_project()
    checker = QAChecker()
    qa = checker.run(proj)
    item = next(i for i in qa.items if i.id == "rooms_inside_site")
    assert item.status in ("pass", "warning")


def test_qa_checker_no_validation_errors_pass():
    proj = _make_project()
    checker = QAChecker()
    qa = checker.run(proj)
    item = next(i for i in qa.items if i.id == "no_validation_errors")
    assert item.status == "pass"


def test_qa_checker_mep_warning_when_not_generated():
    proj = _make_project()
    # MEP not generated by default
    checker = QAChecker()
    qa = checker.run(proj)
    item = next(i for i in qa.items if i.id == "mep_generated")
    assert item.status == "warning"


def test_qa_checker_boq_warning_when_not_generated():
    proj = _make_project()
    checker = QAChecker()
    qa = checker.run(proj)
    item = next(i for i in qa.items if i.id == "boq_generated")
    assert item.status == "warning"


def test_qa_checker_details_warning_when_none():
    proj = _make_project()
    assert len(proj.detail_drawings) == 0
    checker = QAChecker()
    qa = checker.run(proj)
    item = next(i for i in qa.items if i.id == "details_present")
    assert item.status == "warning"


def test_qa_checker_exports_fresh_when_no_stale():
    proj = _make_project()
    # revision_meta.exports_stale defaults False
    checker = QAChecker()
    qa = checker.run(proj)
    item = next(i for i in qa.items if i.id == "exports_fresh")
    assert item.status == "pass"


def test_qa_checker_exports_stale_when_flagged():
    proj = _make_project()
    meta = proj.revision_meta.model_copy(update={"exports_stale": True, "stale_reason": "room added"})
    proj = proj.model_copy(update={"revision_meta": meta})
    checker = QAChecker()
    qa = checker.run(proj)
    item = next(i for i in qa.items if i.id == "exports_fresh")
    assert item.status == "warning"
    assert "stale" in item.detail.lower()


def test_qa_completion_pct_range():
    proj = _make_project()
    checker = QAChecker()
    qa = checker.run(proj)
    assert 0.0 <= qa.completion_pct <= 100.0


def test_qa_counts_add_up():
    proj = _make_project()
    checker = QAChecker()
    qa = checker.run(proj)
    assert qa.passed + qa.failed + qa.warnings + qa.not_checked == len(qa.items)


# ── Review exporter ───────────────────────────────────────────────────────────


def _make_issues_and_qa():
    import uuid
    rs = ReviewStore(user_id="local-user")
    pid = f"proj-{uuid.uuid4().hex[:6]}"
    rs.create(pid, title="Check kitchen")
    rs.create(pid, title="Verify setbacks", category="compliance")
    issues = rs.list(pid)
    proj = _make_project()
    qa = QAChecker().run(proj)
    return pid, issues, qa


def test_export_review_json_is_valid():
    import json
    pid, issues, qa = _make_issues_and_qa()
    data = export_review_json(pid, issues, qa)
    parsed = json.loads(data)
    assert parsed["project_id"] == pid
    assert "qa_summary" in parsed
    assert "issues" in parsed


def test_export_review_json_issue_count():
    import json
    pid, issues, qa = _make_issues_and_qa()
    data = export_review_json(pid, issues, qa)
    parsed = json.loads(data)
    assert parsed["issue_summary"]["total"] == 2


def test_export_review_text_is_bytes():
    pid, issues, qa = _make_issues_and_qa()
    data = export_review_text(pid, issues, qa)
    assert isinstance(data, bytes)
    text = data.decode("utf-8")
    assert "SCOTCH REVIEW REPORT" in text


def test_export_review_text_includes_qa_score():
    pid, issues, qa = _make_issues_and_qa()
    data = export_review_text(pid, issues, qa)
    text = data.decode("utf-8")
    assert "QA CHECKLIST" in text
    assert "passed" in text.lower()


# ── Chat tools ────────────────────────────────────────────────────────────────


def test_run_qa_checklist_tool(store, pid):
    _patch(store)
    result = ct.run_qa_checklist(pid)
    assert "passed" in result
    assert "items" in result
    assert len(result["items"]) == 10


def test_add_review_issue_tool(store, pid):
    from app.core.review.store import _instance
    import app.core.review.store as rs_mod
    # Reset singleton for isolation
    rs_mod._instance = None
    _patch(store)
    result = ct.add_review_issue(pid, title="Check door swing in bedroom")
    assert result["id"]
    assert result["title"] == "Check door swing in bedroom"
    rs_mod._instance = None


def test_list_review_issues_tool(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    _patch(store)
    ct.add_review_issue(pid, title="Issue A")
    ct.add_review_issue(pid, title="Issue B")
    result = ct.list_review_issues(pid)
    assert result["total"] == 2
    assert result["open"] == 2
    rs_mod._instance = None


# ── API routes ────────────────────────────────────────────────────────────────


def _client(store):
    import importlib
    import os
    import app.api.dependencies.auth as auth_mod

    # test_cloud_store.py reloads auth with SCOTCH_AUTH_MODE=cloud and doesn't restore it;
    # force local mode for these tests.
    old_mode = os.environ.get("SCOTCH_AUTH_MODE")
    os.environ["SCOTCH_AUTH_MODE"] = "local"
    importlib.reload(auth_mod)
    if old_mode is None:
        os.environ.pop("SCOTCH_AUTH_MODE", None)
    else:
        os.environ["SCOTCH_AUTH_MODE"] = old_mode

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.storage.factory import get_project_store
    import app.core.review.store as rs_mod

    rs_mod._instance = None
    app.dependency_overrides[get_project_store] = lambda: store
    tc = TestClient(app)
    return tc, app


def test_api_list_issues_empty(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    resp = client.get(f"/projects/{pid}/review/issues")
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


def test_api_create_issue(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    resp = client.post(
        f"/projects/{pid}/review/issues",
        json={"title": "Verify wall thickness", "category": "spatial"},
    )
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Verify wall thickness"
    assert data["category"] == "spatial"


def test_api_get_issue(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    create_resp = client.post(f"/projects/{pid}/review/issues", json={"title": "BOQ check"})
    issue_id = create_resp.json()["id"]
    get_resp = client.get(f"/projects/{pid}/review/issues/{issue_id}")
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == issue_id


def test_api_update_issue(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    create_resp = client.post(f"/projects/{pid}/review/issues", json={"title": "MEP check"})
    issue_id = create_resp.json()["id"]
    patch_resp = client.patch(f"/projects/{pid}/review/issues/{issue_id}", json={"status": "resolved", "resolution_note": "Done"})
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "resolved"


def test_api_delete_issue(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    create_resp = client.post(f"/projects/{pid}/review/issues", json={"title": "Temp"})
    issue_id = create_resp.json()["id"]
    del_resp = client.delete(f"/projects/{pid}/review/issues/{issue_id}")
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert del_resp.status_code == 200


def test_api_qa_checklist(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    resp = client.get(f"/projects/{pid}/review/qa")
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 10


def test_api_export_review_json(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    resp = client.get(f"/projects/{pid}/review/export?fmt=json")
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert resp.status_code == 200
    import json
    data = json.loads(resp.content)
    assert "qa_summary" in data


def test_api_export_review_text(store, pid):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    resp = client.get(f"/projects/{pid}/review/export?fmt=text")
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert resp.status_code == 200
    assert b"SCOTCH REVIEW REPORT" in resp.content


def test_api_404_unknown_project(store):
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    client, app = _client(store)
    resp = client.get("/projects/nonexistent/review/issues")
    app.dependency_overrides.clear()
    rs_mod._instance = None
    assert resp.status_code == 404


# ── Chat routing ──────────────────────────────────────────────────────────────


def _chat(store: LocalProjectStore, pid: str, message: str):
    from app.api.routes.chat import _run_deterministic_fallback, ChatRequest
    import app.core.review.store as rs_mod
    rs_mod._instance = None
    _patch(store)
    result = _run_deterministic_fallback(pid, ChatRequest(message=message, history=[]))
    rs_mod._instance = None
    return result


def test_qa_checklist_keyword_routes(store, pid):
    resp = _chat(store, pid, "run QA checklist")
    assert "run_qa_checklist" in resp.tool_calls


def test_qa_production_ready_keyword(store, pid):
    resp = _chat(store, pid, "is this ready to submit?")
    assert "run_qa_checklist" in resp.tool_calls


def test_add_review_issue_keyword(store, pid):
    resp = _chat(store, pid, "add review issue: check door swings in all bathrooms")
    assert "add_review_issue" in resp.tool_calls


def test_list_review_issues_keyword(store, pid):
    resp = _chat(store, pid, "list review issues")
    assert "list_review_issues" in resp.tool_calls


def test_qa_reply_has_content(store, pid):
    resp = _chat(store, pid, "run QA checklist")
    assert "qa" in resp.reply.lower() or "check" in resp.reply.lower()
