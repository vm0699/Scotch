from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.architecture.sample_factory import create_sample_project
from app.core.models import ExportManifest
from app.core.storage.base import ProjectNotFoundError
from app.core.storage.local_store import LocalProjectStore


@pytest.fixture
def store(tmp_path: Path) -> LocalProjectStore:
    return LocalProjectStore(tmp_path)


def test_create_and_get_round_trip(store: LocalProjectStore) -> None:
    created = store.create_project(name="My House", prompt="a 2bhk")
    loaded = store.get_project(created.id)
    assert loaded == created
    assert loaded.project is None
    assert loaded.created_at == loaded.updated_at


def test_create_writes_expected_layout(store: LocalProjectStore, tmp_path: Path) -> None:
    created = store.create_project(name="Layout Check")
    expected = tmp_path / "users" / "local-user" / "projects" / created.id / "project.json"
    assert expected.exists()


def test_list_orders_by_updated_desc(store: LocalProjectStore) -> None:
    first = store.create_project(name="First")
    second = store.create_project(name="Second")
    store.update_project(first.id, prompt="touched")
    listing = store.list_projects()
    assert [s.id for s in listing] == [first.id, second.id]


def test_update_design_data_and_summary(store: LocalProjectStore) -> None:
    created = store.create_project(name="With Design")
    updated = store.update_project(created.id, project=create_sample_project())
    assert updated.project is not None
    assert updated.updated_at >= created.updated_at
    summary = store.list_projects()[0]
    assert summary.room_count == 8
    assert summary.site_label == "30 × 50 ft"


def test_delete_removes_project(store: LocalProjectStore) -> None:
    created = store.create_project(name="Doomed")
    store.delete_project(created.id)
    assert store.list_projects() == []
    with pytest.raises(ProjectNotFoundError):
        store.get_project(created.id)


def test_missing_project_raises(store: LocalProjectStore) -> None:
    with pytest.raises(ProjectNotFoundError):
        store.get_project("nope")
    with pytest.raises(ProjectNotFoundError):
        store.update_project("nope", name="x")
    with pytest.raises(ProjectNotFoundError):
        store.delete_project("nope")


def test_persistence_across_store_instances(store: LocalProjectStore, tmp_path: Path) -> None:
    created = store.create_project(name="Survivor", project=create_sample_project())
    reopened = LocalProjectStore(tmp_path).get_project(created.id)
    assert reopened.name == "Survivor"
    assert reopened.project is not None
    assert len(reopened.project.rooms) == 8


def test_export_manifest_appends(store: LocalProjectStore, tmp_path: Path) -> None:
    created = store.create_project(name="Exports")
    manifest = ExportManifest(
        filename="plan.svg",
        format="svg",
        path="exports/plan.svg",
        created_at=datetime.now(timezone.utc),
    )
    store.save_export_manifest(created.id, manifest)
    store.save_export_manifest(created.id, manifest)
    file = (
        tmp_path / "users" / "local-user" / "projects" / created.id / "exports" / "manifest.json"
    )
    assert file.exists()
    import json

    assert len(json.loads(file.read_text())) == 2


def test_user_isolation(store: LocalProjectStore) -> None:
    store.create_project(name="Mine", user_id="user-a")
    assert store.list_projects(user_id="user-b") == []
    assert len(store.list_projects(user_id="user-a")) == 1
