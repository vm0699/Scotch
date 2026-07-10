"""Tamil Nadu advisory rule engine — Phase 32.

run_tn_advisory(project, project_id, *, road_width_ft, zone) → TNAdvisoryReport

All results are advisory — not engineering certification.
Every result carries source_name, source_section, confidence, and
needs_professional_verification so the UI can surface these clearly.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.compliance.models import TNAdvisoryReport, TNRuleResult
from app.core.models.project import ArchitectureProject

# ── Source metadata ───────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "regulations" / "tamil_nadu"


def _load_sources() -> dict[str, dict]:
    with open(_DATA_DIR / "sources.json", encoding="utf-8") as f:
        return {s["source_id"]: s for s in json.load(f)}


def _load_rules() -> dict[str, dict]:
    with open(_DATA_DIR / "rules.json", encoding="utf-8") as f:
        return {r["rule_id"]: r for r in json.load(f)}


# ── TN advisory constants (CMDA residential, placeholder values) ──────────────

# Setback by road width (ft) — CMDA DR 2019 Regulation 11 (placeholder)
_TN_SETBACK_TABLE = [
    # (road_width_min_ft, front_ft, side_ft, rear_ft)
    (0,    9.84,  4.92,  9.84),   # road < 23 ft
    (23,   9.84,  4.92,  9.84),   # road 23–39 ft
    (40,  13.12,  4.92,  9.84),   # road 40–59 ft
    (60,  19.69,  6.56, 13.12),   # road ≥ 60 ft
]

_TN_DEFAULT_FSI       = 1.5    # CMDA residential basic (placeholder)
_TN_MAX_COVERAGE_PCT  = 60.0   # CMDA max ground coverage % (placeholder)
_TN_MIN_STAIR_WIDTH   = 3.28   # 1.0 m (CMDA; NBC is 0.9 m)
_RWH_TRIGGER_SQFT     = 2400.0 # Rainwater harvesting mandatory above this plot size

_APPROVAL_DOCS = [
    "Site plan with north direction and dimensions",
    "Floor plans for all levels",
    "Front elevation + at least one section",
    "Structural certificate from licensed structural engineer",
    "Soil test report (required for G+1 and above)",
    "Drainage and water supply NOC from local body",
    "Property ownership document / title deed",
    "Property tax receipt (latest paid)",
    "Identity proof of owner (Aadhaar/PAN)",
    "Architect's licence number and seal",
]


# ── Individual check functions ────────────────────────────────────────────────

def _src(sources: dict, rule: dict) -> tuple[str, str, str]:
    """Return (source_name, source_section, url)."""
    s = sources.get(rule.get("source_id", ""), {})
    return (
        s.get("short_name", rule.get("source_id", "TN Regulations")),
        rule.get("source_section", ""),
        s.get("url_or_path", ""),
    )


def check_site_completeness(
    project: ArchitectureProject,
    road_width_ft: float | None,
    rules: dict,
    sources: dict,
) -> TNRuleResult:
    rule = rules["tn_site_completeness"]
    sname, ssec, surl = _src(sources, rule)
    missing: list[str] = []
    if project.site.width <= 0 or project.site.depth <= 0:
        missing.append("site dimensions (width × depth)")
    if road_width_ft is None or road_width_ft <= 0:
        missing.append("road frontage width")

    if missing:
        return TNRuleResult(
            rule_id=rule["rule_id"], category=rule["category"],
            title=rule["title"], status="missing_input",
            source_name=sname, source_section=ssec, source_url_or_path=surl,
            confidence=rule["confidence"],
            needs_professional_verification=rule["needs_professional_verification"],
            is_placeholder=rule["is_placeholder"],
            missing_inputs=missing,
            message=(
                f"Missing inputs: {'; '.join(missing)}. "
                "Accurate setback and FSI checks require these values — "
                "add them to the project prompt or parameter panel."
            ),
        )
    site_area = project.site.width * project.site.depth
    return TNRuleResult(
        rule_id=rule["rule_id"], category=rule["category"],
        title=rule["title"], status="pass",
        source_name=sname, source_section=ssec, source_url_or_path=surl,
        confidence=rule["confidence"],
        needs_professional_verification=rule["needs_professional_verification"],
        is_placeholder=rule["is_placeholder"],
        value=round(site_area, 1), unit="ft²",
        message=f"Site {project.site.width:.0f} × {project.site.depth:.0f} ft ({site_area:.0f} ft²); "
                f"road width {road_width_ft:.0f} ft — inputs complete for TN checks.",
    )


def check_tn_setbacks(
    project: ArchitectureProject,
    road_width_ft: float | None,
    rules: dict,
    sources: dict,
) -> TNRuleResult:
    rule = rules["tn_setback_advisory"]
    sname, ssec, surl = _src(sources, rule)

    if road_width_ft is None or road_width_ft <= 0:
        return TNRuleResult(
            rule_id=rule["rule_id"], category=rule["category"],
            title=rule["title"], status="missing_input",
            source_name=sname, source_section=ssec, source_url_or_path=surl,
            confidence=rule["confidence"],
            needs_professional_verification=rule["needs_professional_verification"],
            is_placeholder=rule["is_placeholder"],
            missing_inputs=["road_frontage_width"],
            message="Road width not specified — cannot determine TN setback tier. "
                    "Defaulting to NBC setbacks (front 9.84 ft, side 4.92 ft, rear 9.84 ft).",
        )

    # Find applicable tier
    front, side, rear = _TN_SETBACK_TABLE[0][1], _TN_SETBACK_TABLE[0][2], _TN_SETBACK_TABLE[0][3]
    for min_w, f, s, r in _TN_SETBACK_TABLE:
        if road_width_ft >= min_w:
            front, side, rear = f, s, r

    sw = project.site.width
    sd = project.site.depth
    violations: list[str] = []
    for room in project.rooms:
        if room.type == "balcony":
            continue
        if room.x < side - 1e-3:
            violations.append(f"{room.name} (W side {room.x:.1f} ft < {side:.1f} ft)")
        if room.x + room.width > sw - side + 1e-3:
            violations.append(f"{room.name} (E side {room.x + room.width:.1f} ft > {sw - side:.1f} ft)")
        if room.y < front - 1e-3:
            violations.append(f"{room.name} (front {room.y:.1f} ft < {front:.1f} ft)")
        if room.y + room.depth > sd - rear + 1e-3:
            violations.append(f"{room.name} (rear {room.y + room.depth:.1f} ft > {sd - rear:.1f} ft)")

    tier_label = f"road {road_width_ft:.0f} ft → front {front:.1f} ft / side {side:.1f} ft / rear {rear:.1f} ft"
    if violations:
        return TNRuleResult(
            rule_id=rule["rule_id"], category=rule["category"],
            title=rule["title"], status="warn",
            source_name=sname, source_section=ssec, source_url_or_path=surl,
            confidence=rule["confidence"],
            needs_professional_verification=rule["needs_professional_verification"],
            is_placeholder=rule["is_placeholder"],
            message=(
                f"TN setback advisory ({tier_label}): "
                f"{len(violations)} potential encroachment(s). "
                f"First: {violations[0]}. Advisory — verify with CMDA/DTCP."
            ),
        )
    return TNRuleResult(
        rule_id=rule["rule_id"], category=rule["category"],
        title=rule["title"], status="advisory",
        source_name=sname, source_section=ssec, source_url_or_path=surl,
        confidence=rule["confidence"],
        needs_professional_verification=rule["needs_professional_verification"],
        is_placeholder=rule["is_placeholder"],
        message=(
            f"TN setback advisory ({tier_label}): "
            "Rooms appear within setback envelope. Advisory — confirm with licensed architect."
        ),
    )


def check_tn_fsi(
    project: ArchitectureProject,
    rules: dict,
    sources: dict,
) -> TNRuleResult:
    rule = rules["tn_fsi_advisory"]
    sname, ssec, surl = _src(sources, rule)
    site_area = project.site.width * project.site.depth
    if site_area <= 0:
        return TNRuleResult(
            rule_id=rule["rule_id"], category=rule["category"],
            title=rule["title"], status="missing_input",
            source_name=sname, source_section=ssec, source_url_or_path=surl,
            confidence=rule["confidence"],
            needs_professional_verification=rule["needs_professional_verification"],
            is_placeholder=rule["is_placeholder"],
            missing_inputs=["site_dimensions"],
            message="Site area is zero — cannot calculate FSI.",
        )
    built_up = sum(r.width * r.depth for r in project.rooms if r.type not in ("parking", "balcony"))
    fsi = round(built_up / site_area, 3) if site_area > 0 else 0.0
    status: str = "advisory"
    msg = (
        f"Calculated FSI {fsi:.2f} vs. TN residential basic limit {_TN_DEFAULT_FSI} "
        f"(zone classification not specified — using default). "
        "Advisory — confirm FSI zone with CMDA/DTCP."
    )
    if fsi > _TN_DEFAULT_FSI:
        status = "warn"
        msg = (
            f"FSI {fsi:.2f} exceeds TN basic residential limit {_TN_DEFAULT_FSI}. "
            "Higher FSI zones (up to 2.5) require premium payment or TDR. "
            "Advisory — verify your specific zone with CMDA."
        )
    return TNRuleResult(
        rule_id=rule["rule_id"], category=rule["category"],
        title=rule["title"], status=status,  # type: ignore[arg-type]
        source_name=sname, source_section=ssec, source_url_or_path=surl,
        confidence=rule["confidence"],
        needs_professional_verification=rule["needs_professional_verification"],
        is_placeholder=rule["is_placeholder"],
        value=fsi, limit=_TN_DEFAULT_FSI, unit="ratio",
        message=msg,
        missing_inputs=["zone_classification"],
    )


def check_ground_coverage(
    project: ArchitectureProject,
    rules: dict,
    sources: dict,
) -> TNRuleResult:
    rule = rules["tn_ground_coverage"]
    sname, ssec, surl = _src(sources, rule)
    site_area = project.site.width * project.site.depth
    if site_area <= 0:
        return TNRuleResult(
            rule_id=rule["rule_id"], category=rule["category"],
            title=rule["title"], status="missing_input",
            source_name=sname, source_section=ssec, source_url_or_path=surl,
            confidence=rule["confidence"],
            needs_professional_verification=rule["needs_professional_verification"],
            is_placeholder=rule["is_placeholder"],
            missing_inputs=["site_dimensions"],
            message="Site area is zero — cannot calculate ground coverage.",
        )
    # Ground floor footprint = rooms on level 0 (or lowest level)
    level_0_rooms = [r for r in project.rooms if r.level == 0 and r.type not in ("balcony",)]
    footprint = sum(r.width * r.depth for r in level_0_rooms)
    coverage_pct = round(footprint / site_area * 100, 1) if site_area > 0 else 0.0
    limit = _TN_MAX_COVERAGE_PCT
    status = "warn" if coverage_pct > limit else "advisory"
    msg = (
        f"Ground coverage {coverage_pct:.1f}% vs. CMDA max {limit:.0f}% advisory limit. "
        + ("Exceeds advisory limit — review ground floor footprint. " if coverage_pct > limit else "Within advisory limit. ")
        + "Advisory — confirm with licensed architect."
    )
    return TNRuleResult(
        rule_id=rule["rule_id"], category=rule["category"],
        title=rule["title"], status=status,  # type: ignore[arg-type]
        source_name=sname, source_section=ssec, source_url_or_path=surl,
        confidence=rule["confidence"],
        needs_professional_verification=rule["needs_professional_verification"],
        is_placeholder=rule["is_placeholder"],
        value=coverage_pct, limit=limit, unit="%",
        message=msg,
    )


def check_tn_parking(
    project: ArchitectureProject,
    rules: dict,
    sources: dict,
) -> TNRuleResult:
    rule = rules["tn_parking_advisory"]
    sname, ssec, surl = _src(sources, rule)
    bedrooms = sum(1 for r in project.rooms if r.type in ("bedroom", "master_bedroom"))
    has_parking = any(r.type == "parking" for r in project.rooms)

    if bedrooms < 2:
        return TNRuleResult(
            rule_id=rule["rule_id"], category=rule["category"],
            title=rule["title"], status="skip",
            source_name=sname, source_section=ssec, source_url_or_path=surl,
            confidence=rule["confidence"],
            needs_professional_verification=rule["needs_professional_verification"],
            is_placeholder=rule["is_placeholder"],
            message="Studio / 1BHK — TN parking norm does not apply.",
        )

    required_cars = 1 if bedrooms == 2 else 2
    status = "advisory" if has_parking else "warn"
    msg = (
        f"CMDA parking advisory: {bedrooms}-bedroom unit → {required_cars} car space(s) + 2 two-wheeler spaces. "
        + ("Parking space found in program. " if has_parking else "No parking room in program — add covered parking. ")
        + "Advisory — confirm two-wheeler spaces with local body."
    )
    return TNRuleResult(
        rule_id=rule["rule_id"], category=rule["category"],
        title=rule["title"], status=status,  # type: ignore[arg-type]
        source_name=sname, source_section=ssec, source_url_or_path=surl,
        confidence=rule["confidence"],
        needs_professional_verification=rule["needs_professional_verification"],
        is_placeholder=rule["is_placeholder"],
        message=msg,
    )


def check_rainwater_harvesting(
    project: ArchitectureProject,
    rules: dict,
    sources: dict,
) -> TNRuleResult:
    rule = rules["tn_rainwater_harvesting"]
    sname, ssec, surl = _src(sources, rule)
    site_area = project.site.width * project.site.depth
    mandatory = site_area >= _RWH_TRIGGER_SQFT
    if not mandatory:
        return TNRuleResult(
            rule_id=rule["rule_id"], category=rule["category"],
            title=rule["title"], status="advisory",
            source_name=sname, source_section=ssec, source_url_or_path=surl,
            confidence=rule["confidence"],
            needs_professional_verification=rule["needs_professional_verification"],
            is_placeholder=rule["is_placeholder"],
            value=round(site_area, 0), limit=_RWH_TRIGGER_SQFT, unit="ft²",
            message=(
                f"Site area {site_area:.0f} ft² < {_RWH_TRIGGER_SQFT:.0f} ft² threshold. "
                "Rainwater harvesting not mandatory under TN rules at this size — but strongly recommended."
            ),
        )
    return TNRuleResult(
        rule_id=rule["rule_id"], category=rule["category"],
        title=rule["title"], status="warn",
        source_name=sname, source_section=ssec, source_url_or_path=surl,
        confidence=rule["confidence"],
        needs_professional_verification=rule["needs_professional_verification"],
        is_placeholder=rule["is_placeholder"],
        value=round(site_area, 0), limit=_RWH_TRIGGER_SQFT, unit="ft²",
        message=(
            f"Site area {site_area:.0f} ft² ≥ {_RWH_TRIGGER_SQFT:.0f} ft². "
            "Rainwater harvesting is MANDATORY under Tamil Nadu law. "
            "Include sump (min 2000 L) and recharge pit (min 1 m diameter) in the design. "
            "Required before plan approval."
        ),
    )


def check_tn_stair(
    project: ArchitectureProject,
    rules: dict,
    sources: dict,
) -> TNRuleResult:
    rule = rules["tn_stair_advisory"]
    sname, ssec, surl = _src(sources, rule)
    min_w = rule.get("min_width_ft", _TN_MIN_STAIR_WIDTH)
    stair_rooms = [r for r in project.rooms if r.type == "stair"]
    if not stair_rooms:
        if project.building.floors <= 1:
            return TNRuleResult(
                rule_id=rule["rule_id"], category=rule["category"],
                title=rule["title"], status="skip",
                source_name=sname, source_section=ssec, source_url_or_path=surl,
                confidence=rule["confidence"],
                needs_professional_verification=rule["needs_professional_verification"],
                is_placeholder=rule["is_placeholder"],
                message="Single-floor building — staircase advisory not applicable.",
            )
        return TNRuleResult(
            rule_id=rule["rule_id"], category=rule["category"],
            title=rule["title"], status="warn",
            source_name=sname, source_section=ssec, source_url_or_path=surl,
            confidence=rule["confidence"],
            needs_professional_verification=rule["needs_professional_verification"],
            is_placeholder=rule["is_placeholder"],
            message=(
                f"Multi-floor building ({project.building.floors} floors) but no staircase in program. "
                f"CMDA advisory: stair width ≥ {min_w:.2f} ft (1.0 m) — include staircase room."
            ),
        )
    narrow = min(min(r.width, r.depth) for r in stair_rooms)
    ok = narrow >= min_w
    return TNRuleResult(
        rule_id=rule["rule_id"], category=rule["category"],
        title=rule["title"], status="advisory" if ok else "warn",
        source_name=sname, source_section=ssec, source_url_or_path=surl,
        confidence=rule["confidence"],
        needs_professional_verification=rule["needs_professional_verification"],
        is_placeholder=rule["is_placeholder"],
        value=round(narrow, 2), limit=min_w, unit="ft",
        message=(
            f"Stair width {narrow:.2f} ft — CMDA advisory min {min_w:.2f} ft (1.0 m). "
            + ("Width adequate. " if ok else "Below CMDA advisory minimum. ")
            + "Advisory — verify handrail requirement for width > 1.2 m."
        ),
    )


def check_approval_checklist(
    project: ArchitectureProject,
    rules: dict,
    sources: dict,
) -> TNRuleResult:
    rule = rules["tn_approval_checklist"]
    sname, ssec, surl = _src(sources, rule)
    docs = rule.get("required_documents", _APPROVAL_DOCS)
    floors = project.building.floors
    # Mark soil test as required if multi-floor
    advisory_items = list(docs)
    if floors <= 1:
        advisory_items = [d for d in advisory_items if "soil test" not in d.lower()]
        advisory_items.append("Soil test report (optional for G+0 but recommended)")
    return TNRuleResult(
        rule_id=rule["rule_id"], category=rule["category"],
        title=rule["title"], status="advisory",
        source_name=sname, source_section=ssec, source_url_or_path=surl,
        confidence=rule["confidence"],
        needs_professional_verification=rule["needs_professional_verification"],
        is_placeholder=rule["is_placeholder"],
        advisory_items=advisory_items,
        message=(
            f"CMDA/Corporation building plan approval typically requires {len(advisory_items)} documents. "
            "Advisory — confirm the current list with the local authority before submission."
        ),
    )


# ── Main entry point ─────────────────────────────────────────────────────────

def run_tn_advisory(
    project: ArchitectureProject,
    project_id: str,
    *,
    road_width_ft: float | None = None,
    zone: str = "residential_basic",
) -> TNAdvisoryReport:
    """Run all TN advisory checks and return a TNAdvisoryReport.

    All results are advisory (not engineering certification).
    road_width_ft: frontage road width in feet (None = missing input).
    """
    sources = _load_sources()
    rules = _load_rules()

    results: list[TNRuleResult] = [
        check_site_completeness(project, road_width_ft, rules, sources),
        check_tn_setbacks(project, road_width_ft, rules, sources),
        check_tn_fsi(project, rules, sources),
        check_ground_coverage(project, rules, sources),
        check_tn_parking(project, rules, sources),
        check_rainwater_harvesting(project, rules, sources),
        check_tn_stair(project, rules, sources),
        check_approval_checklist(project, rules, sources),
    ]

    missing_inputs = []
    for r in results:
        missing_inputs.extend(r.missing_inputs)
    missing_inputs = list(dict.fromkeys(missing_inputs))  # deduplicate preserving order

    hard_warns = [r for r in results if r.status in ("fail", "warn")]
    passes_advisory = len(hard_warns) == 0

    if passes_advisory:
        summary = (
            f"No hard advisory warnings for Tamil Nadu. "
            f"{len(missing_inputs)} input(s) missing for full analysis. "
            "Advisory only — professional verification required."
        )
    else:
        summary = (
            f"{len(hard_warns)} TN advisory warning(s) require attention. "
            f"{len(missing_inputs)} missing input(s). "
            "Advisory only — professional verification required."
        )

    return TNAdvisoryReport(
        project_id=project_id,
        passes_advisory=passes_advisory,
        summary=summary,
        results=results,
        missing_inputs=missing_inputs,
    )
