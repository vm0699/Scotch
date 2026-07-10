"""Local user profile store — Phase 33.2.

Persists UserProfile as JSON sidecar at:
  services/api/app/data/users/{user_id}/profile.json

The storage root mirrors LocalProjectStore so the same data/ tree hosts both.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.profile.models import UserProfile

_DATA_ROOT = Path(__file__).parent.parent.parent / "data" / "users"


class LocalUserProfileStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _DATA_ROOT

    def _path(self, user_id: str) -> Path:
        return self._root / user_id / "profile.json"

    def get_profile(self, user_id: str) -> UserProfile:
        p = self._path(user_id)
        if p.exists():
            return UserProfile.model_validate_json(p.read_text(encoding="utf-8"))
        return UserProfile()

    def save_profile(self, user_id: str, profile: UserProfile) -> UserProfile:
        p = self._path(user_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return profile

    def update_profile(self, user_id: str, **updates) -> UserProfile:
        profile = self.get_profile(user_id)
        updated = profile.model_copy(update=updates)
        return self.save_profile(user_id, updated)


_default_store: LocalUserProfileStore | None = None


def get_profile_store() -> LocalUserProfileStore:
    global _default_store
    if _default_store is None:
        _default_store = LocalUserProfileStore()
    return _default_store
