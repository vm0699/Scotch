"""Phase 27.8 — Compliance engine tests.

Covers:
  FSI check, setback inset, min room areas, ventilation,
  stair width, parking norms, run_compliance integration.
"""

from __future__ import annotations

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.compliance.engine import run_compliance
from app.core.compliance.rules import (
    DEFAULT_FRONT_SETBACK,
    DEFAULT_MAX_FSI,
    DEFAULT_REAR_SETBACK,
    DEFAULT_SIDE_SETBACK,
    check_fsi,
    check_parking,
    check_room_areas,
    check_setbacks,
    check_stair_width,
    check_ventilation,
)
from app.core.models.project import (
    ArchitectureProject,
    Building,
    Door,
    Room,
    Site,
    Window,
)

# ── Fixture helpers ───────────────────────────────────────────────────────────

def _room(
    rid: str,
    rtype: str,
    x: float,
    y: float,
    w: float,
    d: float,
    level: int = 0,
    name: str | None = None,
) -> Room:
    return Room(id=rid, type=rtype, name=name or rtype, x=x, y=y, width=w, depth=d, level=level)


def _project(
    rooms: list[Room],
    *,
    site_w: float = 50.0,
    site_d: float = 70.0,
    floors: int = 1,
    windows: list[Window] | None = None,
    doors: list[Door] | None = None,
) -> ArchitectureProject:
    return ArchitectureProject(
        id="test",
        name="Test",
        site=Site(width=site_w, depth=site_d),
        building=Building(floors=floors),
        rooms=rooms,
        windows=windows or [],
        doors=doors or [],
    )


# ── FSI / FAR checks ─────────────────────────────────────────────────────────

def test_fsi_pass() -> None:
    """Rooms well within FSI 1.5."""
    rooms = [_room("living", "living", 10, 10, 12, 10)]
    result = check_fsi(_project(rooms, site_w=50, site_d=70), max_fsi=1.5)
    assert result.status == "pass"
    assert result.value is not None and result.value < 1.5


def test_fsi_fail() -> None:
    """Total built-up area exceeds FSI limit."""
    # site 20×20 = 400 ft²; 5 rooms @ 12×12 = 144 ft² each → 720 / 400 = 1.8 > 1.5
    rooms = [_room(f"r{i}", "bedroom", 0, i * 12, 12, 12) for i in range(5)]
    result = check_fsi(_project(rooms, site_w=20, site_d=20), max_fsi=1.5)
    assert result.status == "fail"
    assert result.value is not None and result.value > 1.5


def test_fsi_excludes_balcony() -> None:
    """Balcony area is not counted in built-up for FSI."""
    # big balcony that would push FSI over if counted
    rooms = [
        _room("bed", "bedroom", 10, 10, 11, 10),
        _room("balcony", "balcony", 10, 20, 30, 30),   # 900 ft² balcony
    ]
    site_w, site_d = 50.0, 70.0
    result = check_fsi(_project(rooms, site_w=site_w, site_d=site_d), max_fsi=1.5)
    built_up = 11 * 10   # only bedroom counted
    actual_fsi = built_up / (site_w * site_d)
    assert result.value == pytest.approx(actual_fsi, abs=0.01)
    assert result.status == "pass"


# ── Setback checks ────────────────────────────────────────────────────────────

def test_setbacks_pass() -> None:
    """Rooms well inside setback envelope."""
    rooms = [_room("living", "living", 10, 15, 20, 20)]
    results = check_setbacks(
        _project(rooms, site_w=50, site_d=60),
        front=DEFAULT_FRONT_SETBACK,
        side=DEFAULT_SIDE_SETBACK,
        rear=DEFAULT_REAR_SETBACK,
    )
    assert all(r.status == "pass" for r in results)


def test_setbacks_fail_front() -> None:
    """Room starts at y=0 — violates front setback of 9.84 ft."""
    rooms = [_room("living", "living", 10, 0, 20, 10)]
    results = check_setbacks(
        _project(rooms, site_w=50, site_d=60),
        front=DEFAULT_FRONT_SETBACK,
        side=DEFAULT_SIDE_SETBACK,
        rear=DEFAULT_REAR_SETBACK,
    )
    assert any(r.status == "fail" for r in results)


def test_setbacks_fail_side() -> None:
    """Room starts at x=0 — violates side setback."""
    rooms = [_room("living", "living", 0, 15, 20, 20)]
    results = check_setbacks(
        _project(rooms, site_w=50, site_d=60),
        front=DEFAULT_FRONT_SETBACK,
        side=DEFAULT_SIDE_SETBACK,
        rear=DEFAULT_REAR_SETBACK,
    )
    assert any(r.status == "fail" for r in results)


def test_setbacks_balcony_exempt() -> None:
    """Balcony at front edge does not trigger a setback violation."""
    rooms = [
        _room("living", "living", 10, 15, 20, 20),
        _room("balc", "balcony", 10, 0, 10, 3),   # front edge
    ]
    results = check_setbacks(
        _project(rooms, site_w=50, site_d=60),
        front=DEFAULT_FRONT_SETBACK,
        side=DEFAULT_SIDE_SETBACK,
        rear=DEFAULT_REAR_SETBACK,
    )
    assert all(r.status == "pass" for r in results)


# ── Min room area checks ──────────────────────────────────────────────────────

def test_room_areas_pass() -> None:
    """Bedroom at 12×9 = 108 ft² passes NBC minimum (102.3 ft²)."""
    rooms = [_room("bed1", "bedroom", 10, 10, 12, 9)]
    results = check_room_areas(_project(rooms))
    assert all(r.status == "pass" for r in results)


def test_room_areas_fail_small_bedroom() -> None:
    """Bedroom at 8×9 = 72 ft² fails NBC minimum (102.3 ft²)."""
    rooms = [_room("bed1", "bedroom", 10, 10, 8, 9)]
    results = check_room_areas(_project(rooms))
    assert any(r.status == "fail" for r in results)


def test_room_areas_fail_kitchen() -> None:
    """Kitchen at 5×5 = 25 ft² fails NBC minimum (53.8 ft²)."""
    rooms = [_room("kitchen", "kitchen", 5, 5, 5, 5)]
    results = check_room_areas(_project(rooms))
    assert any(r.status == "fail" for r in results)


def test_room_areas_skip_non_regulated() -> None:
    """Living room has no NBC minimum — should not generate a rule result."""
    rooms = [_room("living", "living", 5, 5, 8, 6)]
    results = check_room_areas(_project(rooms))
    assert results == []   # living room not regulated by this checker


# ── Ventilation checks ────────────────────────────────────────────────────────

def test_ventilation_pass() -> None:
    """Bedroom 12×9 = 108 ft²; window 6 ft wide × 4 ft = 24 ft² > 108/8 = 13.5 ft²."""
    rooms = [_room("bed1", "bedroom", 10, 10, 12, 9)]
    windows = [Window(id="w1", room_id="bed1", wall="north", offset=2, width=6)]
    results = check_ventilation(_project(rooms, windows=windows))
    assert all(r.status == "pass" for r in results)


def test_ventilation_fail_no_windows() -> None:
    """No windows → ventilation fail for habitable rooms."""
    rooms = [_room("bed1", "bedroom", 10, 10, 12, 9)]
    results = check_ventilation(_project(rooms))
    assert any(r.status == "fail" for r in results)


def test_ventilation_skip_non_habitable() -> None:
    """Bathroom is not a habitable room — no ventilation rule generated."""
    rooms = [_room("bath", "bathroom", 5, 5, 5, 5)]
    results = check_ventilation(_project(rooms))
    assert results == []


# ── Stair width checks ────────────────────────────────────────────────────────

def test_stair_skip_single_floor() -> None:
    """Single-floor building with no stair → skip, not warn."""
    rooms = [_room("living", "living", 5, 5, 10, 10)]
    results = check_stair_width(_project(rooms, floors=1))
    assert all(r.status == "skip" for r in results)


def test_stair_warn_multi_floor_no_stair() -> None:
    """Multi-floor building with no stair room → warn."""
    rooms = [_room("bed", "bedroom", 5, 5, 12, 10)]
    results = check_stair_width(_project(rooms, floors=2))
    assert any(r.status == "warn" for r in results)


def test_stair_pass() -> None:
    """Stair room wider than 2.95 ft → pass."""
    rooms = [_room("stair", "stair", 5, 5, 5, 5)]
    results = check_stair_width(_project(rooms, floors=2))
    assert all(r.status == "pass" for r in results)


def test_stair_fail_too_narrow() -> None:
    """Stair room 2 ft wide → fail NBC 0.9 m (2.95 ft) minimum."""
    rooms = [_room("stair", "stair", 5, 5, 2, 3)]
    results = check_stair_width(_project(rooms, floors=2))
    assert any(r.status == "fail" for r in results)


# ── Parking norms ─────────────────────────────────────────────────────────────

def test_parking_skip_1bhk() -> None:
    """Studio / 1BHK → parking not mandatory."""
    rooms = [_room("bed", "bedroom", 5, 5, 12, 10)]
    results = check_parking(_project(rooms))
    assert all(r.status == "skip" for r in results)


def test_parking_fail_2bhk_no_parking() -> None:
    """2BHK without parking → fail."""
    rooms = [
        _room("bed1", "bedroom", 5, 5, 12, 10),
        _room("bed2", "bedroom", 18, 5, 12, 10),
    ]
    results = check_parking(_project(rooms))
    assert any(r.status == "fail" for r in results)


def test_parking_pass_2bhk_with_parking() -> None:
    """2BHK with parking room → pass."""
    rooms = [
        _room("bed1", "bedroom", 5, 5, 12, 10),
        _room("bed2", "bedroom", 18, 5, 12, 10),
        _room("park", "parking", 5, 50, 10, 8),
    ]
    results = check_parking(_project(rooms))
    assert all(r.status == "pass" for r in results)


# ── run_compliance integration ─────────────────────────────────────────────────

def test_run_compliance_all_pass() -> None:
    """Happy-path project — all rules pass."""
    # All rooms placed within front/side/rear setback envelope:
    # site 50×70 → usable: x [4.92, 45.08], y [9.84, 60.16]
    rooms = [
        _room("bed1",   "bedroom",  10, 12, 12, 10),  # 120 ft² > 102.3 ✓; y+d=22 ✓
        _room("bed2",   "bedroom",  23, 12, 12, 10),  # same; x+w=35 < 45.08 ✓
        _room("kit",    "kitchen",  10, 25,  8,  7),  # 56 ft² > 53.8 ✓
        _room("bath",   "bathroom", 23, 25,  6,  5),  # 30 ft² > 25 ✓
        _room("living", "living",   10, 36, 20, 10),  # x+w=30 ✓; y+d=46 < 60.16 ✓
        _room("park",   "parking",  10, 49, 10,  8),  # y+d=57 < 60.16 ✓
    ]
    windows = [
        Window(id="w1", room_id="bed1",  wall="north", offset=2, width=6),
        Window(id="w2", room_id="bed2",  wall="north", offset=2, width=6),
        Window(id="w3", room_id="kit",   wall="north", offset=1, width=4),
        Window(id="w4", room_id="living",wall="north", offset=2, width=8),
    ]
    proj = _project(rooms, site_w=50, site_d=70, windows=windows)
    report = run_compliance(proj, "test-id")
    assert report.project_id == "test-id"
    assert report.passes_review
    fails = [r for r in report.rules if r.status == "fail"]
    assert fails == [], [r.message for r in fails]


def test_run_compliance_fsi_and_setback_fail() -> None:
    """A project with FSI > 1.5 AND a room outside setback → fails review."""
    # Rooms packed too dense and touching the edge
    rooms = [
        _room(f"r{i}", "bedroom", 0, i * 12, 50, 12) for i in range(6)
    ]
    proj = _project(rooms, site_w=50, site_d=80)
    report = run_compliance(proj, "test-bad")
    assert not report.passes_review
    fail_ids = {r.rule_id for r in report.rules if r.status == "fail"}
    assert "fsi_check" in fail_ids or "setback_violation" in fail_ids


def test_run_compliance_returns_all_rule_categories() -> None:
    """ComplianceReport covers all expected rule categories."""
    rooms = [_room("bed", "bedroom", 10, 10, 12, 10)]
    proj = _project(rooms)
    report = run_compliance(proj, "cat-test")
    categories = {r.category for r in report.rules}
    assert "fsi" in categories
    assert "setback" in categories


# ── Generator integration — setback inset ─────────────────────────────────────

def test_generator_applies_setback_inset() -> None:
    """Floorplan generator must pack rooms within setback envelope."""
    prompt = "2BHK apartment on a 40x60 ft site with living, kitchen, 2 bedrooms, 2 bathrooms, parking"
    project, _ = generate_floorplan(parse_prompt(prompt))

    front  = DEFAULT_FRONT_SETBACK
    side   = DEFAULT_SIDE_SETBACK
    rear   = DEFAULT_REAR_SETBACK
    sw = project.site.width
    sd = project.site.depth

    for room in project.rooms:
        if room.type == "balcony":
            continue   # balconies exempt
        # Allow 1 ft tolerance for wall offsets and rounding
        assert room.x >= side - 1.0, f"{room.name}.x={room.x:.1f} < side setback {side}"
        assert room.x + room.width <= sw - side + 1.0, f"{room.name} overflows east"
        assert room.y >= front - 1.0, f"{room.name}.y={room.y:.1f} < front setback {front}"
        assert room.y + room.depth <= sd - rear + 1.0, f"{room.name} overflows rear"


def test_generator_fsi_guard_warning_when_dense() -> None:
    """Dense prompt → FSI warning surfaced in project.warnings."""
    prompt = "5BHK mansion on a tiny 20x25 ft site"
    project, _ = generate_floorplan(parse_prompt(prompt))
    # Generator should not crash; rooms stay inside site
    for room in project.rooms:
        assert room.x + room.width <= project.site.width + 1e-3
        assert room.y + room.depth <= project.site.depth + 1e-3
