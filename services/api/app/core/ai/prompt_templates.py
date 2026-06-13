"""System prompt and user-message templates for AI-driven generation."""

from __future__ import annotations

import json

from app.core.models import ArchitectureProject


def build_messages(user_prompt: str) -> dict[str, str]:
    """Return {"system": ..., "user": ...} for the AI provider call.

    Embeds the full ArchitectureProject JSON schema so the model can produce
    conforming output without guessing field names.
    """
    schema = ArchitectureProject.model_json_schema()
    schema_json = json.dumps(schema, indent=2)

    system = (
        "You are an architecture planning engine for Scotch, an AI-native design platform.\n"
        "Given a building description, return a COMPLETE, valid ArchitectureProject JSON "
        "that strictly conforms to the schema below.\n\n"
        "Critical rules:\n"
        "- Output ONLY raw JSON — no markdown fences, no prose, no explanation.\n"
        "- Every room MUST have: id (unique slug), name, x, y, width, depth.\n"
        "- Default units are 'ft'. site.width and site.depth must be positive.\n"
        "- All rooms must fit within site bounds: x >= 0, y >= 0, "
        "x + width <= site.width, y + depth <= site.depth.\n"
        "- Include at least one door per room and windows on exterior walls.\n"
        "- Set building.floor_height (9–10 ft typical) and building.levels (default 1).\n"
        "- Add ProjectWarning objects for design assumptions made.\n"
        "- notes is a list of plain strings describing assumptions.\n\n"
        f"ArchitectureProject schema:\n{schema_json}"
    )

    return {"system": system, "user": f"Design brief: {user_prompt}"}
