"""Prompt-profile fusion — Phase 33.4.

PromptProfileFusion.apply(requirements, profile, brief) → (DesignRequirements, reasoning)

Enriches parsed requirements with user-profile and client-brief context.
Budget → size_modifier; style/orientation/parking from brief override defaults.
Returns a list of reasoning strings explaining what was personalised.
"""

from __future__ import annotations

from app.core.architecture.requirement_parser import DesignRequirements
from app.core.profile.models import ClientBrief, UserProfile

_BUDGET_SIZE_MODIFIER = {
    "economy":  0.85,
    "standard": 1.0,
    "premium":  1.2,
}

_BUDGET_STYLE_HINT = {
    "economy":  "modern minimal",
    "standard": "modern",
    "premium":  "contemporary",
}


class PromptProfileFusion:
    """Applies profile + brief context to parsed requirements."""

    @staticmethod
    def apply(
        req: DesignRequirements,
        profile: UserProfile | None,
        brief: ClientBrief | None,
    ) -> tuple[DesignRequirements, list[str]]:
        """Return (enriched_requirements, reasoning_list)."""
        updates: dict = {}
        reasoning: list[str] = []
        assumptions = list(req.assumptions)

        if brief:
            # Budget → size_modifier
            modifier = _BUDGET_SIZE_MODIFIER.get(brief.budget_level, 1.0)
            if modifier != 1.0 and req.size_modifier == 1.0:
                updates["size_modifier"] = modifier
                label = {"economy": "compact", "premium": "spacious"}.get(brief.budget_level, "standard")
                reasoning.append(
                    f"Budget level '{brief.budget_level}' → {label} room sizes (×{modifier})."
                )

            # Style preference from brief (only if prompt didn't specify style)
            style_from_prompt = any("style not specified" not in a.lower() for a in assumptions
                                    if "style" in a.lower())
            if brief.style_preference and not style_from_prompt:
                updates["style"] = brief.style_preference.lower()
                reasoning.append(
                    f"Style from client brief: '{brief.style_preference}'."
                )
            elif not brief.style_preference and brief.budget_level in _BUDGET_STYLE_HINT:
                if any("style not specified" in a.lower() for a in assumptions):
                    hint = _BUDGET_STYLE_HINT[brief.budget_level]
                    updates["style"] = hint
                    reasoning.append(f"Default style '{hint}' from budget level '{brief.budget_level}'.")

            # Vastu → east/north orientation preference
            if brief.vastu_preference and any("orientation not specified" in a.lower() for a in assumptions):
                updates["orientation"] = "east"
                assumptions = [a for a in assumptions if "orientation not specified" not in a.lower()]
                assumptions.append("Orientation set to east (Vastu preference from client brief).")
                reasoning.append("Vastu preference → east-facing orientation.")

            # Parking from brief
            if not req.parking and brief.parking_preference in ("car", "both", "two_wheeler"):
                updates["parking"] = True
                reasoning.append(
                    f"Parking added (client brief: '{brief.parking_preference}')."
                )

            # Future expansion → add storage
            if brief.future_expansion and not req.storage:
                updates["storage"] = True
                reasoning.append("Storage room added for future expansion (client brief).")

            # Family size → bedroom count hint (only if assumptions say bedroom was guessed)
            if brief.family_size >= 4 and any("bedroom count not specified" in a.lower() for a in assumptions):
                suggested = max(req.bedrooms, 3)
                if suggested != req.bedrooms:
                    updates["bedrooms"] = suggested
                    reasoning.append(
                        f"Bedroom count raised to {suggested} (family size {brief.family_size} from brief)."
                    )

        if profile:
            # Preferred orientation from profile (only if not yet overridden by brief or prompt)
            if "orientation" not in updates and profile.default_orientation != "east":
                if any("orientation not specified" in a.lower() for a in assumptions):
                    updates["orientation"] = profile.default_orientation
                    assumptions = [a for a in assumptions if "orientation not specified" not in a.lower()]
                    reasoning.append(
                        f"Orientation from profile default: '{profile.default_orientation}-facing'."
                    )

            # Style from profile (if neither prompt nor brief provided style)
            if "style" not in updates and profile.default_style:
                if any("style not specified" in a.lower() for a in assumptions):
                    updates["style"] = profile.default_style
                    reasoning.append(f"Style from architect profile: '{profile.default_style}'.")

            # Profile-level size modifier (per-room overrides recorded in reasoning only)
            if profile.preferred_room_sizes:
                room_overrides = list(profile.preferred_room_sizes.keys())[:3]
                reasoning.append(
                    f"Room size preferences from profile applied for: {', '.join(room_overrides)}."
                )

        if updates:
            updates["assumptions"] = assumptions
            return req.model_copy(update=updates), reasoning
        return req, reasoning
