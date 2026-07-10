"""Phase 34 — RevisionMeta and revision utility tests."""
import pytest
from datetime import datetime, timezone

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.changes.revisions import (
    bump_revision,
    format_revision_label,
    mark_exports_fresh,
    mark_exports_stale,
)
from app.core.models.project import RevisionMeta

PROMPT = "2BHK on 30x40 ft east-facing site"


def _project():
    proj, _ = generate_floorplan(parse_prompt(PROMPT))
    return proj


def _fresh_meta() -> RevisionMeta:
    return RevisionMeta()


# ── RevisionMeta default values ───────────────────────────────────────────────

def test_project_has_revision_meta():
    proj = _project()
    assert hasattr(proj, "revision_meta")
    assert isinstance(proj.revision_meta, RevisionMeta)


def test_default_revision_number_is_zero():
    meta = _fresh_meta()
    assert meta.revision_number == 0


def test_default_exports_stale_is_false():
    meta = _fresh_meta()
    assert meta.exports_stale is False


def test_default_stale_reason_empty():
    meta = _fresh_meta()
    assert meta.stale_reason == ""


# ── bump_revision ─────────────────────────────────────────────────────────────

def test_bump_increments_revision_number():
    meta = _fresh_meta()
    bumped = bump_revision(meta, note="Client change applied")
    assert bumped.revision_number == 1


def test_bump_twice_reaches_two():
    meta = _fresh_meta()
    meta = bump_revision(meta, note="First client change")
    meta = bump_revision(meta, note="Second client change")
    assert meta.revision_number == 2


def test_bump_sets_exports_stale():
    meta = _fresh_meta()
    bumped = bump_revision(meta)
    assert bumped.exports_stale is True


def test_bump_records_stale_reason():
    meta = _fresh_meta()
    bumped = bump_revision(meta)
    assert "revision" in bumped.stale_reason.lower() or "change" in bumped.stale_reason.lower()


def test_bump_records_note():
    meta = _fresh_meta()
    bumped = bump_revision(meta, note="Added attached toilet")
    assert bumped.note == "Added attached toilet"


def test_bump_records_affected_sheets():
    meta = _fresh_meta()
    bumped = bump_revision(meta, affected_sheets=["Sheet A1", "Sheet M1"])
    assert "Sheet A1" in bumped.affected_sheets
    assert "Sheet M1" in bumped.affected_sheets


def test_bump_updates_date():
    meta = RevisionMeta(date=datetime(2020, 1, 1, tzinfo=timezone.utc))
    bumped = bump_revision(meta)
    assert bumped.date.year >= 2026


def test_bump_is_immutable_original_unchanged():
    meta = _fresh_meta()
    _ = bump_revision(meta)
    assert meta.revision_number == 0


# ── mark_exports_stale ────────────────────────────────────────────────────────

def test_mark_exports_stale_sets_flag():
    meta = _fresh_meta()
    stale = mark_exports_stale(meta, reason="Room resize")
    assert stale.exports_stale is True


def test_mark_exports_stale_records_reason():
    meta = _fresh_meta()
    stale = mark_exports_stale(meta, reason="Room resize after client change")
    assert stale.stale_reason == "Room resize after client change"


def test_mark_exports_stale_preserves_revision_number():
    meta = RevisionMeta(revision_number=3)
    stale = mark_exports_stale(meta)
    assert stale.revision_number == 3


# ── mark_exports_fresh ────────────────────────────────────────────────────────

def test_mark_exports_fresh_clears_flag():
    meta = mark_exports_stale(_fresh_meta())
    fresh = mark_exports_fresh(meta)
    assert fresh.exports_stale is False


def test_mark_exports_fresh_clears_reason():
    meta = mark_exports_stale(_fresh_meta(), reason="Something changed")
    fresh = mark_exports_fresh(meta)
    assert fresh.stale_reason == ""


def test_mark_exports_fresh_preserves_revision():
    meta = RevisionMeta(revision_number=5, exports_stale=True)
    fresh = mark_exports_fresh(meta)
    assert fresh.revision_number == 5


# ── format_revision_label ─────────────────────────────────────────────────────

def test_format_label_initial():
    meta = _fresh_meta()
    assert format_revision_label(meta) == "Initial design"


def test_format_label_rev1():
    meta = bump_revision(_fresh_meta(), note="First change")
    label = format_revision_label(meta)
    assert label.startswith("Rev 1")
    assert "2026" in label


def test_format_label_rev3():
    meta = _fresh_meta()
    for _ in range(3):
        meta = bump_revision(meta)
    label = format_revision_label(meta)
    assert label.startswith("Rev 3")


# ── Round-trip through project JSON ──────────────────────────────────────────

def test_revision_meta_survives_json_roundtrip():
    proj = _project()
    meta = bump_revision(proj.revision_meta, note="Client: add toilet")
    proj2 = proj.model_copy(update={"revision_meta": meta})
    dumped = proj2.model_dump_json()
    from app.core.models import ArchitectureProject
    restored = ArchitectureProject.model_validate_json(dumped)
    assert restored.revision_meta.revision_number == 1
    assert restored.revision_meta.note == "Client: add toilet"
    assert restored.revision_meta.exports_stale is True
