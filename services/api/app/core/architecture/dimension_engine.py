"""AutoDimensionEngine — derives DimensionEntity list from an ArchitectureProject.

DimensionEntities are stored inline on the project (they version with it) and
consumed by the SVG renderer, DXF exporter, and PDF sheet exporter to render
working-drawing dimension layers.

Three layers produced:
  dim-external  — site boundary dimensions (width + depth)
  dim-room      — per-room width and depth at room corners
  dim-opening   — door/window widths (labelled at the opening)
"""

from __future__ import annotations

from app.core.models.project import (
    ArchitectureProject,
    DimensionEntity,
    StairEntity,
)
from app.core.units import UnitConversionService


class AutoDimensionEngine:
    """Derives all working-drawing dimension annotations from a validated project."""

    @staticmethod
    def derive(project: ArchitectureProject) -> list[DimensionEntity]:
        fmt = lambda v: UnitConversionService.format_dimension(v, project.units)
        dims: list[DimensionEntity] = []

        # ── Site boundary ──────────────────────────────────────────────────────
        w = project.site.width
        d = project.site.depth

        dims.append(DimensionEntity(
            id="dim-site-width",
            dim_type="external",
            p1=[0.0, d],
            p2=[w, d],
            value=w,
            label=fmt(w),
            layer="dim-external",
        ))
        dims.append(DimensionEntity(
            id="dim-site-depth",
            dim_type="external",
            p1=[0.0, 0.0],
            p2=[0.0, d],
            value=d,
            label=fmt(d),
            layer="dim-external",
        ))

        # ── Per-room dimensions ────────────────────────────────────────────────
        for room in project.rooms:
            # Width: top edge of room, left to right
            dims.append(DimensionEntity(
                id=f"dim-{room.id}-w",
                dim_type="room",
                p1=[room.x, room.y],
                p2=[room.x + room.width, room.y],
                value=room.width,
                label=fmt(room.width),
                layer="dim-room",
            ))
            # Depth: right edge, top to bottom
            dims.append(DimensionEntity(
                id=f"dim-{room.id}-d",
                dim_type="room",
                p1=[room.x + room.width, room.y],
                p2=[room.x + room.width, room.y + room.depth],
                value=room.depth,
                label=fmt(room.depth),
                layer="dim-room",
            ))

        # ── Door/window openings ───────────────────────────────────────────────
        rooms_by_id = {r.id: r for r in project.rooms}
        for door in project.doors:
            room = rooms_by_id.get(door.room_id)
            if room is None:
                continue
            dims.append(DimensionEntity(
                id=f"dim-{door.id}",
                dim_type="opening",
                p1=[0.0, 0.0],   # renderer resolves from door + room coords
                p2=[door.width, 0.0],
                value=door.width,
                label=fmt(door.width),
                layer="dim-opening",
            ))

        # ── Stair dimensions ───────────────────────────────────────────────────
        for stair in project.stairs:
            room = rooms_by_id.get(stair.room_id)
            if room is None:
                continue
            run = stair.risers * stair.tread_depth
            dims.append(DimensionEntity(
                id=f"dim-{stair.id}-run",
                dim_type="stair",
                p1=[room.x, room.y],
                p2=[room.x, room.y + run],
                value=run,
                label=f"{stair.risers}R × {fmt(stair.tread_depth)}",
                layer="dim-stair",
            ))

        return dims

    @staticmethod
    def derive_stair_entities(project: ArchitectureProject) -> list[StairEntity]:
        """Generate StairEntity records from stair Rooms if none exist.

        Extends the existing _stair_spec representation: stair Rooms continue to
        drive layout; StairEntities add riser/tread detail for working drawings.
        """
        stair_rooms = [r for r in project.rooms if r.type == "stair"]
        existing_ids = {s.room_id for s in project.stairs}
        new_stairs: list[StairEntity] = list(project.stairs)

        for i, room in enumerate(stair_rooms):
            if room.id in existing_ids:
                continue
            level_to = room.level + 1 if room.level == 0 else room.level
            level_from = room.level
            new_stairs.append(StairEntity(
                id=f"stair-ent-{i}",
                room_id=room.id,
                level_from=level_from,
                level_to=level_to,
            ))
        return new_stairs
