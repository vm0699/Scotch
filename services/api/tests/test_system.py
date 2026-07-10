"""System detection tests — GET /system/integrations.

The endpoint must always return 200 with a status for every integration, even
when an individual probe fails. Detection itself is OS-specific, so we
monkeypatch the per-app probes rather than asserting on the real machine.
"""

from fastapi.testclient import TestClient

from app.core.system import detect as detect_mod
from app.main import app

client = TestClient(app)

_KEYS = {"sketchup", "revit", "rhino", "blender"}


def test_endpoint_returns_status_for_every_integration() -> None:
    r = client.get("/system/integrations")
    assert r.status_code == 200
    body = r.json()
    assert "platform" in body
    assert set(body["integrations"]) == _KEYS
    for status in body["integrations"].values():
        assert "installed" in status
        assert isinstance(status["installed"], bool)


def test_all_found(monkeypatch) -> None:
    monkeypatch.setattr(detect_mod, "_is_windows", lambda: True)
    found = {"installed": True, "version": "2024", "detail": "x"}
    monkeypatch.setattr(detect_mod, "_PROBES", {k: (lambda: dict(found)) for k in _KEYS})
    result = detect_mod.detect_integrations()
    assert result["platform"] == "windows"
    assert all(s["installed"] for s in result["integrations"].values())


def test_none_found(monkeypatch) -> None:
    monkeypatch.setattr(detect_mod, "_is_windows", lambda: True)
    monkeypatch.setattr(
        detect_mod, "_PROBES", {k: (lambda: {"installed": False, "version": None, "detail": None}) for k in _KEYS}
    )
    result = detect_mod.detect_integrations()
    assert not any(s["installed"] for s in result["integrations"].values())


def test_probe_raising_never_500(monkeypatch) -> None:
    """A probe that explodes must degrade to installed:False, not crash."""
    monkeypatch.setattr(detect_mod, "_is_windows", lambda: True)

    def boom():
        raise RuntimeError("registry access denied")

    monkeypatch.setattr(detect_mod, "_PROBES", {k: boom for k in _KEYS})
    result = detect_mod.detect_integrations()
    assert all(s["installed"] is False for s in result["integrations"].values())


def test_non_windows_reports_unsupported(monkeypatch) -> None:
    monkeypatch.setattr(detect_mod, "_is_windows", lambda: False)
    monkeypatch.setattr(detect_mod.sys, "platform", "linux")
    result = detect_mod.detect_integrations()
    assert result["platform"] == "linux"
    assert all(s["installed"] is False for s in result["integrations"].values())
