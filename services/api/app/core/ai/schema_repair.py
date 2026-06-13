"""
Parse and validate raw AI text output into a valid ArchitectureProject.

Handles:
  - Markdown code fences (```json ... ```)
  - JSON embedded in surrounding prose
  - Pydantic v2 schema validation errors → ValueError
  - Layout validation failures → ValueError
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.models import ArchitectureProject
from app.core.validation import validate_project


def repair_and_parse(raw: str) -> ArchitectureProject:
    """Strip fences, extract JSON, validate schema + layout.

    Raises ValueError with a descriptive message on any failure so callers
    can decide to fall back to the deterministic generator.
    """
    cleaned = _strip_fences(raw.strip())
    data = _extract_json(cleaned)

    try:
        project = ArchitectureProject.model_validate(data)
    except Exception as exc:
        raise ValueError(f"AI output failed schema validation: {exc}") from exc

    result = validate_project(project)
    if not result.valid:
        raise ValueError(
            f"AI output failed layout validation: {'; '.join(result.errors)}"
        )

    return project


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _extract_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in AI output.")

    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError as exc:
                    raise ValueError(f"AI output contains malformed JSON: {exc}") from exc

    raise ValueError("AI output contains an unterminated JSON object.")
