"""Phase 39 — Reference asset model and store tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.references.models import ExtractedEntity, ReferenceAsset, ScaleCalibration
from app.core.references.store import ReferenceStore


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def store(tmp_path: Path) -> ReferenceStore:
    return ReferenceStore(tmp_path)


_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
_USER = "local-user"
_PID = "proj-test"


# ── ScaleCalibration model ────────────────────────────────────────────────────

def test_scale_calibration_derives_pixels_per_foot():
    cal = ScaleCalibration(p1_x=0, p1_y=0, p2_x=100, p2_y=0, known_distance_ft=10.0)
    assert cal.pixels_per_foot == pytest.approx(10.0)


def test_scale_calibration_diagonal():
    import math
    cal = ScaleCalibration(p1_x=0, p1_y=0, p2_x=30, p2_y=40, known_distance_ft=5.0)
    expected = math.sqrt(30 ** 2 + 40 ** 2) / 5.0
    assert cal.pixels_per_foot == pytest.approx(expected)


def test_scale_calibration_rejects_zero_distance():
    with pytest.raises(ValueError):
        ScaleCalibration(p1_x=0, p1_y=0, p2_x=0, p2_y=0, known_distance_ft=10.0)


def test_scale_calibration_rejects_negative_known_distance():
    with pytest.raises(Exception):
        ScaleCalibration(p1_x=0, p1_y=0, p2_x=100, p2_y=0, known_distance_ft=-1.0)


def test_scale_calibration_explicit_pixels_per_foot_not_overwritten():
    cal = ScaleCalibration(
        p1_x=0, p1_y=0, p2_x=100, p2_y=0,
        known_distance_ft=10.0, pixels_per_foot=5.0,
    )
    # If provided explicitly, validator overwrites to the derived value
    assert cal.pixels_per_foot == pytest.approx(10.0)


def test_scale_calibration_origin_defaults():
    cal = ScaleCalibration(p1_x=0, p1_y=0, p2_x=50, p2_y=0, known_distance_ft=5.0)
    assert cal.origin_x_ft == 0.0
    assert cal.origin_y_ft == 0.0


def test_scale_calibration_json_roundtrip():
    cal = ScaleCalibration(p1_x=10, p1_y=20, p2_x=110, p2_y=20, known_distance_ft=5.0)
    restored = ScaleCalibration.model_validate_json(cal.model_dump_json())
    assert restored.pixels_per_foot == pytest.approx(cal.pixels_per_foot)
    assert restored.p1_x == 10


# ── ReferenceAsset model ──────────────────────────────────────────────────────

def test_reference_asset_defaults():
    asset = ReferenceAsset(
        id="ref-abc", project_id="proj-1",
        file_name="sketch.png", file_path="ref-abc_sketch.png",
        mime_type="image/png", file_size_bytes=1024,
    )
    assert asset.scale_status == "uncalibrated"
    assert asset.calibration is None
    assert asset.extracted_entities == []
    assert asset.needs_review is True
    assert asset.reference_type == "reference_image"


def test_reference_asset_json_roundtrip():
    asset = ReferenceAsset(
        id="ref-xyz", project_id="proj-2",
        file_name="plan.jpg", file_path="ref-xyz_plan.jpg",
        mime_type="image/jpeg", file_size_bytes=204800,
        notes="Old floor plan from 2019",
    )
    restored = ReferenceAsset.model_validate_json(asset.model_dump_json())
    assert restored.id == "ref-xyz"
    assert restored.notes == "Old floor plan from 2019"


# ── ReferenceStore CRUD ───────────────────────────────────────────────────────

def test_store_create_saves_file_and_metadata(store, tmp_path):
    asset = store.create(_USER, _PID, _FAKE_PNG, "sketch.png", "image/png")
    assert asset.id.startswith("ref-")
    assert asset.file_size_bytes == len(_FAKE_PNG)
    assert asset.mime_type == "image/png"
    # Metadata file exists
    assert (tmp_path / "users" / _USER / "projects" / _PID / "references" / f"{asset.id}.json").exists()
    # Binary file exists
    bin_path = tmp_path / "users" / _USER / "projects" / _PID / "references" / "files" / asset.file_path
    assert bin_path.exists()
    assert bin_path.read_bytes() == _FAKE_PNG


def test_store_list_empty(store):
    assert store.list(_USER, _PID) == []


def test_store_list_returns_created(store):
    a1 = store.create(_USER, _PID, _FAKE_PNG, "a.png", "image/png")
    a2 = store.create(_USER, _PID, _FAKE_PNG, "b.png", "image/png")
    ids = {a.id for a in store.list(_USER, _PID)}
    assert a1.id in ids
    assert a2.id in ids


def test_store_get_returns_asset(store):
    asset = store.create(_USER, _PID, _FAKE_PNG, "x.png", "image/png")
    fetched = store.get(_USER, _PID, asset.id)
    assert fetched.id == asset.id
    assert fetched.file_name == asset.file_name


def test_store_get_missing_raises(store):
    with pytest.raises(KeyError):
        store.get(_USER, _PID, "ref-nonexistent")


def test_store_delete_removes_both(store, tmp_path):
    asset = store.create(_USER, _PID, _FAKE_PNG, "del.png", "image/png")
    bin_path = store.get_file_path(_USER, _PID, asset.id)
    meta_path = tmp_path / "users" / _USER / "projects" / _PID / "references" / f"{asset.id}.json"

    store.delete(_USER, _PID, asset.id)

    assert not bin_path.exists()
    assert not meta_path.exists()


def test_store_delete_then_get_raises(store):
    asset = store.create(_USER, _PID, _FAKE_PNG, "del2.png", "image/png")
    store.delete(_USER, _PID, asset.id)
    with pytest.raises(KeyError):
        store.get(_USER, _PID, asset.id)


def test_store_set_calibration(store):
    asset = store.create(_USER, _PID, _FAKE_PNG, "plan.png", "image/png")
    cal = ScaleCalibration(p1_x=0, p1_y=0, p2_x=120, p2_y=0, known_distance_ft=10.0)
    updated = store.set_calibration(_USER, _PID, asset.id, cal)
    assert updated.scale_status == "calibrated"
    assert updated.calibration is not None
    assert updated.calibration.pixels_per_foot == pytest.approx(12.0)


def test_store_calibration_persists_on_reload(store):
    asset = store.create(_USER, _PID, _FAKE_PNG, "persist.png", "image/png")
    cal = ScaleCalibration(p1_x=10, p1_y=10, p2_x=110, p2_y=10, known_distance_ft=5.0)
    store.set_calibration(_USER, _PID, asset.id, cal)

    reloaded = store.get(_USER, _PID, asset.id)
    assert reloaded.scale_status == "calibrated"
    assert reloaded.calibration.pixels_per_foot == pytest.approx(20.0)


def test_store_update_notes(store):
    asset = store.create(_USER, _PID, _FAKE_PNG, "note.png", "image/png", notes="initial")
    asset.notes = "updated note"
    updated = store.update(_USER, _PID, asset)
    assert updated.notes == "updated note"
    reloaded = store.get(_USER, _PID, asset.id)
    assert reloaded.notes == "updated note"


def test_store_get_file_path_resolves(store, tmp_path):
    asset = store.create(_USER, _PID, _FAKE_PNG, "img.png", "image/png")
    fp = store.get_file_path(_USER, _PID, asset.id)
    assert fp.exists()
    assert fp.read_bytes() == _FAKE_PNG


def test_store_creates_parent_dirs(store, tmp_path):
    pid2 = "proj-new-never-existed"
    asset = store.create(_USER, pid2, _FAKE_PNG, "new.png", "image/png")
    assert store.get(_USER, pid2, asset.id).id == asset.id


def test_store_file_name_sanitized(store):
    asset = store.create(_USER, _PID, _FAKE_PNG, "../../../etc/passwd", "image/png")
    assert "/" not in asset.file_name
    assert "\\" not in asset.file_name
    assert asset.file_name == "passwd"


def test_store_multiple_projects_isolated(store):
    a = store.create(_USER, "proj-a", _FAKE_PNG, "a.png", "image/png")
    b = store.create(_USER, "proj-b", _FAKE_PNG, "b.png", "image/png")
    assert store.list(_USER, "proj-a") == [a]
    assert store.list(_USER, "proj-b") == [b]


# ── ExtractedEntity model ─────────────────────────────────────────────────────

def test_extracted_entity_defaults():
    e = ExtractedEntity(id="ent-1", entity_type="wall", geometry={"x1": 0, "y1": 0, "x2": 10, "y2": 0})
    assert e.confidence == 1.0
    assert e.needs_review is True
    assert e.linked_project_object_id is None


def test_extracted_entity_json_roundtrip():
    e = ExtractedEntity(
        id="ent-2", entity_type="room",
        geometry={"x": 5, "y": 5, "w": 10, "h": 12},
        label="Kitchen", confidence=0.85,
    )
    r = ExtractedEntity.model_validate_json(e.model_dump_json())
    assert r.label == "Kitchen"
    assert r.confidence == pytest.approx(0.85)


def test_store_add_extracted_entity(store):
    asset = store.create(_USER, _PID, _FAKE_PNG, "extracted.png", "image/png")
    updated = store.add_extracted_entity(
        _USER, _PID, asset.id,
        entity_type="wall",
        geometry={"x1": 0, "y1": 0, "x2": 100, "y2": 0},
        label="North wall",
        confidence=0.9,
    )
    assert len(updated.extracted_entities) == 1
    ent = updated.extracted_entities[0]
    assert ent.entity_type == "wall"
    assert ent.label == "North wall"
    assert ent.confidence == pytest.approx(0.9)
