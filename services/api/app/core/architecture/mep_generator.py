"""MEP Generator — room-type-aware placement of plumbing, electrical, lighting,
and AC service points with conceptual advisory routes.

All output is clearly flagged as conceptual/advisory (confidence scores,
needs_review=True where appropriate). NOT engineering-certified.
Professional review is required before construction.

Placement logic:
- Reads templates from services/api/app/data/mep_templates/
- Applies room-type → fixtures mapping
- Preserves user_override points on regeneration
- Emits warnings for wet-area grouping, review requirements

Usage:
    from app.core.architecture.mep_generator import MEPGenerator
    mep = MEPGenerator.generate(project, systems=["plumbing", "electrical", "lighting", "ac"])
    project = project.model_copy(update={"mep_plan": mep})
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.models.project import (
    ACPlan,
    ArchitectureProject,
    ElectricalPlan,
    LightingPlan,
    MEPPlan,
    PlumbingPlan,
    Room,
    ServicePoint,
    ServiceRoute,
)

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "data" / "mep_templates"


def _load_template(name: str) -> dict[str, Any]:
    path = _TEMPLATES_DIR / name
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def _room_centroid(room: Room) -> tuple[float, float]:
    return room.x + room.width / 2, room.y + room.depth / 2


def _wall_mid_x_y(room: Room, wall: str, offset_from_corner: float = 2.0) -> tuple[float, float]:
    """Return a point on the named wall, offset from the start corner."""
    off = min(offset_from_corner, room.width / 2 if wall in ("north", "south") else room.depth / 2)
    if wall == "north":
        return round(room.x + off, 2), round(room.y + 0.25, 2)
    if wall == "south":
        return round(room.x + off, 2), round(room.y + room.depth - 0.25, 2)
    if wall == "west":
        return round(room.x + 0.25, 2), round(room.y + off, 2)
    # east
    return round(room.x + room.width - 0.25, 2), round(room.y + off, 2)


# ── Plumbing ─────────────────────────────────────────────────────────────────


def _generate_plumbing(
    project: ArchitectureProject,
    tmpl: dict[str, Any],
    existing: PlumbingPlan,
) -> PlumbingPlan:
    room_fixtures: dict[str, list[dict]] = tmpl.get("room_fixtures", {})
    wet_rooms: list[str] = tmpl.get("wet_rooms", [])
    confidence: float = tmpl.get("confidence", 0.8)
    warnings: list[str] = list(tmpl.get("warnings", []))

    # Preserve user overrides
    override_ids = {p.id for p in existing.points if p.user_override}
    new_points: list[ServicePoint] = [p for p in existing.points if p.user_override]
    new_routes: list[ServiceRoute] = []

    wet_room_objects: list[Room] = []

    for room in project.rooms:
        rtype = room.type
        fixtures = room_fixtures.get(rtype, [])
        if rtype in wet_rooms:
            wet_room_objects.append(room)
        for i, fix in enumerate(fixtures):
            pid = f"p-{room.id}-{fix['kind']}-{i}"
            if pid in override_ids:
                continue
            x = round(room.x + fix["x_frac"] * room.width, 2)
            y = round(room.y + fix["y_frac"] * room.depth, 2)
            new_points.append(ServicePoint(
                id=pid,
                system="plumbing",
                kind=fix["kind"],
                room_id=room.id,
                x=x,
                y=y,
                mount_height=fix.get("mount_height", 0.0),
                confidence=confidence,
                needs_review=True,
                label=fix.get("label", fix["kind"]),
            ))

    # Advisory routes: simple horizontal line from first wet-room centroid to last
    if len(wet_room_objects) >= 2:
        sorted_wet = sorted(wet_room_objects, key=lambda r: (r.y, r.x))
        supply_polyline = [[_room_centroid(r)[0], _room_centroid(r)[1]] for r in sorted_wet]
        drain_polyline = [[_room_centroid(r)[0], _room_centroid(r)[1] + 0.3] for r in sorted_wet]
        new_routes = [
            ServiceRoute(
                id="pr-supply-main",
                system="plumbing",
                polyline=supply_polyline,
                kind=tmpl.get("route_kind_supply", "supply"),
                confidence=tmpl.get("route_confidence", 0.65),
                needs_review=True,
            ),
            ServiceRoute(
                id="pr-drain-main",
                system="plumbing",
                polyline=drain_polyline,
                kind=tmpl.get("route_kind_drain", "drain"),
                confidence=tmpl.get("route_confidence", 0.65),
                needs_review=True,
            ),
        ]

    if len(wet_room_objects) > 2:
        warnings.append(
            f"Advisory: {len(wet_room_objects)} wet areas detected — consider grouping to reduce pipe runs."
        )

    return PlumbingPlan(
        points=new_points,
        routes=new_routes,
        warnings=warnings,
        confidence=confidence,
        needs_review=True,
    )


# ── Electrical ───────────────────────────────────────────────────────────────


def _generate_electrical(
    project: ArchitectureProject,
    tmpl: dict[str, Any],
    existing: ElectricalPlan,
) -> ElectricalPlan:
    room_defaults: dict[str, dict] = tmpl.get("room_defaults", {})
    confidence: float = tmpl.get("confidence", 0.8)
    sw_h: float = tmpl.get("mount_height_switch", 4.0)
    sk_h: float = tmpl.get("mount_height_socket", 1.25)
    warnings: list[str] = list(tmpl.get("warnings", []))

    override_ids = {p.id for p in existing.points if p.user_override}
    new_points: list[ServicePoint] = [p for p in existing.points if p.user_override]
    new_routes: list[ServiceRoute] = []

    for room in project.rooms:
        rtype = room.type
        cfg = room_defaults.get(rtype)
        if cfg is None:
            cfg = room_defaults.get("bedroom", {"switches": 1, "sockets": 2,
                                                 "switch_wall": "north", "socket_walls": ["east"]})

        # Switch — placed near door on switch_wall
        sw_wall = cfg.get("switch_wall", "north")
        sid = f"e-sw-{room.id}"
        if sid not in override_ids:
            sx, sy = _wall_mid_x_y(room, sw_wall, offset_from_corner=1.0)
            new_points.append(ServicePoint(
                id=sid, system="electrical", kind="switch", room_id=room.id,
                x=sx, y=sy, mount_height=sw_h, confidence=confidence,
                needs_review=False, label="Switch",
            ))

        # Sockets
        socket_walls: list[str] = cfg.get("socket_walls", ["east"])
        n_sockets: int = cfg.get("sockets", 2)
        for i, wall in enumerate(socket_walls[:n_sockets]):
            skid = f"e-sk-{room.id}-{i}"
            if skid not in override_ids:
                skx, sky = _wall_mid_x_y(room, wall, offset_from_corner=1.5 + i * 1.2)
                new_points.append(ServicePoint(
                    id=skid, system="electrical", kind="socket", room_id=room.id,
                    x=skx, y=sky, mount_height=sk_h, confidence=confidence,
                    needs_review=False, label="Socket",
                ))

    # Advisory circuit route: spine along site centre
    cx = project.site.width / 2
    new_routes.append(ServiceRoute(
        id="er-main-circuit",
        system="electrical",
        polyline=[[cx, 0.0], [cx, project.site.depth]],
        kind="circuit",
        confidence=tmpl.get("route_confidence", 0.65),
        needs_review=True,
    ))

    return ElectricalPlan(
        points=new_points,
        routes=new_routes,
        warnings=warnings,
        confidence=confidence,
        needs_review=True,
    )


# ── Lighting ─────────────────────────────────────────────────────────────────


def _generate_lighting(
    project: ArchitectureProject,
    tmpl: dict[str, Any],
    existing: LightingPlan,
) -> LightingPlan:
    room_defaults: dict[str, dict] = tmpl.get("room_defaults", {})
    confidence: float = tmpl.get("confidence", 0.88)
    mount_h: float = tmpl.get("mount_height", 9.5)
    warnings: list[str] = list(tmpl.get("warnings", []))

    override_ids = {p.id for p in existing.points if p.user_override}
    new_points: list[ServicePoint] = [p for p in existing.points if p.user_override]

    default_cfg: dict = {"count": 1, "type": "ceiling", "label": "Ceiling Light"}

    for room in project.rooms:
        cfg = room_defaults.get(room.type, default_cfg)
        count: int = cfg.get("count", 1)
        label: str = cfg.get("label", "Ceiling Light")

        for i in range(count):
            lid = f"l-{room.id}-{i}"
            if lid in override_ids:
                continue
            cx, cy = _room_centroid(room)
            if count == 2:
                cx = room.x + room.width * (0.33 if i == 0 else 0.67)
            new_points.append(ServicePoint(
                id=lid, system="lighting", kind=cfg.get("type", "ceiling"), room_id=room.id,
                x=round(cx, 2), y=round(cy, 2), mount_height=mount_h,
                confidence=confidence, needs_review=False, label=label,
            ))

    return LightingPlan(
        points=new_points,
        warnings=warnings,
        confidence=confidence,
        needs_review=False,
    )


# ── AC ───────────────────────────────────────────────────────────────────────


def _generate_ac(
    project: ArchitectureProject,
    tmpl: dict[str, Any],
    existing: ACPlan,
) -> ACPlan:
    eligible: list[str] = tmpl.get("eligible_rooms", ["bedroom", "living"])
    room_defaults: dict[str, dict] = tmpl.get("room_defaults", {})
    confidence: float = tmpl.get("confidence", 0.8)
    offset: float = tmpl.get("offset_from_corner", 2.0)
    wall_order: list[str] = tmpl.get("wall_preference_order", ["north", "east", "west", "south"])
    warnings: list[str] = list(tmpl.get("warnings", []))

    override_ids = {p.id for p in existing.points if p.user_override}
    new_points: list[ServicePoint] = [p for p in existing.points if p.user_override]

    for room in project.rooms:
        if room.type not in eligible:
            continue
        aid = f"ac-{room.id}"
        if aid in override_ids:
            continue
        cfg = room_defaults.get(room.type, {})
        wall = cfg.get("wall", wall_order[0])
        mount_h = cfg.get("mount_height", 7.5)
        label = cfg.get("label", "AC Indoor Unit")
        ax, ay = _wall_mid_x_y(room, wall, offset_from_corner=offset)
        new_points.append(ServicePoint(
            id=aid, system="ac", kind="ac_unit", room_id=room.id,
            x=ax, y=ay, mount_height=mount_h,
            confidence=confidence, needs_review=True, label=label,
        ))

    return ACPlan(
        points=new_points,
        warnings=warnings,
        confidence=confidence,
        needs_review=True,
    )


# ── Public API ────────────────────────────────────────────────────────────────


class MEPGenerator:
    """Generates MEP service points and advisory routes for a validated project."""

    _SYSTEM_TEMPLATES = {
        "plumbing": "plumbing_residential.json",
        "electrical": "electrical_residential.json",
        "lighting": "lighting_residential.json",
        "ac": "ac_residential.json",
    }

    @classmethod
    def generate(
        cls,
        project: ArchitectureProject,
        systems: list[str] | None = None,
    ) -> MEPPlan:
        """Generate (or regenerate) MEP for specified systems.

        Passing systems=None generates all four. Existing user_override points
        are preserved across regeneration.
        """
        if systems is None:
            systems = ["plumbing", "electrical", "lighting", "ac"]

        existing = project.mep_plan

        plumbing = existing.plumbing
        electrical = existing.electrical
        lighting = existing.lighting
        ac = existing.ac

        if "plumbing" in systems:
            tmpl = _load_template(cls._SYSTEM_TEMPLATES["plumbing"])
            plumbing = _generate_plumbing(project, tmpl, existing.plumbing)

        if "electrical" in systems:
            tmpl = _load_template(cls._SYSTEM_TEMPLATES["electrical"])
            electrical = _generate_electrical(project, tmpl, existing.electrical)

        if "lighting" in systems:
            tmpl = _load_template(cls._SYSTEM_TEMPLATES["lighting"])
            lighting = _generate_lighting(project, tmpl, existing.lighting)

        if "ac" in systems:
            tmpl = _load_template(cls._SYSTEM_TEMPLATES["ac"])
            ac = _generate_ac(project, tmpl, existing.ac)

        return MEPPlan(
            plumbing=plumbing,
            electrical=electrical,
            lighting=lighting,
            ac=ac,
            generated=True,
            stale=False,
        )

    @classmethod
    def move_point(
        cls,
        mep_plan: MEPPlan,
        point_id: str,
        new_x: float,
        new_y: float,
    ) -> MEPPlan:
        """Move one service point and mark it as user_override."""
        plan = mep_plan.model_copy(deep=True)
        for sub in (plan.plumbing.points, plan.electrical.points, plan.lighting.points, plan.ac.points):
            for pt in sub:
                if pt.id == point_id:
                    pt.x = new_x
                    pt.y = new_y
                    pt.user_override = True
                    return plan
        raise ValueError(f"Service point '{point_id}' not found in MEP plan")

    @classmethod
    def mark_stale(cls, mep_plan: MEPPlan) -> MEPPlan:
        """Mark the MEP plan as stale (rooms changed after generation)."""
        return mep_plan.model_copy(update={"stale": True})
