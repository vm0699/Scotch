"""Phase 18 — Cloud & Account MVP tests.

Stages:
  18.1  Auth context seam — routes default to local-user; dependency override
        isolates data by user.
  18.2  SQLite project index — parity with directory scan.
  18.3  Cloud storage strategy doc — path mapping completeness.
  18.4  CloudProjectStore stub — satisfies ProjectStore ABC; factory selects
        correct backend.
  18.5  Cloud-ready API structure — no route reads global state; all
        project-data routes carry user_id dependency.
"""

import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.sample_factory import create_sample_project
from app.core.auth.context import LOCAL_USER_ID, get_current_user_id
from app.core.storage import (
    CloudProjectStore,
    ProjectIndex,
    ProjectStore,
    SqliteProjectIndex,
    get_project_store,
)
from app.core.storage.base import summarize
from app.core.storage.local_store import LocalProjectStore
from app.main import app

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOCS_ARCH  = _REPO_ROOT / "docs" / "architecture"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample():
    return create_sample_project()


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def project_with_design(client: TestClient):
    sample = client.get("/projects/sample").json()
    proj = client.post("/projects", json={"name": "Cloud Test House"}).json()
    client.patch(f"/projects/{proj['id']}", json={"project": sample})
    return proj["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 18.1 — Auth context seam
# ═══════════════════════════════════════════════════════════════════════════════


def test_18_1_get_current_user_id_returns_local_user():
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(get_current_user_id())
    assert result == LOCAL_USER_ID


def test_18_1_local_user_id_constant():
    assert LOCAL_USER_ID == "local-user"


def test_18_1_default_client_uses_local_user(client):
    """Routes with no override use local-user namespace."""
    r = client.post("/projects", json={"name": "Default User Project"})
    assert r.status_code == 201
    proj = r.json()
    # Retrieve it — should succeed under local-user
    r2 = client.get(f"/projects/{proj['id']}")
    assert r2.status_code == 200


def test_18_1_user_id_override_isolates_data(tmp_path: Path):
    """Projects created as user-A are not visible to user-B."""
    store = LocalProjectStore(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    app.dependency_overrides[get_current_user_id] = lambda: "user-alpha"

    with TestClient(app) as c_alpha:
        r = c_alpha.post("/projects", json={"name": "Alpha Project"})
        assert r.status_code == 201
        proj_id = r.json()["id"]

    # Switch to user-beta — project should not be found
    app.dependency_overrides[get_current_user_id] = lambda: "user-beta"
    with TestClient(app) as c_beta:
        r2 = c_beta.get(f"/projects/{proj_id}")
        assert r2.status_code == 404, "user-beta must not access user-alpha's project"

    app.dependency_overrides.clear()


def test_18_1_user_id_override_owns_own_data(tmp_path: Path):
    """Projects created as user-A are accessible to user-A."""
    store = LocalProjectStore(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    app.dependency_overrides[get_current_user_id] = lambda: "user-gamma"

    with TestClient(app) as c:
        r = c.post("/projects", json={"name": "Gamma Project"})
        assert r.status_code == 201
        proj_id = r.json()["id"]
        r2 = c.get(f"/projects/{proj_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == proj_id

    app.dependency_overrides.clear()


def test_18_1_projects_route_has_user_id_depends():
    from app.api.routes import projects as proj_routes
    sig = inspect.signature(proj_routes.list_projects)
    params = sig.parameters
    assert "user_id" in params, "list_projects must have user_id parameter"


def test_18_1_exports_route_has_user_id_depends():
    from app.api.routes import exports as exp_routes
    sig = inspect.signature(exp_routes.trigger_export)
    assert "user_id" in sig.parameters


def test_18_1_intelligence_route_has_user_id_depends():
    from app.api.routes import intelligence as intel_routes
    sig = inspect.signature(intel_routes.get_intelligence)
    assert "user_id" in sig.parameters


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 18.2 — SQLite project index
# ═══════════════════════════════════════════════════════════════════════════════


def test_18_2_sqlite_index_is_project_index_subclass():
    assert issubclass(SqliteProjectIndex, ProjectIndex)


def test_18_2_sqlite_index_upsert_and_list(tmp_path, sample):
    db = tmp_path / "index.db"
    idx = SqliteProjectIndex(db)
    assert db.exists()

    from datetime import datetime, timezone
    from app.core.storage.base import ProjectSummary
    s = ProjectSummary(
        id="proj-abc123",
        name="Test House",
        prompt="2BHK",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        room_count=5,
        site_label="30 × 50 ft",
    )
    idx.upsert("local-user", s)
    results = idx.list("local-user")
    assert len(results) == 1
    assert results[0].id == "proj-abc123"
    assert results[0].name == "Test House"
    assert results[0].room_count == 5


def test_18_2_sqlite_index_remove(tmp_path):
    db = tmp_path / "index.db"
    idx = SqliteProjectIndex(db)

    from datetime import datetime, timezone
    from app.core.storage.base import ProjectSummary
    s = ProjectSummary(
        id="proj-del",
        name="To Delete",
        prompt=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    idx.upsert("local-user", s)
    assert len(idx.list("local-user")) == 1

    idx.remove("local-user", "proj-del")
    assert idx.list("local-user") == []


def test_18_2_sqlite_index_upsert_is_idempotent(tmp_path):
    db = tmp_path / "index.db"
    idx = SqliteProjectIndex(db)

    from datetime import datetime, timezone
    from app.core.storage.base import ProjectSummary
    s = ProjectSummary(
        id="proj-same",
        name="Original",
        prompt=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    idx.upsert("local-user", s)
    s2 = s.model_copy(update={"name": "Updated"})
    idx.upsert("local-user", s2)

    results = idx.list("local-user")
    assert len(results) == 1
    assert results[0].name == "Updated"


def test_18_2_sqlite_index_orders_newest_first(tmp_path):
    db = tmp_path / "index.db"
    idx = SqliteProjectIndex(db)

    from datetime import datetime, timezone
    from app.core.storage.base import ProjectSummary

    for i, date in enumerate(["2026-01-01", "2026-06-01", "2026-03-01"]):
        s = ProjectSummary(
            id=f"proj-{i}",
            name=f"House {i}",
            prompt=None,
            created_at=datetime.fromisoformat(date + "T00:00:00+00:00"),
            updated_at=datetime.fromisoformat(date + "T00:00:00+00:00"),
        )
        idx.upsert("local-user", s)

    results = idx.list("local-user")
    assert results[0].id == "proj-1"  # 2026-06-01 newest
    assert results[-1].id == "proj-0"  # 2026-01-01 oldest


def test_18_2_sqlite_index_isolates_by_user(tmp_path):
    db = tmp_path / "index.db"
    idx = SqliteProjectIndex(db)

    from datetime import datetime, timezone
    from app.core.storage.base import ProjectSummary
    dt = datetime(2026, 1, 1, tzinfo=timezone.utc)

    idx.upsert("user-a", ProjectSummary(id="p1", name="A", prompt=None, created_at=dt, updated_at=dt))
    idx.upsert("user-b", ProjectSummary(id="p2", name="B", prompt=None, created_at=dt, updated_at=dt))

    assert [s.id for s in idx.list("user-a")] == ["p1"]
    assert [s.id for s in idx.list("user-b")] == ["p2"]


def test_18_2_sqlite_parity_with_directory_scan(tmp_path, sample):
    """Index.list() must equal LocalProjectStore.list_projects() for same data."""
    store = LocalProjectStore(tmp_path)
    db = tmp_path / "index.db"
    idx = SqliteProjectIndex(db)

    # Create 3 projects and upsert each into the index
    for name in ("Alpha House", "Beta Villa", "Gamma Studio"):
        stored = store.create_project(name=name)
        idx.upsert("local-user", summarize(stored))

    store_list = store.list_projects("local-user")
    index_list = idx.list("local-user")

    # Same ids, same names (order may differ slightly due to timing resolution)
    store_ids = {s.id for s in store_list}
    index_ids = {s.id for s in index_list}
    assert store_ids == index_ids, "Index must contain same project ids as store"

    store_names = {s.name for s in store_list}
    index_names = {s.name for s in index_list}
    assert store_names == index_names


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 18.3 — Cloud storage strategy doc
# ═══════════════════════════════════════════════════════════════════════════════


def test_18_3_cloud_storage_strategy_doc_exists():
    assert (_DOCS_ARCH / "cloud-storage-strategy.md").exists()


def test_18_3_doc_maps_project_json_path():
    doc = (_DOCS_ARCH / "cloud-storage-strategy.md").read_text(encoding="utf-8")
    assert "users/{uid}/projects/{pid}/project.json" in doc


def test_18_3_doc_maps_exports_path():
    doc = (_DOCS_ARCH / "cloud-storage-strategy.md").read_text(encoding="utf-8")
    assert "users/{uid}/projects/{pid}/exports" in doc


def test_18_3_doc_maps_manifest_path():
    doc = (_DOCS_ARCH / "cloud-storage-strategy.md").read_text(encoding="utf-8")
    assert "manifest.json" in doc


def test_18_3_doc_mentions_signed_urls():
    doc = (_DOCS_ARCH / "cloud-storage-strategy.md").read_text(encoding="utf-8")
    assert "signed" in doc.lower() or "presigned" in doc.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 18.4 — CloudProjectStore stub + factory
# ═══════════════════════════════════════════════════════════════════════════════


def test_18_4_cloud_store_is_project_store_subclass():
    assert issubclass(CloudProjectStore, ProjectStore)


def test_18_4_cloud_store_satisfies_abc():
    """CloudProjectStore must be instantiable (all abstract methods overridden)."""
    store = CloudProjectStore(bucket="test", region="us-east-1")
    assert isinstance(store, ProjectStore)


def test_18_4_cloud_store_raises_not_implemented():
    store = CloudProjectStore()
    with pytest.raises(NotImplementedError):
        store.list_projects(user_id="u1")


def test_18_4_cloud_store_raises_on_all_methods():
    store = CloudProjectStore()
    sample = create_sample_project()
    methods_and_args = [
        (store.list_projects,          ("u",)),
        (store.get_project,            ("p1", "u")),
        (store.delete_project,         ("p1", "u")),
        (store.list_export_manifests,  ("p1", "u")),
        (store.get_export_path,        ("p1", "file.json", "u")),
    ]
    for method, args in methods_and_args:
        with pytest.raises(NotImplementedError):
            method(*args)


def test_18_4_factory_returns_local_store_by_default(tmp_path, monkeypatch):
    from app.config import get_settings
    from app.core.storage.factory import get_project_store as factory_fn

    monkeypatch.setattr(get_settings(), "storage_backend", "local")
    monkeypatch.setattr(get_settings(), "data_dir", tmp_path)
    # Clear lru_cache to force re-evaluation
    factory_fn.cache_clear()
    store = factory_fn()
    assert isinstance(store, LocalProjectStore)
    factory_fn.cache_clear()


def test_18_4_factory_raises_on_unknown_backend(monkeypatch):
    from app.config import get_settings
    from app.core.storage.factory import get_project_store as factory_fn

    factory_fn.cache_clear()
    monkeypatch.setattr(get_settings(), "storage_backend", "unknown-backend")
    with pytest.raises(ValueError, match="Unknown storage backend"):
        factory_fn()
    factory_fn.cache_clear()


def test_18_4_cloud_store_exported_from_storage_init():
    from app.core import storage
    assert hasattr(storage, "CloudProjectStore")


def test_18_4_sqlite_index_exported_from_storage_init():
    from app.core import storage
    assert hasattr(storage, "SqliteProjectIndex")
    assert hasattr(storage, "ProjectIndex")


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 18.5 — Cloud-ready API structure
# ═══════════════════════════════════════════════════════════════════════════════


def test_18_5_auth_strategy_doc_exists():
    assert (_DOCS_ARCH / "auth-strategy.md").exists()


def test_18_5_database_strategy_doc_exists():
    assert (_DOCS_ARCH / "database-strategy.md").exists()


def test_18_5_cloud_api_readiness_doc_exists():
    assert (_DOCS_ARCH / "cloud-api-readiness.md").exists()


def test_18_5_auth_doc_covers_google_oauth():
    doc = (_DOCS_ARCH / "auth-strategy.md").read_text(encoding="utf-8")
    assert "Google" in doc
    assert "OAuth" in doc
    assert "PKCE" in doc


def test_18_5_auth_doc_covers_jwt():
    doc = (_DOCS_ARCH / "auth-strategy.md").read_text(encoding="utf-8")
    assert "JWT" in doc
    assert "sub" in doc


def test_18_5_cloud_api_doc_covers_all_routes():
    doc = (_DOCS_ARCH / "cloud-api-readiness.md").read_text(encoding="utf-8")
    for route in ("/projects", "/exports", "/intelligence", "/generate"):
        assert route in doc, f"Route {route!r} not documented in cloud-api-readiness.md"


def test_18_5_cloud_api_doc_mentions_pagination():
    doc = (_DOCS_ARCH / "cloud-api-readiness.md").read_text(encoding="utf-8")
    assert "skip" in doc or "pagination" in doc.lower()


def test_18_5_no_route_calls_store_without_user_id(tmp_path, client, project_with_design):
    """Smoke: all project routes function correctly via the user_id dependency."""
    r = client.get("/projects")
    assert r.status_code == 200

    r = client.get(f"/projects/{project_with_design}")
    assert r.status_code == 200

    r = client.post(f"/projects/{project_with_design}/exports/json")
    assert r.status_code == 201


def test_18_5_database_doc_covers_schema():
    doc = (_DOCS_ARCH / "database-strategy.md").read_text(encoding="utf-8")
    for table in ("users", "projects", "exports"):
        assert table in doc, f"Table {table!r} missing from database-strategy.md"


def test_18_5_database_doc_covers_postgres_vs_mongo():
    doc = (_DOCS_ARCH / "database-strategy.md").read_text(encoding="utf-8")
    assert "Postgres" in doc
    assert "Mongo" in doc or "MongoDB" in doc
