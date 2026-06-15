"""Stage 17.3 — Camera suggestions derived from ArchitectureProject geometry.

Produces 5 CameraSuggestion presets from site dimensions and room positions.

Coordinate convention for position / target:
    [plan_x, height, plan_y]

This maps directly to three.js [x, y, z] (no transform needed).
For Blender (Z-up): plan_x → X, plan_y → Y, height → Z  (multiply by FT_TO_M).

All values are in project units (feet when units == "feet").
"""

from app.core.models import ArchitectureProject, CameraSuggestion


def derive_cameras(project: ArchitectureProject) -> list[CameraSuggestion]:
    """Return 5 camera presets derived from *project* geometry."""
    sw = project.site.width
    sd = project.site.depth
    fh = project.building.floor_height if project.building else 10.0
    cx = sw / 2.0   # plan x centre
    cy = sd / 2.0   # plan y centre
    eye_h = 5.5     # average human eye height in feet

    cameras: list[CameraSuggestion] = []

    # ── 1. Exterior 3/4 view ─────────────────────────────────────────────────
    # NE corner (negative plan_y = north of entrance), elevated.
    cameras.append(CameraSuggestion(
        name="exterior_quarter",
        type="perspective",
        position=[sw * 1.5,  fh * 1.3, -sd * 0.7],
        target=[cx,          fh * 0.35, cy],
        fov=45,
        description="Exterior 3/4 view from north-east corner",
    ))

    # ── 2. Top orthographic plan ─────────────────────────────────────────────
    cameras.append(CameraSuggestion(
        name="top_ortho",
        type="orthographic",
        position=[cx, fh * 4.5, cy],
        target=[cx, 0.0,         cy],
        fov=0,
        description="Top-down orthographic plan view",
    ))

    # ── 3. Street-level eye from entrance side ───────────────────────────────
    # plan_y=0 is the entrance edge; camera is slightly outside (negative plan_y).
    cameras.append(CameraSuggestion(
        name="street_eye",
        type="perspective",
        position=[cx,    eye_h,     -sd * 0.3],
        target=[cx,      fh * 0.45, cy * 0.6],
        fov=60,
        description="Street-level perspective from entrance / north side",
    ))

    # ── 4. Living-room interior ──────────────────────────────────────────────
    living = next(
        (r for r in project.rooms if "living" in r.type.lower()), None
    ) or (project.rooms[0] if project.rooms else None)

    if living:
        lx = living.x + living.width / 2
        ly = living.y + living.depth / 2
        cameras.append(CameraSuggestion(
            name="living_interior",
            type="perspective",
            position=[lx - living.width * 0.28, eye_h, ly - living.depth * 0.28],
            target=[lx  + living.width * 0.15,  eye_h * 0.85, ly + living.depth * 0.15],
            fov=75,
            description="Interior view from living room",
        ))

    # ── 5. Balcony view / exterior corner ────────────────────────────────────
    balcony = next(
        (r for r in project.rooms if "balcony" in r.type.lower()), None
    )
    if balcony:
        bx = balcony.x + balcony.width / 2
        by = balcony.y + balcony.depth / 2
        cameras.append(CameraSuggestion(
            name="balcony_view",
            type="perspective",
            position=[bx, fh * 0.65, by],
            target=[cx,  fh * 0.3,   cy],
            fov=65,
            description="View from balcony looking into building",
        ))
    else:
        # NW exterior corner fallback
        cameras.append(CameraSuggestion(
            name="corner_exterior",
            type="perspective",
            position=[-sw * 0.25, fh * 0.9, -sd * 0.25],
            target=[cx, fh * 0.35, cy],
            fov=55,
            description="Exterior view from north-west corner",
        ))

    return cameras
