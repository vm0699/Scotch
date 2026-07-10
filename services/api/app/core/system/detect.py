"""Detect installed desktop host apps for the Scotch integrations.

Each probe checks the Windows registry first (authoritative install records)
and falls back to globbing the standard ``Program Files`` install locations.
Every probe is wrapped so it *never raises* — a failed/odd probe simply reports
``installed: False``. Detection is Windows-only today; on other platforms every
app reports not-installed and ``platform`` reflects the real OS so the UI can
say "detection unsupported here".

Public surface:
    detect_integrations() -> dict  # {"platform": str, "integrations": {...}}
"""

from __future__ import annotations

import glob
import os
import re
import sys
from typing import Callable

# Each value is {"installed": bool, "version": str | None, "detail": str | None}.
IntegrationStatus = dict[str, object]


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _program_files_dirs() -> list[str]:
    """Candidate Program Files roots (64- and 32-bit)."""
    roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("ProgramW6432"),
    ]
    return [r for r in dict.fromkeys(roots) if r]  # dedupe, drop None


def _registry_subkeys(root, path: str) -> list[str]:
    """Return the immediate subkey names under HKLM\\<path>, or []."""
    import winreg  # local import: only available on Windows

    names: list[str] = []
    try:
        with winreg.OpenKey(root, path) as key:
            count = winreg.QueryInfoKey(key)[0]
            for i in range(count):
                names.append(winreg.EnumKey(key, i))
    except OSError:
        pass
    return names


def _first_glob(patterns: list[str]) -> str | None:
    for pattern in patterns:
        for match in glob.glob(pattern):
            return match
    return None


def _year_from(text: str) -> str | None:
    """Pull a 4-digit year (20xx) or a version-ish token out of a path/name."""
    m = re.search(r"(20\d{2})", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d+\.\d+)", text)
    return m.group(1) if m else None


# ── Per-app probes ──────────────────────────────────────────────────────────────


def _detect_revit() -> IntegrationStatus:
    import winreg

    for name in _registry_subkeys(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Autodesk\Revit"):
        if re.search(r"\d{4}", name):
            return {"installed": True, "version": _year_from(name), "detail": f"Autodesk Revit {name}"}
    hit = _first_glob([os.path.join(pf, "Autodesk", "Revit *", "Revit.exe") for pf in _program_files_dirs()])
    if hit:
        return {"installed": True, "version": _year_from(hit), "detail": hit}
    return {"installed": False, "version": None, "detail": None}


def _detect_sketchup() -> IntegrationStatus:
    import winreg

    for name in _registry_subkeys(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\SketchUp"):
        if re.search(r"SketchUp", name):
            return {"installed": True, "version": _year_from(name), "detail": name}
    hit = _first_glob(
        [os.path.join(pf, "SketchUp", "SketchUp *", "SketchUp.exe") for pf in _program_files_dirs()]
    )
    if hit:
        return {"installed": True, "version": _year_from(hit), "detail": hit}
    return {"installed": False, "version": None, "detail": None}


def _detect_rhino() -> IntegrationStatus:
    import winreg

    for name in _registry_subkeys(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\McNeel\Rhinoceros"):
        if re.search(r"\d", name):
            return {"installed": True, "version": _year_from(name), "detail": f"Rhino {name}"}
    hit = _first_glob(
        [os.path.join(pf, "Rhino *", "System", "Rhino.exe") for pf in _program_files_dirs()]
        + [os.path.join(pf, "Rhinoceros *", "System", "Rhino.exe") for pf in _program_files_dirs()]
    )
    if hit:
        return {"installed": True, "version": _year_from(hit), "detail": hit}
    return {"installed": False, "version": None, "detail": None}


def _detect_blender() -> IntegrationStatus:
    import winreg

    for name in _registry_subkeys(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlenderFoundation"):
        return {"installed": True, "version": _year_from(name), "detail": f"Blender {name}"}
    hit = _first_glob(
        [os.path.join(pf, "Blender Foundation", "Blender *", "blender.exe") for pf in _program_files_dirs()]
    )
    if hit:
        return {"installed": True, "version": _year_from(hit), "detail": hit}
    return {"installed": False, "version": None, "detail": None}


# Registry of probes keyed by integration id. Monkeypatch entries in tests.
_PROBES: dict[str, Callable[[], IntegrationStatus]] = {
    "sketchup": _detect_sketchup,
    "revit": _detect_revit,
    "rhino": _detect_rhino,
    "blender": _detect_blender,
}

_NOT_INSTALLED: IntegrationStatus = {"installed": False, "version": None, "detail": None}


def detect_integrations() -> dict:
    """Report installed host apps. Never raises; safe to call on any platform."""
    platform_name = "windows" if _is_windows() else sys.platform
    integrations: dict[str, IntegrationStatus] = {}

    for key, probe in _PROBES.items():
        if not _is_windows():
            integrations[key] = {
                "installed": False,
                "version": None,
                "detail": "detection supported on Windows only",
            }
            continue
        try:
            integrations[key] = probe()
        except Exception:  # pragma: no cover - defensive; a probe must never break the endpoint
            integrations[key] = dict(_NOT_INSTALLED)

    return {"platform": platform_name, "integrations": integrations}
