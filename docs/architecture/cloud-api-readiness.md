# Cloud API Readiness — Scotch (Phase 18.5)

Audit of the Scotch FastAPI routes confirming they are stateless and
ownership-scoped. Every project-mutating operation goes through
`(user_id, project_id)` via injected dependencies.

---

## Route audit

### `GET /health` — `health.py`
- No user data. Stateless. ✅

### `GET /projects/sample` — `projects.py`
- Returns a hard-coded sample project. No store access. Stateless. ✅

### `POST /projects` — `projects.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.create_project(name, prompt, user_id=user_id)` ✅

### `GET /projects` — `projects.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.list_projects(user_id=user_id)` ✅
- Pagination: `skip` / `limit` query params are the next step (see below).

### `GET /projects/{id}` — `projects.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.get_project(project_id, user_id=user_id)` — 404 if user_id mismatch ✅

### `PATCH /projects/{id}` — `projects.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.update_project(project_id, ..., user_id=user_id)` ✅

### `DELETE /projects/{id}` — `projects.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.delete_project(project_id, user_id=user_id)` ✅

### `POST /projects/{id}/exports/{fmt}` — `exports.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.get_project(project_id, user_id=user_id)` ✅
- `store.get_export_path(project_id, filename, user_id=user_id)` ✅
- `store.save_export_manifest(project_id, manifest, user_id=user_id)` ✅

### `GET /projects/{id}/exports` — `exports.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.list_export_manifests(project_id, user_id=user_id)` ✅

### `GET /projects/{id}/exports/{filename}` — `exports.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.get_export_path(project_id, filename, user_id=user_id)` ✅

### `GET /projects/{id}/intelligence` — `intelligence.py`
- `user_id = Depends(get_current_user_id)` ✅
- `store.get_project(project_id, user_id=user_id)` ✅

### `POST /generate/from-prompt` — `generate.py`
- No store access. Stateless generation endpoint. ✅

### `POST /generate/regenerate` — `generate.py`
- No store access. Stateless. ✅

### `POST /generate/options` — `generate.py`
- No store access. Stateless. ✅

### `GET /integrations/sketchup/extension*` — `integrations.py`
- Serves static files from `integrations/sketchup/`. No user data. ✅

### `GET /settings` / `GET /settings/status` — `settings.py`
- Returns global settings / AI provider status. No user data. ✅

**Summary:** All 16 project-data routes are stateless (no global state)
and properly scoped through `(user_id, project_id)`. ✅

---

## Global state audit

No route reads module-level mutable state. The only module-level state is:

| Location | State | Safe? |
|---|---|---|
| `get_settings()` | `@lru_cache` of `Settings` (immutable once loaded) | ✅ (read-only) |
| `get_project_store()` | `@lru_cache` of `ProjectStore` instance | ✅ (factory only; store itself is thread-safe for local) |
| `get_provider()` | `@lru_cache` of AI provider | ✅ (read-only config) |

All three are safe for concurrent requests. Cloud backends will need the
store to be per-request (or stateless) — remove `@lru_cache` from
`get_project_store` when adding cloud backends.

---

## Pagination (Phase 18.5 — ready to add)

For scalable listing, add `skip` and `limit` query params:

```python
@router.get("", response_model=list[ProjectSummary])
def list_projects(
    skip:    int = Query(0, ge=0),
    limit:   int = Query(50, ge=1, le=200),
    store:   ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> list[ProjectSummary]:
    return store.list_projects(user_id=user_id, skip=skip, limit=limit)
```

`ProjectStore.list_projects` would need `skip`/`limit` params added.
The `SqliteProjectIndex.list()` already returns newest-first; add
`LIMIT ? OFFSET ?` to the SQL query.

The Postgres implementation uses `LIMIT/OFFSET` natively on the
`projects` table index.

---

## Auth headers (future)

When Google OAuth is active, all authenticated requests carry:

```
Authorization: Bearer <jwt>
```

The `get_current_user_id` dependency verifies the JWT and returns `sub`.

For local development without auth (Phase ≤ 18):
- No header required; dependency returns `"local-user"`.

For testing with auth (Phase 18+):
```python
app.dependency_overrides[get_current_user_id] = lambda: "test-user-abc"
```

---

## Cloud deployment checklist

- [ ] Replace `get_current_user_id` body with JWT decode
- [ ] Set `SCOTCH_STORAGE_BACKEND=cloud`
- [ ] Configure `SCOTCH_CLOUD_BUCKET`, `SCOTCH_CLOUD_REGION`, `SCOTCH_CLOUD_DB_URL`
- [ ] Remove `@lru_cache` from `get_project_store` (cloud store must be per-request)
- [ ] Add `skip`/`limit` to `list_projects` for paginated listing
- [ ] Add rate limiting middleware (slowapi or a gateway)
- [ ] Enable CORS only for the production frontend origin

*Generated by Scotch — Phase 18.5*
