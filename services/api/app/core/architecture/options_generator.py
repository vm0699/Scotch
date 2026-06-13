"""Phase 10 — compact/balanced/spacious design options generator.

Generates 3 DesignOption objects from a single prompt by running the
deterministic generator with different size_modifier values. AI-mode options
always use deterministic generation to keep variants fast and consistent.
"""

from uuid import uuid4

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models import ArchitectureProject
from app.core.models.project import DesignOption

_VARIANTS: list[tuple[str, float, float, str]] = [
    (
        "compact",
        0.82,
        7.8,
        "Efficient proportions — lower construction cost, ideal for tighter sites.",
    ),
    (
        "balanced",
        1.00,
        8.5,
        "Well-proportioned standard layout — the recommended choice for most projects.",
    ),
    (
        "spacious",
        1.20,
        8.2,
        "Generous room sizes — premium proportions for enhanced comfort and liveability.",
    ),
]


def _score(project: ArchitectureProject, base: float) -> float:
    penalized = any("compressed" in w.message.lower() for w in project.warnings)
    return round(max(0.0, base - (0.5 if penalized else 0.0)), 1)


def generate_options(prompt: str, mode: str, settings: object) -> list[DesignOption]:  # noqa: ARG001
    """Return compact/balanced/spacious DesignOption variants for `prompt`.

    The mode/settings parameters are accepted for API consistency but options
    are always generated deterministically (3 AI calls would be slow and
    unpredictable for variant comparison).
    """
    req = parse_prompt(prompt)
    options: list[DesignOption] = []

    for variant, modifier, base_score, tagline in _VARIANTS:
        variant_req = req.model_copy(update={"size_modifier": modifier})
        project, _ = generate_floorplan(variant_req)
        built = sum(r.width * r.depth for r in project.rooms)
        score = _score(project, base_score)
        summary = f"{len(project.rooms)}-room layout, {built:g} ft² built-up. {tagline}"
        options.append(
            DesignOption(
                option_id=f"opt-{variant}-{uuid4().hex[:8]}",
                variant=variant,  # type: ignore[arg-type]
                score=score,
                summary=summary,
                warnings=project.warnings,
                preview=project,
            )
        )

    return options
