"""Phase 37 — Cloud-store interface tests.

Verifies:
1. LocalProjectStore satisfies the full ProjectStore ABC contract.
2. CloudProjectStore stub raises NotImplementedError (not AttributeError).
3. Storage factory selects the right backend based on env var.
4. Injectable auth dep returns correct values in local vs cloud mode.
5. Migration planning: user-id path is substitutable.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

from app.core.storage.base import LOCAL_USER_ID, ProjectStore, StoredProject
from app.core.storage.cloud_store import CloudProjectStore
from app.core.storage.local_store import LocalProjectStore


# ── 1. LocalProjectStore satisfies the ProjectStore ABC ──────────────────────


def test_local_store_is_project_store_subclass():
    assert issubclass(LocalProjectStore, ProjectStore)


def test_local_store_instantiates(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    assert store is not None


def test_local_store_has_all_abstract_methods(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    abstract_methods = [
        "create_project", "list_projects", "get_project", "update_project",
        "delete_project", "save_export_manifest", "list_export_manifests",
        "get_export_path", "append_version", "list_versions", "get_version",
    ]
    for method_name in abstract_methods:
        assert hasattr(store, method_name) and callable(getattr(store, method_name)), \
            f"LocalProjectStore missing method: {method_name}"


def test_local_store_create_and_get(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    stored = store.create_project("My Project", user_id=LOCAL_USER_ID)
    assert stored.id.startswith("proj-")
    assert stored.name == "My Project"
    fetched = store.get_project(stored.id, user_id=LOCAL_USER_ID)
    assert fetched.id == stored.id


def test_local_store_list_projects(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    store.create_project("A", user_id=LOCAL_USER_ID)
    store.create_project("B", user_id=LOCAL_USER_ID)
    projects = store.list_projects(user_id=LOCAL_USER_ID)
    assert len(projects) == 2


def test_local_store_delete_project(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    s = store.create_project("Delete Me", user_id=LOCAL_USER_ID)
    store.delete_project(s.id, user_id=LOCAL_USER_ID)
    assert len(store.list_projects(user_id=LOCAL_USER_ID)) == 0


def test_local_store_project_not_found(tmp_path: Path):
    from app.core.storage.base import ProjectNotFoundError
    store = LocalProjectStore(tmp_path)
    with pytest.raises(ProjectNotFoundError):
        store.get_project("nonexistent", user_id=LOCAL_USER_ID)


def test_local_store_user_id_isolation(tmp_path: Path):
    """Projects created for user A are not visible to user B."""
    store = LocalProjectStore(tmp_path)
    store.create_project("UserA project", user_id="user-a")
    projects_b = store.list_projects(user_id="user-b")
    assert projects_b == []
    projects_a = store.list_projects(user_id="user-a")
    assert len(projects_a) == 1


def test_local_store_update_project(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    s = store.create_project("Original", user_id=LOCAL_USER_ID)
    store.update_project(s.id, name="Renamed", user_id=LOCAL_USER_ID)
    fetched = store.get_project(s.id, user_id=LOCAL_USER_ID)
    assert fetched.name == "Renamed"


def test_local_store_export_path(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    s = store.create_project("Export Test", user_id=LOCAL_USER_ID)
    path = store.get_export_path(s.id, "test.svg", user_id=LOCAL_USER_ID)
    assert isinstance(path, Path)
    assert "exports" in str(path)


def test_local_store_list_export_manifests_empty(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    s = store.create_project("No Exports", user_id=LOCAL_USER_ID)
    manifests = store.list_export_manifests(s.id, user_id=LOCAL_USER_ID)
    assert manifests == []


# ── 2. CloudProjectStore stub raises NotImplementedError ─────────────────────


def test_cloud_store_is_project_store_subclass():
    assert issubclass(CloudProjectStore, ProjectStore)


def test_cloud_store_instantiates():
    store = CloudProjectStore()
    assert store is not None


def test_cloud_store_create_raises():
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.create_project("Test")


def test_cloud_store_list_raises():
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.list_projects()


def test_cloud_store_get_raises():
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.get_project("any-id")


def test_cloud_store_update_raises():
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.update_project("any-id", name="Name")


def test_cloud_store_delete_raises():
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.delete_project("any-id")


def test_cloud_store_append_version_raises():
    from app.core.models.project import ProjectVersion
    from app.core.architecture.floorplan_generator import generate_floorplan
    from app.core.architecture.requirement_parser import parse_prompt
    from datetime import datetime, timezone
    proj, _ = generate_floorplan(parse_prompt("2BHK on 30x50 east facing site"))
    version = ProjectVersion(
        version_id="v-test",
        created_at=datetime.now(timezone.utc),
        change_type="generate",
        summary="Test",
        snapshot=proj,
    )
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.append_version("any-id", version)


def test_cloud_store_list_versions_raises():
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.list_versions("any-id")


def test_cloud_store_get_version_raises():
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.get_version("any-id", "v-1")


# ── 3. Storage factory backend selection ─────────────────────────────────────


def test_factory_returns_local_store_by_default():
    from app.core.storage.factory import get_project_store
    get_project_store.cache_clear()
    store = get_project_store()
    assert isinstance(store, LocalProjectStore)
    get_project_store.cache_clear()


def test_factory_returns_cloud_store_when_env_set(monkeypatch):
    monkeypatch.setenv("SCOTCH_STORAGE_BACKEND", "cloud")
    # Reload config and factory to pick up env change
    from app.core.storage.factory import get_project_store
    get_project_store.cache_clear()
    import app.config as cfg_module
    cfg_module.get_settings.cache_clear()
    store = get_project_store()
    assert isinstance(store, CloudProjectStore)
    get_project_store.cache_clear()
    cfg_module.get_settings.cache_clear()
    monkeypatch.delenv("SCOTCH_STORAGE_BACKEND", raising=False)


# ── 4. Injectable auth dep ────────────────────────────────────────────────────


def test_auth_dep_returns_local_user_in_local_mode(monkeypatch):
    monkeypatch.setenv("SCOTCH_AUTH_MODE", "local")
    import app.api.dependencies.auth as auth_mod
    import importlib
    importlib.reload(auth_mod)
    result = auth_mod.get_current_user_id(authorization=None)
    assert result == LOCAL_USER_ID
    importlib.reload(auth_mod)


def test_auth_dep_ignores_token_in_local_mode(monkeypatch):
    monkeypatch.setenv("SCOTCH_AUTH_MODE", "local")
    import app.api.dependencies.auth as auth_mod
    importlib.reload(auth_mod)
    result = auth_mod.get_current_user_id(authorization="Bearer some-token")
    assert result == LOCAL_USER_ID
    importlib.reload(auth_mod)


def test_auth_dep_raises_401_in_cloud_mode_no_token(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setenv("SCOTCH_AUTH_MODE", "cloud")
    import app.api.dependencies.auth as auth_mod
    importlib.reload(auth_mod)
    with pytest.raises(HTTPException) as exc_info:
        auth_mod.get_current_user_id(authorization=None)
    assert exc_info.value.status_code == 401
    importlib.reload(auth_mod)


def test_auth_dep_returns_user_id_in_cloud_mode_with_token(monkeypatch):
    monkeypatch.setenv("SCOTCH_AUTH_MODE", "cloud")
    import app.api.dependencies.auth as auth_mod
    importlib.reload(auth_mod)
    result = auth_mod.get_current_user_id(authorization="Bearer my-secret-token")
    assert result.startswith("cloud-user-")
    importlib.reload(auth_mod)


# ── 5. User-id path substitutability (migration planning) ────────────────────


def test_user_id_path_substitutable(tmp_path: Path):
    """Confirm that cloud-user-id paths work the same as local-user paths.

    Real Google subs are numeric; the prefix separator is '-' (not ':') to
    keep the path valid on Windows (colon is a reserved character there).
    """
    store = LocalProjectStore(tmp_path)
    cloud_uid = "google-117560258374901234567"
    s = store.create_project("Google User Project", user_id=cloud_uid)
    fetched = store.get_project(s.id, user_id=cloud_uid)
    assert fetched.name == "Google User Project"
    # Local user doesn't see cloud user's project
    local_projects = store.list_projects(user_id=LOCAL_USER_ID)
    assert all(p.id != s.id for p in local_projects)


def test_project_dir_path_contains_user_id(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    cloud_uid = "google-117560"
    s = store.create_project("Test", user_id=cloud_uid)
    path = store._project_file(cloud_uid, s.id)
    assert cloud_uid in str(path)


# ── 6. Profile model — Phase 37 account-mode fields ─────────────────────────


def test_user_profile_has_account_mode():
    from app.core.profile.models import UserProfile
    p = UserProfile()
    assert p.account_mode == "local"


def test_user_profile_account_mode_cloud():
    from app.core.profile.models import UserProfile
    p = UserProfile(account_mode="cloud", cloud_email="a@b.com", display_name="Priya")
    assert p.account_mode == "cloud"
    assert p.cloud_email == "a@b.com"
    assert p.display_name == "Priya"


def test_user_profile_default_no_cloud_email():
    from app.core.profile.models import UserProfile
    p = UserProfile()
    assert p.cloud_email is None
    assert p.cloud_user_id is None
    assert p.display_name == ""


def test_user_profile_roundtrip_with_cloud_fields():
    from app.core.profile.models import UserProfile
    p = UserProfile(
        account_mode="cloud",
        cloud_email="user@scotch.ai",
        cloud_user_id="google:12345",
        display_name="Vignesh",
    )
    json_str = p.model_dump_json()
    restored = UserProfile.model_validate_json(json_str)
    assert restored.account_mode == "cloud"
    assert restored.cloud_email == "user@scotch.ai"
    assert restored.cloud_user_id == "google:12345"
    assert restored.display_name == "Vignesh"
