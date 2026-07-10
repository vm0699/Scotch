"""India NBC compliance rules — Phase 27.1.

Default byelaw values (urban residential, NBC 2016):
  FSI / FAR  : 1.5  (city residential zone; varies 1.0–2.5)
  Front setback : 3 m ≈ 9.84 ft
  Side setback  : 1.5 m ≈ 4.92 ft  (each side; total 9.84 ft width reduction)
  Rear setback  : 3 m ≈ 9.84 ft

Minimum room areas (NBC Part 4, Section 5):
  Bedroom (habitable)  : 9.5 m² ≈ 102.3 ft²
  Kitchen              : 5.0 m² ≈ 53.8 ft²
  Bathroom / WC        : 1.2 m² ≈ 12.9 ft² (combined bath ≥ 2.32 m² ≈ 25 ft²)

Ventilation / natural light (NBC Part 8):
  Window area ≥ 1/8 of floor area for habitable rooms

Stair minimum width (NBC Part 4):
  ≥ 0.9 m ≈ 2.95 ft  (residential)

Parking norms (generic urban byelaw):
  1 space required per 2 BHK+ unit
"""

from __future__ import annotations

from app.core.compliance.models import RuleResult
from app.core.models.project import ArchitectureProject, Room

# ── NBC constants (in feet) ───────────────────────────────────────────────────

DEFAULT_FRONT_SETBACK = 9.84    # 3 m
DEFAULT_SIDE_SETBACK  = 4.92    # 1.5 m  per side
DEFAULT_REAR_SETBACK  = 9.84    # 3 m
DEFAULT_MAX_FSI       = 1.5

# Minimum room areas (ft²)
_MIN_AREA_FT2: dict[str, tuple[float, str]] = {
    "bedroom":        (102.3, "102.3 ft² (9.5 m²)"),
    "master_bedroom": (102.3, "102.3 ft² (9.5 m²)"),
    "kitchen":        ( 53.8, " 53.8 ft² (5.0 m²)"),
    "bathroom":       ( 25.0, " 25.0 ft² (2.3 m²)"),
}

# Habitable rooms that require natural ventilation
_HABITABLE = {"bedroom", "master_bedroom", "living", "dining", "study", "studio"}
MIN_VENTILATION_RATIO = 1 / 8   # window area / floor area

MIN_STAIR_WIDTH_FT = 2.95       # 0.9 m


# ── Individual rule checkers ──────────────────────────────────────────────────

def check_fsi(
    project: ArchitectureProject,
    max_fsi: float = DEFAULT_MAX_FSI,
) -> RuleResult:
    site_area = project.site.width * project.site.depth
    built_up  = sum(r.width * r.depth for r in project.rooms
                    if r.type not in ("parking", "balcony"))
    actual_fsi = round(built_up / site_area, 3) if site_area > 0 else 0.0

    if actual_fsi <= max_fsi:
        return RuleResult(
            rule_id="fsi_check", category="fsi",
            description=f"FSI/FAR ≤ {max_fsi} (NBC urban residential)",
            status="pass",
            value=actual_fsi, limit=max_fsi, unit="ratio",
            message=f"Built-up area {built_up:.0f} ft² on {site_area:.0f} ft² site → FSI {actual_fsi:.2f} ≤ {max_fsi}.",
        )
    return RuleResult(
        rule_id="fsi_check", category="fsi",
        description=f"FSI/FAR ≤ {max_fsi} (NBC urban residential)",
        status="fail",
        value=actual_fsi, limit=max_fsi, unit="ratio",
        message=f"FSI {actual_fsi:.2f} exceeds allowed {max_fsi}. Reduce built-up area by "
                f"{built_up - max_fsi * site_area:.0f} ft² or increase site size.",
    )


def check_setbacks(
    project: ArchitectureProject,
    front: float = DEFAULT_FRONT_SETBACK,
    side:  float = DEFAULT_SIDE_SETBACK,
    rear:  float = DEFAULT_REAR_SETBACK,
) -> list[RuleResult]:
    results: list[RuleResult] = []
    sw = project.site.width
    sd = project.site.depth

    # Check that no room intrudes into setback zones
    violations: list[str] = []
    for room in project.rooms:
        if room.type in ("balcony",):
            continue  # balconies may encroach front in some byelaws
        if room.x < side - 1e-3:
            violations.append(f"{room.name} west side ({room.x:.1f} ft < {side:.1f} ft)")
        if room.x + room.width > sw - side + 1e-3:
            violations.append(f"{room.name} east side ({room.x + room.width:.1f} ft > {sw - side:.1f} ft)")
        if room.y < front - 1e-3:
            violations.append(f"{room.name} front ({room.y:.1f} ft < {front:.1f} ft)")
        if room.y + room.depth > sd - rear + 1e-3:
            violations.append(f"{room.name} rear ({room.y + room.depth:.1f} ft > {sd - rear:.1f} ft)")

    if violations:
        results.append(RuleResult(
            rule_id="setback_violation", category="setback",
            description=f"Front {front:.1f} ft, sides {side:.1f} ft, rear {rear:.1f} ft setbacks (NBC)",
            status="fail",
            message=f"Setback violations: {'; '.join(violations[:3])}{'…' if len(violations) > 3 else ''}.",
        ))
    else:
        usable_w = sw - 2 * side
        usable_d = sd - front - rear
        results.append(RuleResult(
            rule_id="setback_check", category="setback",
            description=f"Front {front:.1f} ft, sides {side:.1f} ft, rear {rear:.1f} ft setbacks (NBC)",
            status="pass",
            message=f"All rooms within usable envelope ({usable_w:.1f} × {usable_d:.1f} ft).",
        ))

    return results


def check_room_areas(project: ArchitectureProject) -> list[RuleResult]:
    results: list[RuleResult] = []
    for room in project.rooms:
        rt = room.type.lower()
        if rt not in _MIN_AREA_FT2:
            continue
        min_area, limit_label = _MIN_AREA_FT2[rt]
        actual = round(room.width * room.depth, 1)
        if actual < min_area:
            results.append(RuleResult(
                rule_id=f"room_area_{room.id}", category="room_area",
                description=f"Min area for {room.type} ≥ {limit_label}",
                status="fail",
                value=actual, limit=round(min_area, 1), unit="ft²",
                message=f"{room.name} is {actual} ft² — below NBC minimum {limit_label}.",
            ))
        else:
            results.append(RuleResult(
                rule_id=f"room_area_{room.id}", category="room_area",
                description=f"Min area for {room.type} ≥ {limit_label}",
                status="pass",
                value=actual, limit=round(min_area, 1), unit="ft²",
                message=f"{room.name}: {actual} ft² ✓",
            ))
    return results


def check_ventilation(
    project: ArchitectureProject,
) -> list[RuleResult]:
    """Window area ≥ 1/8 floor area for habitable rooms (NBC Part 8)."""
    results: list[RuleResult] = []
    windows_by_room: dict[str, float] = {}
    for win in project.windows:
        windows_by_room[win.room_id] = windows_by_room.get(win.room_id, 0.0) + win.width

    for room in project.rooms:
        if room.type.lower() not in _HABITABLE:
            continue
        floor_area = room.width * room.depth
        win_area   = windows_by_room.get(room.id, 0.0) * 4.0  # approx: win_width × 4 ft height
        required   = floor_area * MIN_VENTILATION_RATIO
        ratio      = round(win_area / floor_area, 3) if floor_area > 0 else 0.0

        if win_area >= required - 1e-3:
            results.append(RuleResult(
                rule_id=f"ventilation_{room.id}", category="ventilation",
                description=f"Window area ≥ 1/8 floor area for {room.name}",
                status="pass",
                value=round(win_area, 1), limit=round(required, 1), unit="ft²",
                message=f"{room.name}: window area {win_area:.1f} ft² ≥ required {required:.1f} ft² ✓",
            ))
        else:
            results.append(RuleResult(
                rule_id=f"ventilation_{room.id}", category="ventilation",
                description=f"Window area ≥ 1/8 floor area for {room.name}",
                status="fail" if win_area == 0 else "warn",
                value=round(win_area, 1), limit=round(required, 1), unit="ft²",
                message=f"{room.name}: window area {win_area:.1f} ft² < required {required:.1f} ft² "
                        f"(1/8 of {floor_area:.0f} ft²).",
            ))
    return results


def check_stair_width(project: ArchitectureProject) -> list[RuleResult]:
    stair_rooms = [r for r in project.rooms if r.type == "stair"]
    if not stair_rooms:
        if project.building.floors <= 1:
            return [RuleResult(
                rule_id="stair_width", category="stair",
                description=f"Stair width ≥ {MIN_STAIR_WIDTH_FT:.2f} ft (0.9 m) for multi-floor (NBC)",
                status="skip",
                message="Single-floor building — no stair required.",
            )]
        return [RuleResult(
            rule_id="stair_width", category="stair",
            description=f"Stair width ≥ {MIN_STAIR_WIDTH_FT:.2f} ft (0.9 m) for multi-floor (NBC)",
            status="warn",
            message="Multi-floor building but no staircase room found in the program.",
        )]

    results: list[RuleResult] = []
    for stair in stair_rooms:
        narrower = min(stair.width, stair.depth)
        ok = narrower >= MIN_STAIR_WIDTH_FT
        results.append(RuleResult(
            rule_id=f"stair_width_{stair.id}", category="stair",
            description=f"Stair width ≥ {MIN_STAIR_WIDTH_FT:.2f} ft (0.9 m) (NBC)",
            status="pass" if ok else "fail",
            value=round(narrower, 2), limit=MIN_STAIR_WIDTH_FT, unit="ft",
            message=f"{stair.name}: {narrower:.1f} ft {'✓' if ok else '— below NBC 0.9 m minimum'}.",
        ))
    return results


def check_parking(project: ArchitectureProject) -> list[RuleResult]:
    """1 parking space required per residential unit with 2+ bedrooms."""
    bedrooms = sum(1 for r in project.rooms if r.type in ("bedroom", "master_bedroom"))
    has_parking = any(r.type == "parking" for r in project.rooms)
    required = bedrooms >= 2

    if not required:
        return [RuleResult(
            rule_id="parking_norm", category="parking",
            description="Parking norm: 1 space for 2BHK+ residential units",
            status="skip",
            message="Studio / 1BHK — parking not mandatory under this norm.",
        )]

    if has_parking:
        return [RuleResult(
            rule_id="parking_norm", category="parking",
            description="Parking norm: 1 space for 2BHK+ residential units",
            status="pass",
            message=f"{bedrooms}-bedroom unit has a parking space ✓",
        )]
    return [RuleResult(
        rule_id="parking_norm", category="parking",
        description="Parking norm: 1 space for 2BHK+ residential units",
        status="fail",
        message=f"{bedrooms}-bedroom unit requires at least 1 parking space (not in program).",
    )]
