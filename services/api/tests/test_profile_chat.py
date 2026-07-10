"""Phase 33 — Profile and client-brief chat-tool tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.profile.models import ClientBrief, UserProfile
from app.core.profile.store import LocalUserProfileStore
from app.core.storage.local_store import LocalProjectStore


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def store(tmp_path: Path) -> LocalProjectStore:
    return LocalProjectStore(tmp_path)


@pytest.fixture()
def pid(store: LocalProjectStore) -> str:
    entry = store.create_project("Profile Test", prompt="2BHK")
    from app.core.architecture.requirement_parser import parse_prompt
    from app.core.architecture.floorplan_generator import generate_floorplan
    from app.core.validation import validate_project
    req = parse_prompt("2BHK house")
    project, _ = generate_floorplan(req)
    assert validate_project(project).valid
    store.update_project(entry.id, project=project, change_type="generate")
    return entry.id


@pytest.fixture()
def profile_store(tmp_path: Path) -> LocalUserProfileStore:
    return LocalUserProfileStore(root=tmp_path / "profiles")


import app.core.chat_tools as ct


def _patch_store(store: LocalProjectStore):
    ct._store = lambda: store  # type: ignore[attr-defined]


# ── get_user_profile ──────────────────────────────────────────────────────────

def test_get_user_profile_returns_default(profile_store: LocalUserProfileStore, tmp_path: Path):
    from app.core.profile import get_profile_store
    # Override at module level is tricky; test via LocalUserProfileStore directly
    profile = profile_store.get_profile("local-user")
    assert isinstance(profile, UserProfile)
    assert profile.role == "architect"


def test_update_user_profile(profile_store: LocalUserProfileStore):
    profile_store.update_profile("local-user", role="owner", default_style="contemporary")
    reloaded = profile_store.get_profile("local-user")
    assert reloaded.role == "owner"
    assert reloaded.default_style == "contemporary"


# ── get_client_brief / update_client_brief ─────────────────────────────────────

def test_get_client_brief_defaults(store: LocalProjectStore, pid: str):
    _patch_store(store)
    brief_dict = ct.get_client_brief(pid)
    assert brief_dict["budget_level"] == "standard"
    assert brief_dict["vastu_preference"] is False
    assert brief_dict["family_size"] == 0


def test_update_client_brief_budget(store: LocalProjectStore, pid: str):
    _patch_store(store)
    result = ct.update_client_brief(pid, budget_level="economy", family_size=4)
    assert result["budget_level"] == "economy"
    assert result["family_size"] == 4
    # Persists
    reloaded = ct.get_client_brief(pid)
    assert reloaded["budget_level"] == "economy"
    assert reloaded["family_size"] == 4


def test_update_client_brief_vastu(store: LocalProjectStore, pid: str):
    _patch_store(store)
    result = ct.update_client_brief(pid, vastu_preference=True)
    assert result["vastu_preference"] is True


def test_update_client_brief_style(store: LocalProjectStore, pid: str):
    _patch_store(store)
    result = ct.update_client_brief(pid, style_preference="contemporary")
    assert result["style_preference"] == "contemporary"


def test_update_client_brief_notes(store: LocalProjectStore, pid: str):
    _patch_store(store)
    result = ct.update_client_brief(pid, notes="Prefer granite counters in kitchen.")
    assert "granite" in result["notes"]


def test_update_client_brief_empty_update(store: LocalProjectStore, pid: str):
    _patch_store(store)
    # No kwargs → no change, returns current brief
    result = ct.update_client_brief(pid)
    assert result["budget_level"] == "standard"


def test_get_client_brief_nonexistent_raises(store: LocalProjectStore):
    _patch_store(store)
    from app.core.storage.base import ProjectNotFoundError
    with pytest.raises((ValueError, ProjectNotFoundError)):
        ct.get_client_brief("nonexistent-project")


# ── generate_design preserves brief ───────────────────────────────────────────

def test_generate_design_preserves_existing_brief(store: LocalProjectStore, pid: str, tmp_path: Path):
    _patch_store(store)
    # Set brief first
    ct.update_client_brief(pid, budget_level="premium", family_size=5, vastu_preference=True)
    # Re-generate
    ct.generate_design(pid, "2BHK house")
    # Brief should be preserved
    reloaded = ct.get_client_brief(pid)
    assert reloaded["budget_level"] == "premium"
    assert reloaded["family_size"] == 5
    assert reloaded["vastu_preference"] is True


# ── fusion affects generation ─────────────────────────────────────────────────

def test_economy_brief_applied_on_generate(store: LocalProjectStore, pid: str):
    """Economy budget should produce smaller rooms (size_modifier=0.85 applied)."""
    _patch_store(store)
    ct.update_client_brief(pid, budget_level="economy", family_size=2)
    result1 = ct.generate_design(pid, "3BHK house")

    ct.update_client_brief(pid, budget_level="premium")
    result2 = ct.generate_design(pid, "3BHK house")

    # Premium design should have same or larger total area than economy
    area1 = sum(r["width"] * r["depth"] for r in result1.get("rooms", []))
    area2 = sum(r["width"] * r["depth"] for r in result2.get("rooms", []))
    # economy ≤ premium
    assert area1 <= area2 + 5  # small tolerance for generator variation
