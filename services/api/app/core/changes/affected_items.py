"""Phase 34.3 — Affected-Item Engine.

Given a ClientChangeRequest and the current ArchitectureProject, compute
exactly which modules and objects are impacted.

Impact rules:
  add_room / remove_room  → rooms + MEP (stale) + BOQ (quantities) + compliance (area rules)
                            + details (stale if type matches) + exports (all stale) + plugins
  resize_room             → rooms + MEP (point positions) + BOQ (qty) + compliance
                            + details (stale) + exports + plugins
  add_toilet              → rooms (new bathroom) + MEP plumbing+electrical + BOQ (fixtures+tile)
                            + compliance (bathroom count, ventilation) + details (toilet detail)
                            + exports + plugins
  budget / cost change    → BOQ (all items) + material_plan (selections)
  move_room               → rooms + dimensions + MEP + exports + plugins
  structural change       → rooms + walls + MEP + compliance + details + exports + plugins
"""
from __future__ import annotations

import re

from app.core.changes.models import AffectedItem, AffectedItems
from app.core.models import ArchitectureProject


# ── Intent detection ──────────────────────────────────────────────────────────

def _detect_intent(text: str) -> dict:
    """Extract structured intent from change request text."""
    t = text.lower()
    intent: dict = {
        "add_room": False,
        "remove_room": False,
        "resize_room": False,
        "move_room": False,
        "add_toilet": False,
        "budget_change": False,
        "material_change": False,
        "structural": False,
        "room_type": None,
        "budget_pct": None,
    }

    # Toilet / attached bathroom is a special compound case
    if any(kw in t for kw in ("attached toilet", "attached bathroom", "attached bath", "en-suite", "ensuite")):
        intent["add_toilet"] = True
        intent["add_room"] = True
        intent["room_type"] = "bathroom"
        return intent

    # Add room
    if any(kw in t for kw in ("add", "include", "attach", "create", "new room", "want a", "need a")):
        intent["add_room"] = True
        for rt in ("bedroom", "bathroom", "kitchen", "living", "study", "storage", "balcony", "parking", "toilet", "wc"):
            if rt in t:
                intent["room_type"] = "bathroom" if rt in ("toilet", "wc") else rt
                if rt in ("toilet", "wc", "bathroom"):
                    intent["add_toilet"] = True
                break

    # Remove room
    if any(kw in t for kw in ("remove", "delete", "take out", "drop")):
        intent["remove_room"] = True
        for rt in ("bedroom", "bathroom", "kitchen", "living", "study", "storage", "balcony", "parking"):
            if rt in t:
                intent["room_type"] = rt
                break

    # Resize
    if any(kw in t for kw in ("bigger", "larger", "smaller", "wider", "resize", "make kitchen", "make bedroom", "make living", "enlarge", "reduce size", "extend")):
        intent["resize_room"] = True
        for rt in ("bedroom", "bathroom", "kitchen", "living", "study", "storage", "balcony"):
            if rt in t:
                intent["room_type"] = rt
                break

    # Move
    if any(kw in t for kw in ("move", "relocate", "shift", "swap", "rotate")):
        intent["move_room"] = True

    # Budget
    if any(kw in t for kw in ("budget", "cost", "reduce cost", "reduce budget", "cheaper", "premium", "economy", "reduce by")):
        intent["budget_change"] = True
        pct_match = re.search(r"(\d+)\s*(?:percent|%)", t)
        if pct_match:
            intent["budget_pct"] = int(pct_match.group(1))

    # Material
    if any(kw in t for kw in ("material", "tile", "finish", "paint", "floor", "wall finish", "marble", "granite", "vitrified")):
        intent["material_change"] = True

    # Structural
    if any(kw in t for kw in ("wall", "structure", "structural", "column", "beam", "slab", "load bearing")):
        intent["structural"] = True

    return intent


# ── Module impact functions ───────────────────────────────────────────────────

def _room_impacts(project: ArchitectureProject, intent: dict) -> list[AffectedItem]:
    items: list[AffectedItem] = []
    rt = intent.get("room_type")

    if intent["add_room"]:
        desc = f"New {rt or 'room'} will be added to the floor plan"
        items.append(AffectedItem(module="rooms", description=desc, severity="action_needed", action="Regenerate floor plan with new room"))

    if intent["remove_room"]:
        matching = [r for r in project.rooms if r.type == rt] if rt else []
        for room in matching:
            items.append(AffectedItem(module="rooms", object_id=room.id, description=f"Room '{room.name}' will be removed", severity="action_needed", action="Confirm removal and regenerate"))
        if not matching:
            items.append(AffectedItem(module="rooms", description=f"No {rt or 'matching'} room found to remove", severity="warning", action="Specify room by name"))

    if intent["resize_room"]:
        matching = [r for r in project.rooms if r.type == rt] if rt else project.rooms[:1]
        for room in matching:
            items.append(AffectedItem(module="rooms", object_id=room.id, description=f"Room '{room.name}' dimensions will change", severity="action_needed", action="Apply resize via parameter editor"))

    if intent["move_room"]:
        items.append(AffectedItem(module="rooms", description="Room position will change; adjacency relationships may shift", severity="warning", action="Review room layout after move"))

    return items


def _mep_impacts(project: ArchitectureProject, intent: dict) -> list[AffectedItem]:
    items: list[AffectedItem] = []
    has_mep = project.mep_plan.generated

    if intent["add_toilet"]:
        items.append(AffectedItem(module="mep", description="Plumbing — drain and supply points needed for new WC + basin", severity="action_needed", action="Regenerate MEP plumbing layer"))
        items.append(AffectedItem(module="mep", description="Electrical — switch and light point needed in new bathroom", severity="action_needed", action="Regenerate MEP electrical layer"))
        if has_mep:
            items.append(AffectedItem(module="mep", description="Existing MEP plan is now stale", severity="warning", action="Re-run MEP generation to include new fixtures"))

    elif intent["add_room"]:
        if has_mep:
            items.append(AffectedItem(module="mep", description="MEP plan is stale — new room not covered", severity="warning", action="Re-run MEP generation"))

    elif intent["resize_room"] or intent["move_room"]:
        if has_mep:
            rt = intent.get("room_type")
            pts = [p for p in (project.mep_plan.plumbing.points + project.mep_plan.electrical.points + project.mep_plan.lighting.points + project.mep_plan.ac.points) if rt is None or True]
            for p in pts[:3]:  # show first 3 affected
                items.append(AffectedItem(module="mep", object_id=p.id, description=f"MEP point '{p.kind}' in room may need repositioning", severity="warning", action="Review MEP point positions after resize"))

    return items


def _boq_impacts(project: ArchitectureProject, intent: dict) -> list[AffectedItem]:
    items: list[AffectedItem] = []
    has_boq = project.cost_plan.generated

    if intent["add_toilet"]:
        items.append(AffectedItem(module="boq", description="Plumbing fixtures — WC, basin (+₹15,000–₹25,000 est.)", severity="action_needed", action="Recalculate BOQ to include new fixtures"))
        items.append(AffectedItem(module="boq", description="Floor tiles — new bathroom area (~25–40 ft²)", severity="action_needed", action="Recalculate BOQ for tile quantities"))
        items.append(AffectedItem(module="boq", description="Waterproofing — new bathroom floor and walls", severity="action_needed", action="Add waterproofing BOQ line"))
        if has_boq:
            items.append(AffectedItem(module="boq", description="Existing BOQ is stale — grand total will change", severity="warning", action="Recalculate BOQ"))

    elif intent["add_room"]:
        if has_boq:
            items.append(AffectedItem(module="boq", description="BOQ is stale — new room adds floor tile, paint, and opening quantities", severity="warning", action="Recalculate BOQ"))

    elif intent["resize_room"]:
        if has_boq:
            rt = intent.get("room_type")
            items.append(AffectedItem(module="boq", description=f"{rt or 'Room'} area change affects tile and paint quantities", severity="warning", action="Recalculate BOQ"))

    if intent["budget_change"]:
        pct = intent.get("budget_pct")
        pct_str = f"{pct}%" if pct else "target"
        items.append(AffectedItem(module="boq", description=f"Budget reduction to {pct_str} — BOQ rates and material selections must be reviewed", severity="action_needed", action="Edit rates in BOQ Studio and recalculate"))
        items.append(AffectedItem(module="boq", description="Grand total must be reconciled to budget target", severity="warning", action="Recalculate BOQ after rate edits"))

    if intent["material_change"]:
        items.append(AffectedItem(module="boq", description="Material change affects supply rates and quantities", severity="warning", action="Update material plan and recalculate BOQ"))

    return items


def _compliance_impacts(project: ArchitectureProject, intent: dict) -> list[AffectedItem]:
    items: list[AffectedItem] = []

    if intent["add_toilet"]:
        bath_count = sum(1 for r in project.rooms if r.type in ("bathroom", "master_bathroom")) + 1
        items.append(AffectedItem(module="compliance", description=f"Bathroom count will be {bath_count} — verify NBC ventilation requirement (window ≥ 1/8 floor area)", severity="warning", action="Recheck compliance after room addition"))

    if intent["add_room"] or intent["resize_room"]:
        built = sum(r.width * r.depth for r in project.rooms)
        site = project.site.width * project.site.depth
        cov_pct = round(built / site * 100, 1) if site > 0 else 0
        items.append(AffectedItem(module="compliance", description=f"Coverage currently {cov_pct}% — new room may exceed NBC/CMDA limit", severity="warning", action="Recheck compliance after change"))

    if intent["structural"]:
        items.append(AffectedItem(module="compliance", description="Structural change may affect setback compliance and load-path review", severity="action_needed", action="Submit revised drawings for engineer review"))

    return items


def _detail_impacts(project: ArchitectureProject, intent: dict) -> list[AffectedItem]:
    items: list[AffectedItem] = []
    rt = intent.get("room_type")

    stale_details = [d for d in project.detail_drawings if not d.stale]
    if intent["add_toilet"]:
        items.append(AffectedItem(module="details", description="Toilet plan detail required for new bathroom", severity="action_needed", action="Generate toilet detail drawing"))

    if (intent["resize_room"] or intent["move_room"]) and rt:
        matching_details = [d for d in stale_details if any(oid in [r.id for r in project.rooms if r.type == rt] for oid in d.source_object_ids)]
        for d in matching_details:
            items.append(AffectedItem(module="details", object_id=d.id, description=f"Detail '{d.name}' is stale after room resize", severity="warning", action="Regenerate detail drawing"))

    if intent["add_room"] or intent["remove_room"]:
        for d in stale_details:
            items.append(AffectedItem(module="details", object_id=d.id, description=f"Detail '{d.name}' may need review after floor plan change", severity="info", action="Verify detail is still current"))

    return items


def _export_impacts(project: ArchitectureProject) -> list[AffectedItem]:
    return [
        AffectedItem(module="exports", description="All drawing exports (DXF, SVG, PDF, IFC) are stale after design change", severity="warning", action="Re-export after change is applied"),
        AffectedItem(module="exports", description="3D exports (SketchUp .rb, Blender .py, GLTF) need re-generation", severity="warning", action="Re-export 3D model after change"),
        AffectedItem(module="exports", description="Presentation sheets (SVG/PDF) show outdated floor plan", severity="warning", action="Re-export presentation sheets"),
    ]


def _plugin_impacts(intent: dict) -> list[AffectedItem]:
    items: list[AffectedItem] = []
    if intent["add_room"] or intent["remove_room"] or intent["resize_room"] or intent["move_room"] or intent["structural"]:
        items.append(AffectedItem(module="plugins", description="Revit model is out of sync — run Revit add-in sync to pull changes", severity="warning", action="Use Revit › Scotch › Sync › Pull"))
        items.append(AffectedItem(module="plugins", description="SketchUp model is out of sync — re-import updated .rb script", severity="warning", action="Download new SketchUp script and run in Ruby Console"))
    return items


# ── Main entry ────────────────────────────────────────────────────────────────

def compute_affected_items(
    change_id: str,
    request_text: str,
    project: ArchitectureProject,
) -> AffectedItems:
    """Compute full affected-item report for a change request against *project*."""
    intent = _detect_intent(request_text)

    rooms = _room_impacts(project, intent)
    mep = _mep_impacts(project, intent)
    boq = _boq_impacts(project, intent)
    compliance = _compliance_impacts(project, intent)
    details = _detail_impacts(project, intent)
    exports = _export_impacts(project)
    plugins = _plugin_impacts(intent)

    total = sum(len(x) for x in [rooms, mep, boq, compliance, details, exports, plugins])

    # Build human-readable summary
    action_count = sum(
        1 for item in (rooms + mep + boq + compliance + details + exports + plugins)
        if item.severity == "action_needed"
    )
    warn_count = sum(
        1 for item in (rooms + mep + boq + compliance + details + exports + plugins)
        if item.severity == "warning"
    )

    if intent["add_toilet"]:
        summary = f"Adding attached toilet — {action_count} actions needed across MEP, BOQ, and compliance."
        cost_impact = "Est. +₹25,000–₹45,000 (WC, basin, tiles, waterproofing, plumbing)"
    elif intent["budget_change"]:
        pct = intent.get("budget_pct")
        summary = f"Budget reduction {f'by {pct}%' if pct else ''} — affects all BOQ categories."
        cost_impact = f"Reduce BOQ grand total by {pct}%" if pct else "Review all rates"
    elif intent["add_room"]:
        rt = intent.get("room_type", "room")
        summary = f"Adding {rt} — {action_count} actions, {warn_count} warnings across {total} items."
        cost_impact = "Est. area-dependent; recalculate BOQ"
    elif intent["resize_room"]:
        rt = intent.get("room_type", "room")
        summary = f"Resizing {rt} — MEP, BOQ, and details need review ({warn_count} warnings)."
        cost_impact = "Tile/paint quantities will change; recalculate BOQ"
    elif intent["remove_room"]:
        rt = intent.get("room_type", "room")
        summary = f"Removing {rt} — {action_count} actions needed."
        cost_impact = "BOQ quantities will decrease"
    else:
        summary = f"{action_count} action(s) needed, {warn_count} warning(s) across {total} item(s)."
        cost_impact = "Recalculate BOQ to assess cost impact"

    return AffectedItems(
        change_id=change_id,
        rooms=rooms,
        mep=mep,
        boq=boq,
        compliance=compliance,
        details=details,
        exports=exports,
        plugins=plugins,
        total_count=total,
        summary=summary,
        cost_impact=cost_impact,
    )
