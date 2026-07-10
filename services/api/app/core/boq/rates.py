"""Default rate table for BOQ generation (Phase 31.5).

All rates are in INR per unit as listed. They are editable via the UI / prompt;
missing rates (rate=0) are surfaced as warnings and excluded from totals.
"""

from __future__ import annotations

from app.core.models.project import RateEntry


# Default residential rates (INR, sqft-based unless otherwise noted)
DEFAULT_RATES: list[RateEntry] = [
    # Flooring
    RateEntry(category="flooring", item="tile_supply",         unit="sqft",  rate=80.0,   source="market_estimate"),
    RateEntry(category="flooring", item="tile_laying",         unit="sqft",  rate=40.0,   source="market_estimate"),
    RateEntry(category="flooring", item="marble_supply",       unit="sqft",  rate=200.0,  source="market_estimate"),
    RateEntry(category="flooring", item="marble_laying",       unit="sqft",  rate=60.0,   source="market_estimate"),
    RateEntry(category="flooring", item="wood_flooring",       unit="sqft",  rate=150.0,  source="market_estimate"),
    # Wall tile (bathrooms / kitchens)
    RateEntry(category="wall_tile", item="tile_supply",        unit="sqft",  rate=70.0,   source="market_estimate"),
    RateEntry(category="wall_tile", item="tile_laying",        unit="sqft",  rate=45.0,   source="market_estimate"),
    # Paint
    RateEntry(category="paint",    item="interior_paint",      unit="sqft",  rate=18.0,   source="market_estimate"),
    RateEntry(category="paint",    item="exterior_paint",      unit="sqft",  rate=22.0,   source="market_estimate"),
    RateEntry(category="paint",    item="ceiling_paint",       unit="sqft",  rate=15.0,   source="market_estimate"),
    # Doors & windows
    RateEntry(category="doors",    item="interior_door",       unit="nos",   rate=8000.0, source="market_estimate"),
    RateEntry(category="doors",    item="main_door",           unit="nos",   rate=20000.0, source="market_estimate"),
    RateEntry(category="windows",  item="upvc_window",         unit="nos",   rate=6000.0, source="market_estimate"),
    RateEntry(category="windows",  item="aluminium_window",    unit="nos",   rate=4500.0, source="market_estimate"),
    # Plumbing (per fixture)
    RateEntry(category="plumbing", item="wc",                  unit="nos",   rate=5000.0, source="market_estimate"),
    RateEntry(category="plumbing", item="basin",               unit="nos",   rate=3000.0, source="market_estimate"),
    RateEntry(category="plumbing", item="sink",                unit="nos",   rate=3500.0, source="market_estimate"),
    RateEntry(category="plumbing", item="shower",              unit="nos",   rate=4000.0, source="market_estimate"),
    # Electrical (per point)
    RateEntry(category="electrical", item="light_point",       unit="nos",   rate=1200.0, source="market_estimate"),
    RateEntry(category="electrical", item="socket_point",      unit="nos",   rate=1500.0, source="market_estimate"),
    RateEntry(category="electrical", item="switch_point",      unit="nos",   rate=800.0,  source="market_estimate"),
    RateEntry(category="electrical", item="ac_point",          unit="nos",   rate=3500.0, source="market_estimate"),
]


class RateTable:
    """Mutable rate table layered over defaults.

    Override rates via `set(category, item, rate)`.
    Retrieve with `get(category, item)` → float (0.0 if missing).
    """

    def __init__(self, overrides: list[RateEntry] | None = None) -> None:
        self._rates: dict[tuple[str, str], RateEntry] = {
            (e.category, e.item): e for e in DEFAULT_RATES
        }
        for entry in (overrides or []):
            self._rates[(entry.category, entry.item)] = entry

    def get(self, category: str, item: str) -> float:
        entry = self._rates.get((category, item))
        return entry.rate if entry else 0.0

    def set(self, category: str, item: str, rate: float, unit: str = "", source: str = "manual") -> None:
        key = (category, item)
        existing = self._rates.get(key)
        self._rates[key] = RateEntry(
            category=category,
            item=item,
            unit=unit or (existing.unit if existing else "nos"),
            rate=rate,
            source=source,
        )

    def get_entry(self, category: str, item: str) -> RateEntry | None:
        return self._rates.get((category, item))

    def all_entries(self) -> list[RateEntry]:
        return list(self._rates.values())

    @classmethod
    def from_project(cls, rate_entries: list[RateEntry]) -> "RateTable":
        return cls(overrides=rate_entries)
