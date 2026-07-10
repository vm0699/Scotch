"""Phase 24 — MCP tool implementations (Stages 24.2–24.4).

Shared by:
- app/api/routes/chat.py  (in-app agentic chat loop)
- services/mcp/server.py  (standalone MCP server, imports via sys.path)

Every design-mutating tool runs the validator before saving.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.regenerate import ParameterChange, apply_changes
from app.core.architecture.requirement_parser import parse_prompt
from app.core.models import ArchitectureProject
from app.core.storage.factory import get_project_store
from app.core.validation import validate_project


# ── helpers ───────────────────────────────────────────────────────────────────


def _store():
    return get_project_store()


def _load(project_id: str) -> ArchitectureProject:
    stored = _store().get_project(project_id)
    if stored.project is None:
        raise ValueError(f"Project '{project_id}' has no design — generate first.")
    return stored.project


def _save(project_id: str, project: ArchitectureProject, change_type: str = "regenerate") -> dict:
    _store().update_project(project_id, project=project, change_type=change_type)
    return project.model_dump()


def _apply_and_save(project_id: str, changes: list[ParameterChange]) -> dict:
    proj = _load(project_id)
    updated, _ = apply_changes(proj, changes)
    result = validate_project(updated)
    if not result.valid:
        raise ValueError(f"Invalid design after edit: {'; '.join(result.errors)}")
    return _save(project_id, updated)


# ── Stage 24.2 — Read tools ───────────────────────────────────────────────────


def get_project(project_id: str) -> dict:
    """Return the full ArchitectureProject for a stored project."""
    from app.core.storage import ProjectNotFoundError
    try:
        stored = _store().get_project(project_id)
    except ProjectNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    if stored.project is None:
        raise ValueError(f"Project '{project_id}' has no design yet.")
    return stored.project.model_dump()


def list_projects() -> list[dict]:
    """List all stored projects (summary rows)."""
    return [p.model_dump() for p in _store().list_projects()]


def get_program(project_id: str) -> dict:
    """Return structured program table: site + rooms + totals."""
    proj = _load(project_id)
    total_area = sum(r.width * r.depth for r in proj.rooms)
    site_area = proj.site.width * proj.site.depth
    return {
        "site": {
            "width": proj.site.width,
            "depth": proj.site.depth,
            "orientation": proj.site.orientation,
            "floors": proj.building.floors,
            "floor_height": proj.building.floor_height,
        },
        "rooms": [
            {
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "width": r.width,
                "depth": r.depth,
                "area": round(r.width * r.depth, 2),
                "level": r.level,
            }
            for r in proj.rooms
        ],
        "totals": {
            "built_up_area": round(total_area, 2),
            "site_area": round(site_area, 2),
            "coverage_pct": round(total_area / site_area * 100, 1) if site_area else 0,
            "room_count": len(proj.rooms),
        },
    }


def list_versions(project_id: str) -> list[dict]:
    """List version history snapshots."""
    stored = _store().get_project(project_id)
    versions = getattr(stored, "versions", None) or []
    return [
        {
            "id": getattr(v, "id", str(i)),
            "created_at": getattr(v, "created_at", ""),
            "change_type": getattr(v, "change_type", ""),
            "summary": getattr(v, "summary", ""),
        }
        for i, v in enumerate(versions)
    ]


# ── Stage 24.3 — Generate / edit tools ───────────────────────────────────────


def generate_design(project_id: str, prompt: str, mode: str = "deterministic") -> dict:
    """Generate a floor plan from a prompt and save it. Applies profile + brief fusion."""
    from app.core.profile.fusion import PromptProfileFusion
    from app.core.profile.store import get_profile_store

    req = parse_prompt(prompt)

    # Fuse with user profile + project client brief (if project already exists)
    profile = get_profile_store().get_profile("local-user")
    brief = None
    try:
        existing = _load(project_id)
        brief = existing.client_brief
    except Exception:
        pass
    req, _reasoning = PromptProfileFusion.apply(req, profile, brief)

    project, _ = generate_floorplan(req)

    # Preserve existing client_brief if project had one
    if brief is not None:
        project = project.model_copy(update={"client_brief": brief})

    result = validate_project(project)
    if not result.valid:
        raise ValueError(f"Generated design failed validation: {'; '.join(result.errors)}")
    return _save(project_id, project, change_type="generate")


def add_room(project_id: str, room_type: str, name: str = "") -> dict:
    """Add a room of the given type."""
    updated = _apply_and_save(project_id, [ParameterChange(key="add_room", value=room_type)])
    if name:
        # Rename the newly added room
        proj_after = _load(project_id)
        matching = [r for r in proj_after.rooms if r.type == room_type]
        if matching:
            _apply_and_save(
                project_id,
                [ParameterChange(key="room_name", value=name, target_id=matching[-1].id)],
            )
            return _load(project_id).model_dump()
    return updated


def remove_room(project_id: str, room_id: str) -> dict:
    """Remove a room by its stable ID."""
    return _apply_and_save(
        project_id,
        [ParameterChange(key="remove_room", value="", target_id=room_id)],
    )


def set_parameter(project_id: str, key: str, value: Any, target_id: str = "") -> dict:
    """Edit a project or room parameter."""
    change = ParameterChange(
        key=key,
        value=value,
        **({"target_id": target_id} if target_id else {}),
    )
    return _apply_and_save(project_id, [change])


# ── Stage 24.4 — Intelligence + export tools ─────────────────────────────────


def run_intelligence(project_id: str, vastu: bool = False) -> dict:
    """Run spatial and Vastu analysis."""
    from app.core.intelligence import (
        IntelligenceReport,
        compute_areas,
        run_spatial_checks,
        run_vastu_checks,
    )
    proj = _load(project_id)
    report = IntelligenceReport(
        project_id=project_id,
        spatial_checks=run_spatial_checks(proj),
        area_summary=compute_areas(proj),
        vastu_suggestions=run_vastu_checks(proj) if vastu else None,
    )
    return report.model_dump()


def export_project(project_id: str, format: str) -> dict:
    """Export the project to a file and return the filename."""
    from app.config import get_settings
    from app.core.exports import export_dxf, export_json, export_png, export_svg
    from app.core.exports.ifc_exporter import export_ifc

    proj = _load(project_id)
    settings = get_settings()
    exports_dir = (
        Path(settings.data_dir) / "users" / "local-user" / "projects" / project_id / "exports"
    )
    exports_dir.mkdir(parents=True, exist_ok=True)

    _EXPORTERS: dict[str, tuple[Any, str]] = {
        "json": (export_json, "floor_plan.json"),
        "svg": (export_svg, "floor_plan.svg"),
        "png": (export_png, "floor_plan.png"),
        "dxf": (export_dxf, "floor_plan.dxf"),
        "ifc": (export_ifc, "model.ifc"),
    }
    if format not in _EXPORTERS:
        raise ValueError(f"Unsupported format '{format}'. Choose from: {list(_EXPORTERS)}")

    fn, name = _EXPORTERS[format]
    fn(proj, exports_dir / name)
    return {"filename": name}


def render_project(project_id: str, camera_id: str, style: str) -> dict:
    """Generate a render (deterministic passthrough when no SD key)."""
    from app.core.ai.provider import get_render_provider
    proj = _load(project_id)
    img_bytes = get_render_provider().render_image(proj, camera_id, style, None)
    return {"render_b64": base64.b64encode(img_bytes).decode()}


# ── Phase 29: MEP tools ───────────────────────────────────────────────────────


def generate_mep(project_id: str, systems: list[str] | None = None) -> dict:
    """Generate MEP service points for the given systems (default: all four).

    Runs MEPGenerator, validates, persists, and returns the updated project.
    systems: list of "plumbing" | "electrical" | "lighting" | "ac"
    """
    from app.core.architecture.mep_generator import MEPGenerator

    proj = _load(project_id)
    systems = systems or ["plumbing", "electrical", "lighting", "ac"]
    mep = MEPGenerator.generate(proj, systems=systems)
    proj = proj.model_copy(update={"mep_plan": mep, "show_mep": True})
    result = validate_project(proj)
    if not result.valid:
        raise ValueError(f"MEP generation failed validation: {'; '.join(result.errors)}")
    return _save(project_id, proj, change_type="regenerate")


def edit_mep_point(project_id: str, point_id: str, x: float, y: float) -> dict:
    """Move a MEP service point to new coordinates and mark it as user-override."""
    from app.core.architecture.mep_generator import MEPGenerator

    proj = _load(project_id)
    new_mep = MEPGenerator.move_point(proj.mep_plan, point_id, x, y)
    proj = proj.model_copy(update={"mep_plan": new_mep})
    result = validate_project(proj)
    if not result.valid:
        raise ValueError(f"Edit rejected: {'; '.join(result.errors)}")
    return _save(project_id, proj, change_type="regenerate")


def get_mep_plan(project_id: str) -> dict:
    """Return the current MEP plan (all systems)."""
    proj = _load(project_id)
    return proj.mep_plan.model_dump()


# ── Phase 30: Detail Drawing tools ───────────────────────────────────────────


def generate_detail(
    project_id: str,
    detail_type: str,
    source_id: str,
) -> dict:
    """Generate a detail drawing (toilet/kitchen/door_window/wall_section/tile_layout/stair).

    detail_type: one of toilet | kitchen | door_window | wall_section | tile_layout | stair
    source_id: id of the Room, Door, Window, or StairEntity to detail
    """
    from app.core.architecture.detail_engine import DetailEngine

    proj = _load(project_id)
    drawing = DetailEngine.generate(proj, detail_type, source_id)
    drawings = DetailEngine.replace_or_add(proj.detail_drawings, drawing)
    proj = proj.model_copy(update={"detail_drawings": drawings})
    result = validate_project(proj)
    if not result.valid:
        raise ValueError(f"Detail generation failed validation: {'; '.join(result.errors)}")
    return _save(project_id, proj, change_type="regenerate")


def list_details(project_id: str) -> dict:
    """List all detail drawings for a project."""
    proj = _load(project_id)
    return {
        "detail_drawings": [
            {
                "id": d.id, "name": d.name, "detail_type": d.detail_type,
                "scale": d.scale, "view": d.view, "stale": d.stale,
                "confidence": d.confidence, "needs_review": d.needs_review,
                "source_object_ids": d.source_object_ids,
            }
            for d in proj.detail_drawings
        ],
        "count": len(proj.detail_drawings),
    }


def delete_detail(project_id: str, detail_id: str) -> dict:
    """Remove a detail drawing by id."""
    from app.core.architecture.detail_engine import DetailEngine

    proj = _load(project_id)
    drawings = DetailEngine.remove(proj.detail_drawings, detail_id)
    if len(drawings) == len(proj.detail_drawings):
        raise ValueError(f"Detail '{detail_id}' not found")
    proj = proj.model_copy(update={"detail_drawings": drawings})
    return _save(project_id, proj, change_type="edit")


# ── Phase 31: BOQ / Cost tools ────────────────────────────────────────────────


def calculate_boq(project_id: str) -> dict:
    """Calculate the Bill of Quantities and cost plan for a project.

    Uses room areas, door/window counts, MEP fixture counts (if generated),
    and default INR rates. Returns the updated project with cost_plan populated.
    """
    from app.core.boq.quantity_engine import QuantityEngine

    proj = _load(project_id)
    engine = QuantityEngine(proj)
    updated_mat, cost = engine.build_boq()
    proj = proj.model_copy(update={
        "material_plan": updated_mat,
        "cost_plan": cost,
    })
    result = validate_project(proj)
    if not result.valid:
        raise ValueError(f"BOQ failed validation: {'; '.join(result.errors)}")
    return _save(project_id, proj, change_type="regenerate")


def edit_rate(project_id: str, category: str, item: str, rate: float) -> dict:
    """Update a single rate in the project's rate table and recalculate BOQ.

    category: e.g. "flooring" | "paint" | "plumbing" | "electrical" | "doors" | "windows"
    item: e.g. "tile_supply" | "interior_paint" | "wc" | "interior_door"
    rate: new rate in INR per unit
    """
    from app.core.boq.quantity_engine import QuantityEngine
    from app.core.models.project import RateEntry

    proj = _load(project_id)
    # Upsert rate entry
    rates = list(proj.material_plan.editable_rates)
    existing = next((r for r in rates if r.category == category and r.item == item), None)
    if existing:
        rates = [r for r in rates if not (r.category == category and r.item == item)]
    rates.append(RateEntry(category=category, item=item, unit="", rate=rate, source="manual"))
    mat = proj.material_plan.model_copy(update={"editable_rates": rates})
    proj = proj.model_copy(update={"material_plan": mat})
    # Recalculate BOQ with updated rates
    engine = QuantityEngine(proj)
    updated_mat, cost = engine.build_boq()
    proj = proj.model_copy(update={"material_plan": updated_mat, "cost_plan": cost})
    result = validate_project(proj)
    if not result.valid:
        raise ValueError(f"Rate edit failed validation: {'; '.join(result.errors)}")
    return _save(project_id, proj, change_type="edit")


def get_boq(project_id: str) -> dict:
    """Return the current cost plan / BOQ for a project."""
    proj = _load(project_id)
    return {
        "generated": proj.cost_plan.generated,
        "grand_total": proj.cost_plan.grand_total,
        "category_totals": [ct.model_dump() for ct in proj.cost_plan.category_totals],
        "missing_rates": proj.cost_plan.missing_rates,
        "assumptions": proj.cost_plan.assumptions,
        "confidence": proj.cost_plan.confidence,
        "needs_review": proj.cost_plan.needs_review,
        "boq_items": [item.model_dump() for item in proj.cost_plan.boq_items],
    }


def edit_tile_spec(
    project_id: str,
    tile_spec_id: str,
    size_w: float | None = None,
    size_h: float | None = None,
    rate_per_sqft: float | None = None,
    wastage_pct: float | None = None,
) -> dict:
    """Edit a tile specification by id and recalculate BOQ."""
    from app.core.boq.quantity_engine import QuantityEngine

    proj = _load(project_id)
    specs = list(proj.material_plan.tile_specs)
    target = next((s for s in specs if s.id == tile_spec_id), None)
    if target is None:
        raise ValueError(f"TileSpec '{tile_spec_id}' not found.")
    updates: dict = {}
    if size_w is not None:
        updates["size_w"] = size_w
    if size_h is not None:
        updates["size_h"] = size_h
    if rate_per_sqft is not None:
        updates["rate_per_sqft"] = rate_per_sqft
    if wastage_pct is not None:
        updates["wastage_pct"] = wastage_pct
    new_spec = target.model_copy(update=updates)
    specs = [new_spec if s.id == tile_spec_id else s for s in specs]
    mat = proj.material_plan.model_copy(update={"tile_specs": specs})
    proj = proj.model_copy(update={"material_plan": mat})
    engine = QuantityEngine(proj)
    updated_mat, cost = engine.build_boq()
    proj = proj.model_copy(update={"material_plan": updated_mat, "cost_plan": cost})
    result = validate_project(proj)
    if not result.valid:
        raise ValueError(f"Tile spec edit failed validation: {'; '.join(result.errors)}")
    return _save(project_id, proj, change_type="edit")


# ── Phase 32 — Tamil Nadu advisory ────────────────────────────────────────────

def check_tn_rules(project_id: str, road_width_ft: float = 0.0) -> dict:
    """Run Tamil Nadu advisory checks (CMDA/DTCP). Advisory — not engineering certification."""
    from app.core.compliance.tamil_nadu import run_tn_advisory

    proj = _load(project_id)
    report = run_tn_advisory(
        proj,
        project_id,
        road_width_ft=road_width_ft if road_width_ft > 0 else None,
    )
    return {
        "type": "tn_advisory",
        "passes_advisory": report.passes_advisory,
        "summary": report.summary,
        "results": [r.model_dump() for r in report.results],
        "missing_inputs": report.missing_inputs,
        "disclaimer": report.disclaimer,
        "result_count": len(report.results),
        "warn_count": sum(1 for r in report.results if r.status in ("warn", "fail")),
    }


# ── Phase 33 — Profile + brief tools ─────────────────────────────────────────


def get_user_profile(user_id: str = "local-user") -> dict:
    """Return the stored architect-twin profile for the user."""
    from app.core.profile.store import get_profile_store
    profile = get_profile_store().get_profile(user_id)
    return profile.model_dump()


def update_user_profile(
    user_id: str = "local-user",
    role: str | None = None,
    preferred_units: str | None = None,
    default_location: str | None = None,
    default_style: str | None = None,
    default_orientation: str | None = None,
    explanation_style: str | None = None,
    account_mode: str | None = None,
    display_name: str | None = None,
    cloud_email: str | None = None,
    cloud_user_id: str | None = None,
) -> dict:
    """Update fields on the user architect-twin profile."""
    from app.core.profile.store import get_profile_store
    updates: dict = {}
    if role is not None:
        updates["role"] = role
    if preferred_units is not None:
        updates["preferred_units"] = preferred_units
    if default_location is not None:
        updates["default_location"] = default_location
    if default_style is not None:
        updates["default_style"] = default_style
    if default_orientation is not None:
        updates["default_orientation"] = default_orientation
    if explanation_style is not None:
        updates["explanation_style"] = explanation_style
    if account_mode is not None:
        updates["account_mode"] = account_mode
    if display_name is not None:
        updates["display_name"] = display_name
    if cloud_email is not None:
        updates["cloud_email"] = cloud_email
    if cloud_user_id is not None:
        updates["cloud_user_id"] = cloud_user_id
    store = get_profile_store()
    store.update_profile(user_id, **updates)
    return store.get_profile(user_id).model_dump()


def get_client_brief(project_id: str) -> dict:
    """Return the client brief attached to a project."""
    proj = _load(project_id)
    return proj.client_brief.model_dump()


def update_client_brief(
    project_id: str,
    family_name: str | None = None,
    family_size: int | None = None,
    lifestyle: str | None = None,
    budget_level: str | None = None,
    budget_inr: float | None = None,
    style_preference: str | None = None,
    vastu_preference: bool | None = None,
    parking_preference: str | None = None,
    future_expansion: bool | None = None,
    material_preference: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update the client brief on a project (without re-generating the design)."""
    proj = _load(project_id)
    brief = proj.client_brief
    updates: dict = {}
    if family_name is not None:
        updates["family_name"] = family_name
    if family_size is not None:
        updates["family_size"] = family_size
    if lifestyle is not None:
        updates["lifestyle"] = lifestyle
    if budget_level is not None:
        updates["budget_level"] = budget_level
    if budget_inr is not None:
        updates["budget_inr"] = budget_inr
    if style_preference is not None:
        updates["style_preference"] = style_preference
    if vastu_preference is not None:
        updates["vastu_preference"] = vastu_preference
    if parking_preference is not None:
        updates["parking_preference"] = parking_preference
    if future_expansion is not None:
        updates["future_expansion"] = future_expansion
    if material_preference is not None:
        updates["material_preference"] = material_preference
    if notes is not None:
        updates["notes"] = notes
    if updates:
        new_brief = brief.model_copy(update=updates)
        proj = proj.model_copy(update={"client_brief": new_brief})
        result = validate_project(proj)
        if not result.valid:
            raise ValueError(f"Brief update failed validation: {'; '.join(result.errors)}")
        _save(project_id, proj, change_type="edit")
    return proj.client_brief.model_dump()


def restore_version(project_id: str, version_id: str) -> dict:
    """Restore to a saved version snapshot."""
    from app.core.storage import VersionNotFoundError
    from app.core.storage.base import LOCAL_USER_ID
    store = _store()
    try:
        ver = store.get_version(project_id, version_id, user_id=LOCAL_USER_ID)
    except (VersionNotFoundError, Exception) as exc:
        raise ValueError(str(exc)) from exc
    snapshot = ver.snapshot
    result = validate_project(snapshot)
    if not result.valid:
        raise ValueError(f"Version snapshot failed validation: {'; '.join(result.errors)}")
    stored = store.update_project(
        project_id, project=snapshot, change_type="restore",
        version_summary=f"Restored to version {version_id}",
    )
    if stored.project is None:
        raise ValueError("Restored version has no design data.")
    return stored.project.model_dump()


# ── Phase 34 — Client Change Management tools ─────────────────────────────────


def create_client_change(project_id: str, request_text: str, source: str = "client", priority: str = "medium") -> dict:
    """Create a new client change request and compute its affected items.

    Returns the ClientChangeRequest with embedded AffectedItems so the caller
    can immediately present impact summary and status to the user.
    """
    from app.core.changes.affected_items import compute_affected_items
    from app.core.changes.store import get_change_store
    from app.core.storage.base import LOCAL_USER_ID

    cs = get_change_store()
    change = cs.create(LOCAL_USER_ID, project_id, request_text, source, priority)

    # Compute affected items if project has a design
    try:
        proj = _load(project_id)
        affected = compute_affected_items(change.id, request_text, proj)
        change.affected_items = affected
        change.affected_modules = list({item.module for items in [
            affected.rooms, affected.mep, affected.boq,
            affected.compliance, affected.details, affected.exports, affected.plugins
        ] for item in items})
        change.summary = affected.summary
        change.cost_impact = affected.cost_impact
        change = cs.update(LOCAL_USER_ID, project_id, change)
    except Exception:
        pass

    return change.model_dump()


def show_affected_items(project_id: str, change_id: str) -> dict:
    """Return the full affected-item report for an existing change request."""
    from app.core.changes.affected_items import compute_affected_items
    from app.core.changes.store import get_change_store
    from app.core.storage.base import LOCAL_USER_ID

    cs = get_change_store()
    try:
        change = cs.get(LOCAL_USER_ID, project_id, change_id)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc

    proj = _load(project_id)
    affected = compute_affected_items(change.id, change.request_text, proj)
    return affected.model_dump()


def list_client_changes(project_id: str) -> dict:
    """List all client change requests for a project."""
    from app.core.changes.store import get_change_store
    from app.core.storage.base import LOCAL_USER_ID

    cs = get_change_store()
    changes = cs.list(LOCAL_USER_ID, project_id)
    pending = [c for c in changes if c.status == "pending"]
    approved = [c for c in changes if c.status == "approved"]
    applied = [c for c in changes if c.status == "applied"]
    return {
        "total": len(changes),
        "pending": len(pending),
        "approved": len(approved),
        "applied": len(applied),
        "changes": [
            {
                "id": c.id,
                "request_text": c.request_text,
                "status": c.status,
                "priority": c.priority,
                "summary": c.summary,
                "cost_impact": c.cost_impact,
                "affected_modules": c.affected_modules,
                "created_at": c.created_at.isoformat(),
            }
            for c in changes
        ],
    }


def approve_change(project_id: str, change_id: str) -> dict:
    """Approve a pending client change request."""
    from app.core.changes.store import get_change_store
    from app.core.storage.base import LOCAL_USER_ID

    cs = get_change_store()
    try:
        change = cs.set_status(LOCAL_USER_ID, project_id, change_id, "approved")
    except KeyError as exc:
        raise ValueError(str(exc)) from exc
    return {"change_id": change.id, "status": change.status, "message": f"Change '{change.request_text[:60]}' approved — ready to apply."}


def reject_change(project_id: str, change_id: str, reason: str = "") -> dict:
    """Reject a client change request."""
    from app.core.changes.store import get_change_store
    from app.core.storage.base import LOCAL_USER_ID

    cs = get_change_store()
    try:
        change = cs.get(LOCAL_USER_ID, project_id, change_id)
        change.status = "rejected"
        if reason:
            change.summary = f"Rejected: {reason}"
        change = cs.update(LOCAL_USER_ID, project_id, change)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc
    return {"change_id": change.id, "status": change.status, "message": f"Change rejected. {reason}"}


def revert_change(project_id: str, change_id: str) -> dict:
    """Revert an applied client change by restoring the before_version snapshot."""
    from app.core.changes.store import get_change_store
    from app.core.storage.base import LOCAL_USER_ID
    from app.core.storage import VersionNotFoundError

    cs = get_change_store()
    try:
        change = cs.get(LOCAL_USER_ID, project_id, change_id)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc

    if change.status != "applied":
        raise ValueError(f"Change is '{change.status}' — only applied changes can be reverted.")

    if not change.before_version:
        raise ValueError("No before_version snapshot recorded for this change — cannot revert automatically.")

    # Restore the before_version
    try:
        result = restore_version(project_id, change.before_version)
    except Exception as exc:
        raise ValueError(f"Revert failed — could not restore snapshot: {exc}") from exc

    change.status = "reverted"
    cs.update(LOCAL_USER_ID, project_id, change)
    return {"change_id": change.id, "status": "reverted", "message": "Change reverted — design restored to before-change snapshot.", "project": result}


# ── Phase 36 — Render prompt generation ───────────────────────────────────────


def generate_render_prompt_tool(project_id: str, camera_name: str | None = None, extra_tags: list[str] | None = None) -> dict:
    """Generate a context-aware photorealistic render prompt from the project."""
    from app.core.render.prompt_generator import generate_render_prompt
    proj = _load(project_id)
    prompt_str = generate_render_prompt(proj, camera_name=camera_name, extra_tags=extra_tags)
    return {
        "render_prompt": prompt_str,
        "camera": camera_name or "exterior_front",
        "style": proj.building.style,
        "orientation": proj.site.orientation,
        "budget_level": getattr(getattr(proj, "client_brief", None), "budget_level", "standard"),
        "usage": "Paste into Midjourney, Stable Diffusion, DALL-E 3, or Blender render comment.",
    }


def export_drawing(project_id: str, format: str = "svg") -> dict:
    """Export a project drawing file (svg, dxf, png, pdf, json, etc.)."""
    return export_project(project_id, format=format)


# ── Phase 40 — Feasibility / Yield Analysis ───────────────────────────────────


def run_feasibility(project_id: str, road_width_ft: float = 0.0) -> dict:
    """Run residential feasibility / yield analysis on the project site.

    Returns site metrics, FSI/FAR envelope, and five development options
    (compact, balanced, spacious, future-expansion, rental-friendly).
    Advisory only — verify with a licensed architect and CMDA/DTCP.
    """
    from app.core.feasibility.engine import FeasibilityEngine

    proj = _load(project_id)
    engine = FeasibilityEngine()
    feasibility = engine.compute(proj, road_width_ft=road_width_ft)
    updated = proj.model_copy(update={"feasibility": feasibility})
    _save(project_id, updated, change_type="edit")
    return feasibility.model_dump()


def compare_feasibility_options(project_id: str) -> dict:
    """Return a formatted comparison of all feasibility options for the project.

    If feasibility has not been run yet, runs it first with default setbacks.
    """
    proj = _load(project_id)
    if not proj.feasibility.generated:
        from app.core.feasibility.engine import FeasibilityEngine
        feasibility = FeasibilityEngine().compute(proj, road_width_ft=0.0)
        proj = proj.model_copy(update={"feasibility": feasibility})
        _save(project_id, proj, change_type="edit")
    else:
        feasibility = proj.feasibility

    options_summary = []
    for opt in feasibility.options:
        options_summary.append({
            "name": opt.name,
            "label": opt.label,
            "unit_count": opt.unit_count,
            "unit_type": opt.unit_type,
            "built_up_area": opt.built_up_area,
            "coverage_pct": opt.coverage_pct,
            "parking_slots": opt.parking_slots,
            "description": opt.description,
            "trade_offs": opt.trade_offs[:2],
        })
    return {
        "site_area": feasibility.site_area,
        "usable_footprint": feasibility.usable_footprint,
        "coverage_pct": feasibility.coverage_pct,
        "fsi_far": feasibility.fsi_far,
        "buildable_area": feasibility.buildable_area,
        "floors": feasibility.floors,
        "options": options_summary,
        "warnings": feasibility.warnings,
        "assumptions": feasibility.assumptions[:2],
    }


# ── Phase 41 — Review / QA tools ─────────────────────────────────────────────


def run_qa_checklist(project_id: str) -> dict:
    """Run the automated QA checklist against the project.

    Checks: validation, room count, rooms inside site, openings, dimensions,
    MEP, details, BOQ completeness, missing rates, export freshness.
    Advisory — verify with a licensed architect.
    """
    from app.core.review.qa_checklist import QAChecker

    proj = _load(project_id)
    checker = QAChecker()
    qa = checker.run(proj)
    return {
        "project_id": project_id,
        "passed": qa.passed,
        "failed": qa.failed,
        "warnings": qa.warnings,
        "completion_pct": qa.completion_pct,
        "items": [item.model_dump() for item in qa.items],
        "advisory": qa.advisory,
    }


def add_review_issue(
    project_id: str,
    title: str,
    category: str = "general",
    description: str = "",
    object_ref: str | None = None,
    priority: str = "medium",
) -> dict:
    """Add a review comment / issue to the project.

    category: spatial | mep | compliance | boq | detail | export | general
    priority: low | medium | high
    """
    from app.core.review.store import get_review_store

    rs = get_review_store()
    issue = rs.create(
        project_id,
        title=title,
        category=category,
        description=description,
        object_ref=object_ref,
        priority=priority,
    )
    return issue.model_dump()


def list_review_issues(project_id: str) -> dict:
    """List all review issues for the project."""
    from app.core.review.store import get_review_store

    rs = get_review_store()
    issues = rs.list(project_id)
    return {
        "total": len(issues),
        "open": sum(1 for i in issues if i.status == "open"),
        "in_progress": sum(1 for i in issues if i.status == "in_progress"),
        "resolved": sum(1 for i in issues if i.status == "resolved"),
        "issues": [i.model_dump() for i in issues],
    }
