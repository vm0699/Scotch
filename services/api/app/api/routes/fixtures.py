"""Phase 42 — Demo project fixtures.

Returns pre-specified demo projects generated fresh on request.
These are used by the dashboard "Load Demo" flow and pilot packages.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models import ArchitectureProject

router = APIRouter(prefix="/fixtures", tags=["fixtures"])

_DEMOS: dict[str, dict] = {
    "2bhk_tn_house": {
        "name": "2BHK Tamil Nadu House",
        "description": "Budget-friendly 2-bedroom house for a family of 4, 30×50 ft east-facing plot, TN style",
        "prompt": "2BHK house for family of 4, 30x50 ft east-facing site, vastu-compliant, budget-friendly, Tamil Nadu style with living room, dining, 2 bedrooms, 2 bathrooms, kitchen, utility",
    },
    "3bhk_villa": {
        "name": "3BHK Premium Villa",
        "description": "Spacious 3-bedroom villa with modern styling on a 40×60 ft site",
        "prompt": "3BHK premium villa, 40x60 ft north-facing site, 2 floors, modern style, 3 bedrooms with attached baths, large living room, open kitchen, utility, car parking",
    },
    "studio_apartment": {
        "name": "Studio Apartment",
        "description": "Compact urban studio with efficient layout on a 20×30 ft footprint",
        "prompt": "studio apartment, 20x30 ft west-facing site, compact open plan, sleeping area, kitchenette, bathroom, 1 floor, urban modern style",
    },
    "small_cafe": {
        "name": "Small Café",
        "description": "Cozy neighbourhood café with seating, counter, kitchen and storage",
        "prompt": "small neighbourhood cafe, 25x40 ft commercial plot, south-facing, seating area for 20, service counter, open kitchen, storage room, 1 floor, modern minimal style",
    },
    "duplex_house": {
        "name": "Duplex House",
        "description": "Compact duplex with independent units on 2 floors, 25×40 ft plot",
        "prompt": "duplex house, 25x40 ft east-facing site, 2 floors, each floor independent 2BHK unit, separate entrances, living room kitchen 2 beds 1 bath per floor, vastu preferred",
    },
}


@router.get("/", summary="List available demo fixtures")
def list_fixtures() -> list[dict]:
    return [{"id": k, **{kk: v for kk, v in meta.items() if kk != "prompt"}} for k, meta in _DEMOS.items()]


@router.get("/{fixture_id}", summary="Generate a demo project from a fixture")
def get_fixture(fixture_id: str) -> ArchitectureProject:
    if fixture_id not in _DEMOS:
        raise HTTPException(
            status_code=404,
            detail=f"Fixture '{fixture_id}' not found. Available: {', '.join(_DEMOS)}",
        )
    meta = _DEMOS[fixture_id]
    req = parse_prompt(meta["prompt"])
    project, _ = generate_floorplan(req)
    # Override the project name to the fixture name
    return project.model_copy(update={"name": meta["name"]})
