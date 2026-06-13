"""Phase 10 — Design Options tests.

Covers: options_generator, /generate/options endpoint, size_modifier in the
floorplan generator, and options persistence via project PATCH.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.options_generator import generate_options
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models.project import DesignOption
from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app

# ── Fixtures ─────────────────────────────────────────────────────────────────

_PROMPT = "Design a 2BHK apartment on a 30x50 ft east-facing site."


class _MockSettings:
    generation_mode = "deterministic"
    ai_provider = "anthropic"
    anthropic_api_key = ""
    anthropic_model = "claude-sonnet-4-6"
    openai_api_key = ""
    openai_base_url = "https://api.openai.com/v1"
    openai_model = "gpt-4o"


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── size_modifier in floorplan generator ─────────────────────────────────────


class TestSizeModifier:
    def test_default_modifier_unchanged(self):
        req = parse_prompt(_PROMPT)
        project, _ = generate_floorplan(req)
        built_default = sum(r.width * r.depth for r in project.rooms)
        assert built_default > 0

    def test_compact_smaller_than_balanced(self):
        req = parse_prompt(_PROMPT)
        compact = generate_floorplan(req.model_copy(update={"size_modifier": 0.82}))[0]
        balanced = generate_floorplan(req.model_copy(update={"size_modifier": 1.00}))[0]
        built_compact = sum(r.width * r.depth for r in compact.rooms)
        built_balanced = sum(r.width * r.depth for r in balanced.rooms)
        assert built_compact < built_balanced

    def test_spacious_larger_than_balanced(self):
        req = parse_prompt(_PROMPT)
        balanced = generate_floorplan(req.model_copy(update={"size_modifier": 1.00}))[0]
        spacious = generate_floorplan(req.model_copy(update={"size_modifier": 1.20}))[0]
        built_balanced = sum(r.width * r.depth for r in balanced.rooms)
        built_spacious = sum(r.width * r.depth for r in spacious.rooms)
        assert built_spacious > built_balanced

    def test_modifier_does_not_change_room_count(self):
        req = parse_prompt(_PROMPT)
        compact = generate_floorplan(req.model_copy(update={"size_modifier": 0.82}))[0]
        balanced = generate_floorplan(req.model_copy(update={"size_modifier": 1.00}))[0]
        spacious = generate_floorplan(req.model_copy(update={"size_modifier": 1.20}))[0]
        assert len(compact.rooms) == len(balanced.rooms) == len(spacious.rooms)

    def test_rooms_never_below_min_dimension(self):
        req = parse_prompt(_PROMPT)
        project = generate_floorplan(req.model_copy(update={"size_modifier": 0.5}))[0]
        for room in project.rooms:
            assert room.width >= 4.0
            assert room.depth >= 4.0


# ── options_generator ─────────────────────────────────────────────────────────


class TestGenerateOptions:
    def test_returns_three_options(self):
        options = generate_options(_PROMPT, "deterministic", _MockSettings())
        assert len(options) == 3

    def test_variants_are_compact_balanced_spacious(self):
        options = generate_options(_PROMPT, "deterministic", _MockSettings())
        variants = [o.variant for o in options]
        assert variants == ["compact", "balanced", "spacious"]

    def test_option_ids_are_unique(self):
        options = generate_options(_PROMPT, "deterministic", _MockSettings())
        ids = [o.option_id for o in options]
        assert len(set(ids)) == 3

    def test_scores_are_in_valid_range(self):
        options = generate_options(_PROMPT, "deterministic", _MockSettings())
        for opt in options:
            assert 0.0 <= opt.score <= 10.0

    def test_balanced_has_highest_base_score(self):
        options = generate_options(_PROMPT, "deterministic", _MockSettings())
        by_variant = {o.variant: o.score for o in options}
        assert by_variant["balanced"] > by_variant["compact"]

    def test_each_option_has_preview_project(self):
        options = generate_options(_PROMPT, "deterministic", _MockSettings())
        for opt in options:
            assert opt.preview is not None
            assert len(opt.preview.rooms) > 0

    def test_compact_built_area_less_than_spacious(self):
        options = generate_options(_PROMPT, "deterministic", _MockSettings())
        by_variant = {o.variant: sum(r.width * r.depth for r in o.preview.rooms) for o in options}
        assert by_variant["compact"] < by_variant["spacious"]

    def test_summary_contains_room_count(self):
        options = generate_options(_PROMPT, "deterministic", _MockSettings())
        for opt in options:
            assert "room" in opt.summary.lower()

    def test_ai_mode_still_returns_deterministic_options(self):
        # Options are always deterministic regardless of mode param.
        options = generate_options(_PROMPT, "ai", _MockSettings())
        assert len(options) == 3


# ── /generate/options endpoint ────────────────────────────────────────────────


class TestOptionsEndpoint:
    def test_returns_200_with_three_options(self, client):
        resp = client.post("/generate/options", json={"prompt": _PROMPT})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["options"]) == 3

    def test_response_prompt_echoed(self, client):
        resp = client.post("/generate/options", json={"prompt": _PROMPT})
        assert resp.json()["prompt"] == _PROMPT

    def test_option_structure_is_complete(self, client):
        resp = client.post("/generate/options", json={"prompt": _PROMPT})
        opt = resp.json()["options"][0]
        for field in ("option_id", "variant", "score", "summary", "preview"):
            assert field in opt, f"Missing field: {field}"

    def test_preview_contains_rooms(self, client):
        resp = client.post("/generate/options", json={"prompt": _PROMPT})
        for opt in resp.json()["options"]:
            assert len(opt["preview"]["rooms"]) > 0

    def test_empty_prompt_returns_200(self, client):
        resp = client.post("/generate/options", json={"prompt": ""})
        assert resp.status_code == 200

    def test_mode_field_accepted(self, client):
        resp = client.post(
            "/generate/options",
            json={"prompt": _PROMPT, "mode": "deterministic"},
        )
        assert resp.status_code == 200

    def test_invalid_mode_returns_422(self, client):
        resp = client.post(
            "/generate/options",
            json={"prompt": _PROMPT, "mode": "invalid_mode"},
        )
        assert resp.status_code == 422


# ── Options persistence (PATCH /projects/{id}) ────────────────────────────────


class TestOptionsPersistence:
    def _create_project(self, client) -> str:
        resp = client.post("/projects", json={"name": "Test Project"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_patch_saves_options(self, client):
        pid = self._create_project(client)
        options_resp = client.post("/generate/options", json={"prompt": _PROMPT})
        options = options_resp.json()["options"]

        patch_resp = client.patch(f"/projects/{pid}", json={"options": options})
        assert patch_resp.status_code == 200
        assert len(patch_resp.json()["options"]) == 3

    def test_options_persist_across_get(self, client):
        pid = self._create_project(client)
        options_resp = client.post("/generate/options", json={"prompt": _PROMPT})
        options = options_resp.json()["options"]
        client.patch(f"/projects/{pid}", json={"options": options})

        get_resp = client.get(f"/projects/{pid}")
        assert len(get_resp.json()["options"]) == 3

    def test_patch_without_options_does_not_clear(self, client):
        pid = self._create_project(client)
        options_resp = client.post("/generate/options", json={"prompt": _PROMPT})
        options = options_resp.json()["options"]
        client.patch(f"/projects/{pid}", json={"options": options})

        # Patch with only name — options should remain.
        client.patch(f"/projects/{pid}", json={"name": "Renamed"})
        get_resp = client.get(f"/projects/{pid}")
        assert len(get_resp.json()["options"]) == 3

    def test_options_contain_preview_projects(self, client):
        pid = self._create_project(client)
        options_resp = client.post("/generate/options", json={"prompt": _PROMPT})
        options = options_resp.json()["options"]
        client.patch(f"/projects/{pid}", json={"options": options})

        stored = client.get(f"/projects/{pid}").json()
        for opt in stored["options"]:
            assert len(opt["preview"]["rooms"]) > 0
