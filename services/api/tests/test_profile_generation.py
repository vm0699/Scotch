"""Phase 33 — PromptProfileFusion + generation personalisation tests."""

from __future__ import annotations

import pytest

from app.core.architecture.requirement_parser import DesignRequirements, parse_prompt
from app.core.profile.fusion import PromptProfileFusion
from app.core.profile.models import ClientBrief, UserProfile


def _req(**kwargs) -> DesignRequirements:
    base = parse_prompt("2BHK house")
    return base.model_copy(update=kwargs)


# ── Budget → size_modifier ────────────────────────────────────────────────────

def test_economy_budget_reduces_size():
    req = _req(size_modifier=1.0)
    brief = ClientBrief(budget_level="economy")
    result, reasoning = PromptProfileFusion.apply(req, None, brief)
    assert result.size_modifier == pytest.approx(0.85)
    assert any("economy" in r.lower() for r in reasoning)


def test_premium_budget_increases_size():
    req = _req(size_modifier=1.0)
    brief = ClientBrief(budget_level="premium")
    result, reasoning = PromptProfileFusion.apply(req, None, brief)
    assert result.size_modifier == pytest.approx(1.2)
    assert any("premium" in r.lower() for r in reasoning)


def test_standard_budget_no_size_change():
    req = _req(size_modifier=1.0)
    brief = ClientBrief(budget_level="standard")
    result, _ = PromptProfileFusion.apply(req, None, brief)
    assert result.size_modifier == pytest.approx(1.0)


def test_size_modifier_not_overridden_if_already_set():
    req = _req(size_modifier=0.9)
    brief = ClientBrief(budget_level="economy")
    result, _ = PromptProfileFusion.apply(req, None, brief)
    # Only overrides if was 1.0 (default)
    assert result.size_modifier == pytest.approx(0.9)


# ── Vastu → orientation ───────────────────────────────────────────────────────

def test_vastu_sets_east_orientation():
    req = _req(assumptions=["Orientation not specified — defaulting to east-facing."])
    brief = ClientBrief(vastu_preference=True)
    result, reasoning = PromptProfileFusion.apply(req, None, brief)
    assert result.orientation == "east"
    assert any("vastu" in r.lower() for r in reasoning)


def test_no_vastu_no_orientation_change():
    req = _req(orientation="north")
    brief = ClientBrief(vastu_preference=False)
    result, _ = PromptProfileFusion.apply(req, None, brief)
    assert result.orientation == "north"


# ── Parking ───────────────────────────────────────────────────────────────────

def test_parking_added_from_brief():
    req = _req(parking=False)
    brief = ClientBrief(parking_preference="car")
    result, reasoning = PromptProfileFusion.apply(req, None, brief)
    assert result.parking is True
    assert any("parking" in r.lower() for r in reasoning)


def test_no_parking_added_if_already_present():
    req = _req(parking=True)
    brief = ClientBrief(parking_preference="car")
    result, reasoning = PromptProfileFusion.apply(req, None, brief)
    assert result.parking is True
    # Should not add duplicate reasoning
    assert sum(1 for r in reasoning if "parking" in r.lower()) <= 1


# ── Future expansion → storage ────────────────────────────────────────────────

def test_future_expansion_adds_storage():
    req = _req(storage=False)
    brief = ClientBrief(future_expansion=True)
    result, reasoning = PromptProfileFusion.apply(req, None, brief)
    assert result.storage is True
    assert any("storage" in r.lower() for r in reasoning)


# ── Family size → bedrooms ────────────────────────────────────────────────────

def test_family_of_4_bumps_bedrooms():
    req = _req(bedrooms=2, assumptions=["Bedroom count not specified — defaulting to 2."])
    brief = ClientBrief(family_size=4)
    result, reasoning = PromptProfileFusion.apply(req, None, brief)
    assert result.bedrooms == 3
    assert any("bedroom" in r.lower() for r in reasoning)


def test_family_of_2_does_not_bump_bedrooms():
    req = _req(bedrooms=2, assumptions=["Bedroom count not specified — defaulting to 2."])
    brief = ClientBrief(family_size=2)
    result, _ = PromptProfileFusion.apply(req, None, brief)
    assert result.bedrooms == 2


# ── Style from brief / profile ────────────────────────────────────────────────

def test_style_from_brief():
    req = _req(assumptions=["Style not specified — using modern."])
    brief = ClientBrief(style_preference="vernacular")
    result, reasoning = PromptProfileFusion.apply(req, None, brief)
    assert result.style == "vernacular"
    assert any("style" in r.lower() for r in reasoning)


def test_style_from_profile_when_no_brief_style():
    req = _req(assumptions=["Style not specified — using modern."])
    profile = UserProfile(default_style="industrial")
    result, reasoning = PromptProfileFusion.apply(req, profile, None)
    assert result.style == "industrial"
    assert any("profile" in r.lower() for r in reasoning)


def test_brief_style_takes_precedence_over_profile():
    req = _req(assumptions=["Style not specified — using modern."])
    profile = UserProfile(default_style="industrial")
    brief = ClientBrief(style_preference="tropical")
    result, _ = PromptProfileFusion.apply(req, profile, brief)
    assert result.style == "tropical"


# ── Orientation from profile ──────────────────────────────────────────────────

def test_profile_orientation_applied():
    req = _req(assumptions=["Orientation not specified — defaulting to east-facing."])
    profile = UserProfile(default_orientation="north")
    result, reasoning = PromptProfileFusion.apply(req, profile, None)
    assert result.orientation == "north"
    assert any("orientation" in r.lower() for r in reasoning)


# ── No changes when nothing to apply ─────────────────────────────────────────

def test_no_profile_no_brief_returns_unchanged():
    req = parse_prompt("3BHK villa 40x60")
    result, reasoning = PromptProfileFusion.apply(req, None, None)
    assert result == req
    assert reasoning == []


# ── Different output for different briefs ─────────────────────────────────────

def test_economy_vs_premium_differ():
    req = _req(size_modifier=1.0)
    economy_result, _ = PromptProfileFusion.apply(req, None, ClientBrief(budget_level="economy"))
    premium_result, _ = PromptProfileFusion.apply(req, None, ClientBrief(budget_level="premium"))
    assert economy_result.size_modifier != premium_result.size_modifier
