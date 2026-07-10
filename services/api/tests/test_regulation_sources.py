"""Tests for TN regulation source library — Phase 32.2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent.parent / "app" / "data" / "regulations" / "tamil_nadu"


def test_sources_file_exists() -> None:
    assert (DATA_DIR / "sources.json").exists()


def test_rules_file_exists() -> None:
    assert (DATA_DIR / "rules.json").exists()


def test_sources_valid_json() -> None:
    data = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) > 0


def test_rules_valid_json() -> None:
    data = json.loads((DATA_DIR / "rules.json").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) > 0


def test_every_source_has_required_fields() -> None:
    data = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))
    required = {"source_id", "name", "jurisdiction", "issuer", "version_date", "confidence"}
    for src in data:
        missing = required - src.keys()
        assert not missing, f"Source '{src.get('source_id')}' missing fields: {missing}"


def test_every_rule_has_required_fields() -> None:
    data = json.loads((DATA_DIR / "rules.json").read_text(encoding="utf-8"))
    required = {"rule_id", "title", "category", "check_logic_key", "source_id",
                "confidence", "needs_professional_verification"}
    for rule in data:
        missing = required - rule.keys()
        assert not missing, f"Rule '{rule.get('rule_id')}' missing fields: {missing}"


def test_every_rule_has_source_reference() -> None:
    sources = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))
    rules = json.loads((DATA_DIR / "rules.json").read_text(encoding="utf-8"))
    source_ids = {s["source_id"] for s in sources}
    for rule in rules:
        assert rule["source_id"] in source_ids, (
            f"Rule '{rule['rule_id']}' references unknown source '{rule['source_id']}'"
        )


def test_rule_ids_are_unique() -> None:
    data = json.loads((DATA_DIR / "rules.json").read_text(encoding="utf-8"))
    ids = [r["rule_id"] for r in data]
    assert len(ids) == len(set(ids)), "Duplicate rule_id found"


def test_source_ids_are_unique() -> None:
    data = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))
    ids = [s["source_id"] for s in data]
    assert len(ids) == len(set(ids)), "Duplicate source_id found"


def test_placeholder_rules_flagged() -> None:
    data = json.loads((DATA_DIR / "rules.json").read_text(encoding="utf-8"))
    for rule in data:
        # Every rule must have is_placeholder field
        assert "is_placeholder" in rule, f"Rule '{rule['rule_id']}' missing is_placeholder"


def test_confidence_values_in_range() -> None:
    rules = json.loads((DATA_DIR / "rules.json").read_text(encoding="utf-8"))
    sources = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))
    for rule in rules:
        c = rule["confidence"]
        assert 0.0 <= c <= 1.0, f"Rule '{rule['rule_id']}' confidence {c} out of range"
    for src in sources:
        c = src["confidence"]
        assert 0.0 <= c <= 1.0, f"Source '{src['source_id']}' confidence {c} out of range"


def test_known_rule_ids_present() -> None:
    data = json.loads((DATA_DIR / "rules.json").read_text(encoding="utf-8"))
    ids = {r["rule_id"] for r in data}
    expected = {
        "tn_site_completeness", "tn_setback_advisory", "tn_fsi_advisory",
        "tn_ground_coverage", "tn_parking_advisory",
        "tn_rainwater_harvesting", "tn_stair_advisory", "tn_approval_checklist",
    }
    assert expected <= ids, f"Missing rule IDs: {expected - ids}"
