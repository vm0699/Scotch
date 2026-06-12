"""Storage backend selection.

settings.storage_backend picks the implementation; "local" is the only one
today. Cloud backends (Phase 18: S3/Supabase object storage, database-backed
metadata) register here without callers changing.
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
    raise ValueError(f"Unknown storage backend '{settings.storage_backend}'")
