# Database Strategy — Scotch (Phase 18.2)

Scotch is local-first: `project.json` files on disk are the authoritative
store. This document describes the database layer that activates when Scotch
goes multi-user or cloud-hosted.

---

## Current state (Phase 18): JSON on disk

```
data/users/{user_id}/projects/{project_id}/project.json
data/users/{user_id}/projects/{project_id}/exports/manifest.json
```

**Listing** (`GET /projects`) scans the directory tree. Adequate for
one user / dozens of projects; becomes slow at thousands.

**Accelerator available now:** `SqliteProjectIndex` (`core/storage/sqlite_index.py`)
provides a drop-in fast listing layer for the local store without a server.

---

## Phase 18+ database design

### Trade-off: Postgres vs. MongoDB

| Concern | Postgres | MongoDB |
|---|---|---|
| Structured metadata (users, exports, versions) | ✅ Strong SQL joins | ⚠️ Aggregation pipelines |
| JSON document store (ArchitectureProject) | ✅ `jsonb` column | ✅ Native document |
| Schema migrations | ✅ Alembic | ⚠️ Manual / Mongoose |
| Hosting simplicity | ✅ Supabase, Railway, Render | ⚠️ Atlas ($$$) |
| Full-text search on room names/prompts | ✅ `tsvector` | ✅ Atlas Search |
| **Verdict** | **Recommended** | Acceptable if document flexibility needed |

**Decision:** Postgres with `jsonb` for the `ArchitectureProject` document.
Supabase (Postgres-as-a-Service) is the primary target for its built-in
auth integration with the OAuth strategy (see `auth-strategy.md`).

---

## Schema

### `users`
```sql
CREATE TABLE users (
    user_id     TEXT PRIMARY KEY,          -- Google OAuth sub
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    last_seen   TIMESTAMPTZ DEFAULT now()
);
```

### `projects`
```sql
CREATE TABLE projects (
    project_id  TEXT PRIMARY KEY,          -- "proj-<uuid12>"
    user_id     TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    prompt      TEXT,
    design      JSONB,                     -- ArchitectureProject JSON
    options     JSONB DEFAULT '[]',        -- list[DesignOption]
    room_count  SMALLINT DEFAULT 0,        -- denormalized for fast listing
    site_label  TEXT,                      -- denormalized for fast listing
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_projects_user_updated
    ON projects (user_id, updated_at DESC);
```

### `exports`
```sql
CREATE TABLE exports (
    export_id   SERIAL PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    filename    TEXT NOT NULL,
    format      TEXT NOT NULL,
    storage_key TEXT NOT NULL,             -- S3/Supabase object key
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_exports_project ON exports (project_id);
```

### `versions` (Phase 19)
```sql
CREATE TABLE versions (
    version_id  TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    change_type TEXT NOT NULL,             -- generate|regenerate|edit|option|restore
    summary     TEXT,
    snapshot    JSONB NOT NULL,            -- full ArchitectureProject at this point
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_versions_project ON versions (project_id, created_at DESC);
```

---

## SQLite index (available now)

`SqliteProjectIndex` in `core/storage/sqlite_index.py` provides fast listing
without a Postgres server. It maintains a single-table summary of all
projects in the local store, ordered by `updated_at`.

```python
from app.core.storage.sqlite_index import SqliteProjectIndex
from pathlib import Path

index = SqliteProjectIndex(Path("data/project_index.db"))
index.upsert(user_id, summarize(stored))  # call after every create/update
index.remove(user_id, project_id)         # call after every delete
summaries = index.list(user_id)           # instead of directory scan
```

**Parity guarantee:** `index.list()` returns the same summaries as
`LocalProjectStore.list_projects()` for the same data set
(verified in `test_cloud_readiness.py`).

---

## Migration path: disk → Postgres

1. Run `scripts/migrate_to_postgres.py` (Phase 18+):
   - Scans `data/users/*/projects/*/project.json`
   - Inserts into `projects` table
   - Uploads export files to S3/Supabase Storage
   - Records object keys in `exports` table
2. Flip `SCOTCH_STORAGE_BACKEND=cloud` and `SCOTCH_DB_URL=...`
3. Verify with smoke tests; local data can be kept as backup
4. Optionally prune `data/` after validation

---

## When to graduate from JSON-on-disk

| Signal | Action |
|---|---|
| > 1 concurrent user | Add `SqliteProjectIndex` for fast listing |
| > 1 server instance | Move to Postgres + S3 (race conditions on disk) |
| > 500 projects per user | Postgres full-text search on `prompt` |
| Multi-tenant SaaS launch | Postgres row-level security (RLS) |

*Generated by Scotch — Phase 18.2*
