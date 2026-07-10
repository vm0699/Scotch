"""Prompt → DesignRequirements.

Deterministic keyword/regex extraction with smart defaults: anything the
prompt doesn't specify is filled in and recorded in `assumptions`, which the
generator surfaces as editable info warnings — nothing is assumed silently.
"""

import re

from pydantic import BaseModel

from app.core.architecture.defaults import (
    DEFAULT_ORIENTATION,
    DEFAULT_SITE,
    DEFAULT_STYLE,
)

BuildingKind = str  # "apartment" | "villa" | "studio" | "duplex" | "cafe" | "office"


class DesignRequirements(BaseModel):
    site_width: float
    site_depth: float
    orientation: str
    building_kind: BuildingKind
    bedrooms: int
    bathrooms: int
    floors: int
    style: str
    parking: bool
    balcony: bool
    dining: bool
    study: bool
    storage: bool
    assumptions: list[str] = []
    prompt: str
    # Multiplier applied to all default room sizes; 1.0 = standard, <1 = compact, >1 = spacious.
    size_modifier: float = 1.0
    # NBC byelaw parameters (Phase 27.2); defaults match India urban residential zone.
    front_setback: float = 9.84   # 3 m
    side_setback:  float = 4.92   # 1.5 m per side
    rear_setback:  float = 9.84   # 3 m
    max_fsi:       float = 1.5


_SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|')?", re.I)
_ORIENTATION = re.compile(r"\b(north|south|east|west)\s*[- ]?\s*facing\b", re.I)
_BHK = re.compile(r"\b(\d+)\s*bhk\b", re.I)
_BEDROOMS = re.compile(r"\b(\d+)\s*bed(?:room)?s?\b", re.I)
_BATHROOMS = re.compile(r"\b(\d+)\s*(?:bath|bathroom|toilet)s?\b", re.I)
_FLOORS = re.compile(r"\b(\d+)\s*(?:floor|storey|story)s?\b", re.I)

_STYLES = [
    "modern minimal",
    "minimal",
    "modern",
    "contemporary",
    "traditional",
    "industrial",
    "scandinavian",
]


def _detect_kind(text: str) -> BuildingKind | None:
    if re.search(r"\bcaf[eé]\b|\bcoffee\s*shop\b", text):
        return "cafe"
    if re.search(r"\boffice\b|\bworkspace\b|\bworkstations?\b", text):
        return "office"
    if re.search(r"\bstudio\s+apartment\b|\bstudio\b", text):
        return "studio"
    if re.search(r"\bduplex\b", text):
        return "duplex"
    if re.search(r"\bvilla\b|\bbungalow\b", text):
        return "villa"
    if re.search(r"\bapartment\b|\bflat\b|\bhouse\b|\bhome\b|\bbhk\b", text):
        return "apartment"
    return None


def parse_prompt(prompt: str) -> DesignRequirements:
    text = prompt.strip().lower()
    assumptions: list[str] = []

    size = _SIZE.search(text)
    if size:
        site_width, site_depth = float(size.group(1)), float(size.group(2))
    else:
        site_width, site_depth = DEFAULT_SITE
        assumptions.append(
            f"Site size not specified — assumed {site_width:g} × {site_depth:g} ft."
        )

    orientation_match = _ORIENTATION.search(text)
    if orientation_match:
        orientation = orientation_match.group(1)
    else:
        orientation = DEFAULT_ORIENTATION
        assumptions.append(f"Orientation not specified — assumed {orientation}-facing.")

    kind = _detect_kind(text)
    if kind is None:
        kind = "apartment"
        assumptions.append("Building type not specified — assumed an apartment.")

    bhk = _BHK.search(text)
    bedrooms_match = _BEDROOMS.search(text)
    if kind == "studio":
        bedrooms = 0
    elif bhk:
        bedrooms = int(bhk.group(1))
    elif bedrooms_match:
        bedrooms = int(bedrooms_match.group(1))
    elif kind in ("cafe", "office"):
        bedrooms = 0
    else:
        bedrooms = 2
        assumptions.append("Bedroom count not specified — assumed 2.")

    bathrooms_match = _BATHROOMS.search(text)
    if bathrooms_match:
        bathrooms = int(bathrooms_match.group(1))
    elif kind in ("cafe", "office"):
        bathrooms = 1
    elif kind == "studio":
        bathrooms = 1
    else:
        bathrooms = max(1, bedrooms)
        assumptions.append(f"Bathroom count not specified — assumed {bathrooms}.")

    floors_match = _FLOORS.search(text)
    if floors_match:
        floors = max(1, int(floors_match.group(1)))
    elif kind == "duplex":
        floors = 2
    else:
        floors = 1
    if floors > 1:
        assumptions.append(
            "Multi-floor requested — Phase 5 generates the ground floor; upper floors arrive with multi-level layouts."
        )

    style = next((s for s in _STYLES if s in text), None)
    if style is None:
        style = DEFAULT_STYLE
        assumptions.append(f"Style not specified — assumed {style}.")

    parking = bool(re.search(r"\bparking\b|\bgarage\b|\bcar\s*port\b", text))
    balcony = bool(re.search(r"\bbalcon(?:y|ies)\b|\bterrace\b", text))
    dining = bool(re.search(r"\bdining\b", text))
    study = bool(re.search(r"\bstudy\b|\bhome\s*office\b", text))
    storage = bool(re.search(r"\bstorage\b|\bstore\s*room\b|\butility\b", text))

    return DesignRequirements(
        site_width=site_width,
        site_depth=site_depth,
        orientation=orientation,
        building_kind=kind,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        floors=floors,
        style=style,
        parking=parking,
        balcony=balcony,
        dining=dining,
        study=study,
        storage=storage,
        assumptions=assumptions,
        prompt=prompt.strip(),
    )
