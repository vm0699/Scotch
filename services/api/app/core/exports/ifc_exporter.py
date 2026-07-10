"""IFC export for Scotch ArchitectureProject (Phase 22.5).

Hierarchy:
  IfcProject → IfcSite → IfcBuilding
    → IfcBuildingStorey (one per project level)
      → IfcSpace (one per room)

Geometry: IfcExtrudedAreaSolid (box from room bounding rect × floor_height).
Units:    project is in feet; IFC SI requires metres → multiply by FT_TO_M.

Requires: ifcopenshell 0.8+
"""

from __future__ import annotations

from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.owner
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit

from app.core.models import ArchitectureProject

FT_TO_M = 0.3048


def _m(ft: float) -> float:
    return round(ft * FT_TO_M, 6)


def export_ifc(project: ArchitectureProject, path: Path) -> None:
    """Write an IFC4 file from an ArchitectureProject."""
    ifc = ifcopenshell.api.run("project.create_file", version="IFC4")

    # ── Spatial hierarchy — Project must come before unit assignment ───────────
    ifc_project = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcProject",
                                       name=project.name)

    # ── SI units (metres) ──────────────────────────────────────────────────────
    ifcopenshell.api.run("unit.assign_unit", ifc, length={"is_metric": True, "raw": "METRES"})

    # ── Geometric context ──────────────────────────────────────────────────────
    model_ctx = ifcopenshell.api.run("context.add_context", ifc, context_type="Model")
    body_ctx = ifcopenshell.api.run(
        "context.add_context", ifc,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_ctx,
    )
    ifc_site = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcSite", name="Site")
    ifc_building = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcBuilding",
                                        name=project.name)

    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[ifc_site],
                         relating_object=ifc_project)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[ifc_building],
                         relating_object=ifc_site)

    floor_h = _m(project.building.floor_height)
    rooms_by_level: dict[int, list] = {}
    for room in project.rooms:
        rooms_by_level.setdefault(room.level, []).append(room)

    # Build one IfcBuildingStorey per level.
    level_map = {lv.index: lv for lv in project.levels}
    for level_idx in sorted(rooms_by_level):
        lv = level_map.get(level_idx)
        lv_name = lv.name if lv else (f"Floor {level_idx}" if level_idx > 0 else "Ground Floor")
        elev = _m(lv.elevation) if lv else round(level_idx * floor_h, 6)

        storey = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcBuildingStorey",
                                      name=lv_name)
        storey.Elevation = elev
        ifcopenshell.api.run("aggregate.assign_object", ifc, products=[storey],
                             relating_object=ifc_building)

        for room in rooms_by_level[level_idx]:
            _add_space(ifc, body_ctx, storey, room, floor_h, elev)

    # ── Furniture — IfcFurnishingElement per item ─────────────────────────────
    rooms_by_id = {r.id: r for r in project.rooms}
    storey_map: dict[int, object] = {}
    for level_idx in sorted(rooms_by_level):
        lv = level_map.get(level_idx)
        lv_name = lv.name if lv else (f"Floor {level_idx}" if level_idx > 0 else "Ground Floor")
        elev = _m(lv.elevation) if lv else round(level_idx * floor_h, 6)
        # Reuse the storey object — look it up by name (we created them above)
        for entity in ifc.by_type("IfcBuildingStorey"):
            if entity.Name == lv_name:
                storey_map[level_idx] = entity
                break

    for item in project.furniture:
        room = rooms_by_id.get(item.room_id)
        level_idx = room.level if room else 0
        storey = storey_map.get(level_idx)
        if storey is None:
            continue

        furn = ifcopenshell.api.run("root.create_entity", ifc,
                                    ifc_class="IfcFurnishingElement", name=item.label or item.type)
        furn.ObjectType = item.type

        base_z = _m((room.level * project.building.floor_height) if room else 0.0)
        placement = ifc.createIfcLocalPlacement(
            None,
            ifc.createIfcAxis2Placement3D(
                ifc.createIfcCartesianPoint([_m(item.x), _m(item.y), base_z]),
                ifc.createIfcDirection([0.0, 0.0, 1.0]),
                ifc.createIfcDirection([1.0, 0.0, 0.0]),
            ),
        )
        furn.ObjectPlacement = placement

        furn_w = _m(item.width)
        furn_d = _m(item.depth)
        furn_h = _m(item.height)

        profile = ifc.createIfcRectangleProfileDef(
            "AREA", None,
            ifc.createIfcAxis2Placement2D(
                ifc.createIfcCartesianPoint([furn_w / 2, furn_d / 2]),
                ifc.createIfcDirection([1.0, 0.0]),
            ),
            furn_w, furn_d,
        )
        extrusion = ifc.createIfcExtrudedAreaSolid(
            profile,
            ifc.createIfcAxis2Placement3D(
                ifc.createIfcCartesianPoint([0.0, 0.0, 0.0]),
                ifc.createIfcDirection([0.0, 0.0, 1.0]),
                ifc.createIfcDirection([1.0, 0.0, 0.0]),
            ),
            ifc.createIfcDirection([0.0, 0.0, 1.0]),
            furn_h,
        )
        shape = ifc.createIfcShapeRepresentation(body_ctx, "Body", "SweptSolid", [extrusion])
        furn.Representation = ifc.createIfcProductDefinitionShape(None, None, [shape])

        ifcopenshell.api.run("aggregate.assign_object", ifc, products=[furn],
                             relating_object=storey)

    ifc.write(str(path))


def _add_space(
    ifc: ifcopenshell.file,
    body_ctx,
    storey,
    room,
    floor_h: float,
    elev: float,
) -> None:
    """Create an IfcSpace with a box geometry for one room."""
    space = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcSpace",
                                 name=room.name)
    space.ObjectType = room.type

    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[space],
                         relating_object=storey)

    # Placement: room origin in plan (x, y) → IFC (X, Y, 0) relative to storey.
    x_m = _m(room.x)
    y_m = _m(room.y)

    placement = ifc.createIfcLocalPlacement(
        None,
        ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint([x_m, y_m, 0.0]),
            ifc.createIfcDirection([0.0, 0.0, 1.0]),
            ifc.createIfcDirection([1.0, 0.0, 0.0]),
        ),
    )
    space.ObjectPlacement = placement

    # Box geometry: width × depth extruded to floor_height.
    w_m = _m(room.width)
    d_m = _m(room.depth)

    profile = ifc.createIfcRectangleProfileDef(
        "AREA", None,
        ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint([w_m / 2, d_m / 2]),
            ifc.createIfcDirection([1.0, 0.0]),
        ),
        w_m, d_m,
    )
    extrusion = ifc.createIfcExtrudedAreaSolid(
        profile,
        ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint([0.0, 0.0, 0.0]),
            ifc.createIfcDirection([0.0, 0.0, 1.0]),
            ifc.createIfcDirection([1.0, 0.0, 0.0]),
        ),
        ifc.createIfcDirection([0.0, 0.0, 1.0]),
        floor_h,
    )

    shape = ifc.createIfcShapeRepresentation(
        body_ctx, "Body", "SweptSolid", [extrusion]
    )
    space.Representation = ifc.createIfcProductDefinitionShape(None, None, [shape])
