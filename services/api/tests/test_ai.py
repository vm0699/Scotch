"""Phase 9 — AI provider integration tests.

Stage 9.6: schema_repair, factory, HybridProvider, endpoint mocking,
settings endpoint. No real API calls — all AI providers are mocked.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.ai.factory import get_provider
from app.core.ai.provider import (
    AnthropicProvider,
    DeterministicProvider,
    HybridProvider,
    OpenAICompatibleProvider,
)
from app.core.ai.schema_repair import _extract_json, _strip_fences, repair_and_parse
from app.core.architecture.sample_factory import create_sample_project
from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sample():
    return create_sample_project()


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── MockSettings helper ───────────────────────────────────────────────────────


class _MockSettings:
    generation_mode = "deterministic"
    ai_provider = "anthropic"
    anthropic_api_key = ""
    anthropic_model = "claude-sonnet-4-6"
    openai_api_key = ""
    openai_base_url = "https://api.openai.com/v1"
    openai_model = "gpt-4o"


# ── _strip_fences ─────────────────────────────────────────────────────────────


class TestStripFences:
    def test_plain_json_unchanged(self, sample):
        raw = sample.model_dump_json()
        assert _strip_fences(raw) == raw.strip()

    def test_json_fenced_with_lang(self, sample):
        raw = sample.model_dump_json()
        assert _strip_fences(f"```json\n{raw}\n```") == raw.strip()

    def test_json_fenced_no_lang(self, sample):
        raw = sample.model_dump_json()
        assert _strip_fences(f"```\n{raw}\n```") == raw.strip()


# ── _extract_json ─────────────────────────────────────────────────────────────


class TestExtractJson:
    def test_clean_json_object(self, sample):
        data = _extract_json(sample.model_dump_json())
        assert data["id"] == sample.id

    def test_json_embedded_in_prose(self, sample):
        raw = "Here is the design: " + sample.model_dump_json() + " That is all."
        data = _extract_json(raw)
        assert data["id"] == sample.id

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object"):
            _extract_json("no json here at all")

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError):
            _extract_json('{"key": "value", missing_quote}')


# ── repair_and_parse ──────────────────────────────────────────────────────────


class TestRepairAndParse:
    def test_clean_json_round_trips(self, sample):
        project = repair_and_parse(sample.model_dump_json())
        assert project.id == sample.id
        assert len(project.rooms) == len(sample.rooms)

    def test_fenced_json_round_trips(self, sample):
        fenced = f"```json\n{sample.model_dump_json()}\n```"
        assert repair_and_parse(fenced).id == sample.id

    def test_invalid_pydantic_raises(self):
        bad = json.dumps({"id": "test", "not_a_valid_field": True})
        with pytest.raises(ValueError, match="schema validation"):
            repair_and_parse(bad)

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            repair_and_parse("Three bedrooms and two baths on a corner lot.")


# ── get_provider factory ──────────────────────────────────────────────────────


class TestGetProvider:
    def test_deterministic_mode(self):
        assert isinstance(get_provider("deterministic", _MockSettings()), DeterministicProvider)

    def test_ai_mode_no_key_raises(self):
        with pytest.raises(ValueError, match="API key"):
            get_provider("ai", _MockSettings())

    def test_ai_mode_anthropic_key(self):
        s = _MockSettings()
        s.anthropic_api_key = "sk-ant-test"
        assert isinstance(get_provider("ai", s), AnthropicProvider)

    def test_ai_mode_openai_key(self):
        s = _MockSettings()
        s.openai_api_key = "sk-test"
        assert isinstance(get_provider("ai", s), OpenAICompatibleProvider)

    def test_hybrid_no_key_falls_back_to_deterministic(self):
        assert isinstance(get_provider("hybrid", _MockSettings()), DeterministicProvider)

    def test_hybrid_with_key(self):
        s = _MockSettings()
        s.anthropic_api_key = "sk-ant-test"
        assert isinstance(get_provider("hybrid", s), HybridProvider)

    def test_unknown_mode_falls_back_to_deterministic(self):
        assert isinstance(get_provider("unknown_xyz", _MockSettings()), DeterministicProvider)


# ── HybridProvider ────────────────────────────────────────────────────────────


class TestHybridProvider:
    def test_returns_ai_result_on_success(self, sample):
        ai_mock = MagicMock()
        ai_mock.generate_project.return_value = (sample, "AI summary")
        project, summary = HybridProvider(ai_mock).generate_project("test prompt")
        assert summary == "AI summary"
        assert project.id == sample.id

    def test_falls_back_to_deterministic_on_ai_failure(self):
        ai_mock = MagicMock()
        ai_mock.generate_project.side_effect = ValueError("AI failed")
        project, summary = HybridProvider(ai_mock).generate_project(
            "Design a simple 2BHK apartment on a 30x50 ft site."
        )
        assert len(project.rooms) > 0
        fallback_msgs = [w.message for w in project.warnings]
        assert any("fallback" in m.lower() for m in fallback_msgs)

    def test_fallback_warning_has_info_severity(self):
        ai_mock = MagicMock()
        ai_mock.generate_project.side_effect = RuntimeError("network error")
        project, _ = HybridProvider(ai_mock).generate_project(
            "Design a simple 2BHK apartment on a 30x50 ft site."
        )
        fallback_warnings = [w for w in project.warnings if "fallback" in w.message.lower()]
        assert len(fallback_warnings) >= 1
        assert fallback_warnings[0].severity == "info"


# ── /generate/from-prompt endpoint ───────────────────────────────────────────


class TestGenerateEndpoint:
    def test_deterministic_default(self, client):
        resp = client.post("/generate/from-prompt", json={"prompt": "Design a simple 2BHK apartment."})
        assert resp.status_code == 200
        assert len(resp.json()["project"]["rooms"]) > 0

    def test_deterministic_explicit_mode(self, client):
        resp = client.post(
            "/generate/from-prompt",
            json={"prompt": "Design a studio apartment.", "mode": "deterministic"},
        )
        assert resp.status_code == 200

    def test_invalid_mode_rejected_422(self, client):
        resp = client.post("/generate/from-prompt", json={"prompt": "test", "mode": "invalid"})
        assert resp.status_code == 422

    def test_ai_mode_with_mock_provider_returns_200(self, client, sample):
        mock_provider = MagicMock()
        mock_provider.generate_project.return_value = (sample, "AI mocked summary")
        with patch("app.api.routes.generate.get_provider", return_value=mock_provider):
            resp = client.post("/generate/from-prompt", json={"prompt": "2BHK", "mode": "ai"})
        assert resp.status_code == 200
        assert resp.json()["summary"] == "AI mocked summary"

    def test_ai_mode_provider_failure_returns_500(self, client):
        mock_provider = MagicMock()
        mock_provider.generate_project.side_effect = ValueError("No API key configured")
        with patch("app.api.routes.generate.get_provider", return_value=mock_provider):
            resp = client.post("/generate/from-prompt", json={"prompt": "2BHK", "mode": "ai"})
        assert resp.status_code == 500

    def test_hybrid_mode_with_mock_provider(self, client, sample):
        mock_provider = MagicMock()
        mock_provider.generate_project.return_value = (sample, "Hybrid summary")
        with patch("app.api.routes.generate.get_provider", return_value=mock_provider):
            resp = client.post("/generate/from-prompt", json={"prompt": "2BHK", "mode": "hybrid"})
        assert resp.status_code == 200

    def test_ai_mode_factory_error_no_key_returns_500(self, client):
        # No AI key in env → factory raises ValueError → route returns 500
        with patch("app.api.routes.generate.get_settings") as mock_settings:
            mock_settings.return_value = _MockSettings()
            resp = client.post("/generate/from-prompt", json={"prompt": "2BHK", "mode": "ai"})
        assert resp.status_code == 500


# ── /settings/generation endpoint ────────────────────────────────────────────


class TestSettingsEndpoint:
    def test_returns_200_with_required_fields(self, client):
        resp = client.get("/settings/generation")
        assert resp.status_code == 200
        data = resp.json()
        assert "mode" in data
        assert "provider" in data
        assert "anthropic_configured" in data
        assert "openai_configured" in data

    def test_configured_fields_are_booleans(self, client):
        data = client.get("/settings/generation").json()
        assert isinstance(data["anthropic_configured"], bool)
        assert isinstance(data["openai_configured"], bool)

    def test_api_keys_never_echoed(self, client):
        body = client.get("/settings/generation").text
        assert "api_key" not in body.lower()
        assert "sk-" not in body

    def test_default_mode_is_deterministic(self, client):
        data = client.get("/settings/generation").json()
        # Default env has no overrides → deterministic
        assert data["mode"] == "deterministic"
