"""Phase 33 — UserProfile and ClientBrief model tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.profile.models import ClientBrief, UserProfile
from app.core.profile.store import LocalUserProfileStore


# ── UserProfile ────────────────────────────────────────────────────────────────


def test_user_profile_defaults():
    p = UserProfile()
    assert p.role == "architect"
    assert p.preferred_units == "feet"
    assert p.default_location == "India"
    assert p.default_style == "modern minimal"
    assert p.default_orientation == "east"
    assert p.explanation_style == "brief"
    assert p.preferred_room_sizes == {}
    assert p.material_preferences == []


def test_user_profile_round_trip():
    p = UserProfile(
        role="student",
        preferred_units="meters",
        default_location="Chennai",
        default_style="contemporary",
    )
    restored = UserProfile.model_validate_json(p.model_dump_json())
    assert restored.role == "student"
    assert restored.preferred_units == "meters"
    assert restored.default_location == "Chennai"


def test_user_profile_invalid_role():
    with pytest.raises(Exception):
        UserProfile(role="manager")  # type: ignore[arg-type]


# ── ClientBrief ────────────────────────────────────────────────────────────────


def test_client_brief_defaults():
    b = ClientBrief()
    assert b.budget_level == "standard"
    assert b.family_size == 0
    assert b.vastu_preference is False
    assert b.parking_preference == "car"
    assert b.future_expansion is False
    assert b.special_needs == []


def test_client_brief_round_trip():
    b = ClientBrief(
        family_name="Kumar",
        family_size=4,
        budget_level="economy",
        vastu_preference=True,
        parking_preference="both",
        future_expansion=True,
    )
    restored = ClientBrief.model_validate_json(b.model_dump_json())
    assert restored.family_name == "Kumar"
    assert restored.family_size == 4
    assert restored.budget_level == "economy"
    assert restored.vastu_preference is True
    assert restored.parking_preference == "both"
    assert restored.future_expansion is True


def test_client_brief_invalid_budget():
    with pytest.raises(Exception):
        ClientBrief(budget_level="luxury")  # type: ignore[arg-type]


# ── LocalUserProfileStore ─────────────────────────────────────────────────────


def test_store_get_missing_returns_default(tmp_path: Path):
    store = LocalUserProfileStore(root=tmp_path)
    profile = store.get_profile("user-1")
    assert isinstance(profile, UserProfile)
    assert profile.role == "architect"


def test_store_save_and_reload(tmp_path: Path):
    store = LocalUserProfileStore(root=tmp_path)
    p = UserProfile(role="owner", default_location="Coimbatore")
    store.save_profile("user-1", p)
    loaded = store.get_profile("user-1")
    assert loaded.role == "owner"
    assert loaded.default_location == "Coimbatore"


def test_store_update_profile(tmp_path: Path):
    store = LocalUserProfileStore(root=tmp_path)
    store.save_profile("user-1", UserProfile(role="student"))
    updated = store.update_profile("user-1", role="architect", default_style="vernacular")
    assert updated.role == "architect"
    assert updated.default_style == "vernacular"
    # Persisted
    reloaded = store.get_profile("user-1")
    assert reloaded.role == "architect"
    assert reloaded.default_style == "vernacular"


def test_store_creates_parent_dirs(tmp_path: Path):
    store = LocalUserProfileStore(root=tmp_path / "nested" / "dir")
    store.save_profile("user-1", UserProfile())
    assert (tmp_path / "nested" / "dir" / "user-1" / "profile.json").exists()


def test_profile_json_is_readable(tmp_path: Path):
    store = LocalUserProfileStore(root=tmp_path)
    store.save_profile("user-1", UserProfile(role="owner"))
    raw = json.loads((tmp_path / "user-1" / "profile.json").read_text())
    assert raw["role"] == "owner"
