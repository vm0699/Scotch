"""Storage backend selection — Phase 4 / 18.4.

SCOTCH_STORAGE_BACKEND selects the implementation:
  "local"  (default) → LocalProjectStore — filesystem under services/api/app/data/
  "cloud"            → CloudProjectStore stub (raises NotImplementedError; see
                        docs/architecture/cloud-storage-strategy.md for the
                        full implementation plan)

Cloud backends register here without callers changing. Routes receive
ProjectStore via Depends(get_project_store) and are unaware of the backend.
"""

from functools import lru_cache

from app.config import get_settings
from app.core.storage.base import ProjectStore
from app.core.storage.local_store import LocalProjectStore


@lru_cache
def get_project_store() -> ProjectStore:
    settings = get_settings()

    if settings.storage_backend == "local":
        return LocalProjectStore(settings.data_dir)

    if settings.storage_backend == "cloud":
        from app.core.storage.cloud_store import CloudProjectStore
        return CloudProjectStore(
            bucket=getattr(settings, "cloud_bucket", ""),
            region=getattr(settings, "cloud_region", ""),
        )

    raise ValueError(
        f"Unknown storage backend '{settings.storage_backend}'. "
        "Set SCOTCH_STORAGE_BACKEND to 'local' or 'cloud'."
    )
