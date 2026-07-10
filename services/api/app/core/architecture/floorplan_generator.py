"""DesignRequirements → ArchitectureProject.

Deterministic rule-based layout on a rectangular site using zoned bands
along the depth axis (y = 0 is the entrance edge):

    front band   — parking, living/seating, balcony   (public zone)
    service band — kitchen, dining, common bath, study, storage
    private bands — bedrooms with attached baths      (residential)

Rooms are packed left-to-right per band at their default sizes, wrapping to
a new band when the site width runs out. Oversized rooms are clamped to the
site with a warning; if the program is deeper than the site, all bands are
compressed proportionally with a warning. Every imperfection is surfaced —
never silently fixed.
"""

from dataclasses import dataclass, field

from app.core.architecture.defaults import DEFAULT_FLOOR_HEIGHT, default_size
from app.core.architecture.furniture_placer import place_all_furniture
from app.core.architecture.materials import assign_default_materials
from app.core.architecture.requirement_parser import DesignRequirements
from app.core.models import (
    ArchitectureProject,
    Building,
    Door,
    Level,
    Parameter,
    ProjectWarning,
    Room,
    Site,
    Window,
)

MIN_ROOM_DIM = 4.0
GAP = 0.0  # rooms share walls; poché rendering handles the joint
_STAIR_W = 8.0
_STAIR_D = 8.0


@dataclass
class _Spec:
    """A room the program wants, before it has a position."""

    id: str
    name: str
    type: str
    width: float
    depth: float


@dataclass
class _GenState:
    warnings: list[ProjectWarning] = field(default_factory=list)

    def warn(self, wid: str, message: str, severity: str = "warning") -> None:
        self.warnings.append(ProjectWarning(id=wid, severity=severity, message=message))


def _stair_spec(level_index: int) -> _Spec:
    label = "G" if level_index == 0 else str(level_index)
    return _Spec(
        id=f"stair-{label.lower()}",
        name="Staircase",
        type="stair",
        width=_STAIR_W,
        depth=_STAIR_D,
    )


def _spec(room_id: str, name: str, room_type: str, size_key: str) -> _Spec:
    width, depth = default_size(size_key)
    return _Spec(id=room_id, name=name, type=room_type, width=width, depth=depth)


def _residential_program(req: DesignRequirements, state: _GenState) -> list[list[_Spec]]:
    front: list[_Spec] = []
    if req.parking:
        front.append(_spec("parking", "Parking", "parking", "parking"))
    if req.building_kind == "studio":
        front.append(_spec("studio", "Studio", "living", "studio_room"))
    else:
        front.append(_spec("living", "Living Room", "living", "living"))
    if req.balcony:
        front.append(_spec("balcony", "Balcony", "balcony", "balcony"))

    service: list[_Spec] = []
    service.append(
        _spec(
            "kitchen",
            "Kitchenette" if req.building_kind == "studio" else "Kitchen",
            "kitchen",
            "kitchenette" if req.building_kind == "studio" else "kitchen",
        )
    )
    if req.dining:
        service.append(_spec("dining", "Dining", "dining", "dining"))
    baths_left = req.bathrooms
    if baths_left > 0:
        service.append(_spec("bath-1", "Common Bath", "bathroom", "bathroom"))
        baths_left -= 1
    if req.study:
        service.append(_spec("study", "Study", "study", "study"))
    if req.storage:
        service.append(_spec("storage", "Storage", "storage", "storage"))

    # Private zone: master first, attached baths interleaved after bedrooms.
    private: list[_Spec] = []
    for i in range(req.bedrooms):
        if i == 0:
            private.append(_spec("bed-master", "Master Bedroom", "bedroom", "master_bedroom"))
        else:
            private.append(_spec(f"bed-{i + 1}", f"Bedroom {i + 1}", "bedroom", "bedroom"))
        if baths_left > 0:
            bath_id = f"bath-{req.bathrooms - baths_left + 1}"
            label = "Attached Bath" if i == 0 else f"Bath {req.bathrooms - baths_left + 1}"
            private.append(_spec(bath_id, label, "bathroom", "bathroom"))
            baths_left -= 1

    bands = [band for band in (front, service, private) if band]
    return bands


def _cafe_program(req: DesignRequirements, state: _GenState) -> list[list[_Spec]]:
    seating_w = max(MIN_ROOM_DIM, req.site_width)
    seating_d = max(10.0, min(16.0, req.site_depth * 0.38))
    seating = _Spec(id="seating", name="Seating Area", type="cafe_seating", width=seating_w, depth=seating_d)
    service = [
        _spec("counter", "Service Counter", "cafe_counter", "cafe_counter"),
        _spec("kitchen", "Kitchen", "kitchen", "cafe_kitchen"),
    ]
    back = [_spec("storage", "Storage", "storage", "storage"),
            _spec("restroom", "Restroom", "bathroom", "restroom")]
    return [[seating], service, back]


def _office_fallback_program(req: DesignRequirements, state: _GenState) -> list[list[_Spec]]:
    state.warn(
        "warn-office-fallback",
        "Detailed office layouts arrive in a later phase — generated a generic open-plan layout instead.",
        severity="info",
    )
    open_w = max(MIN_ROOM_DIM, min(req.site_width, 40.0))
    open_d = max(12.0, min(req.site_depth * 0.45, 30.0))
    open_plan = _Spec(id="open-plan", name="Open Workspace", type="office", width=open_w, depth=open_d)
    back = [_spec("storage", "Storage", "storage", "storage"),
            _spec("restroom", "Restroom", "bathroom", "restroom")]
    return [[open_plan], back]


def _pack_bands(
    bands: list[list[_Spec]], site_width: float, site_depth: float, state: _GenState,
    level: int = 0,
) -> list[Room]:
    """Place specs left-to-right per band, wrapping when width runs out."""
    placed: list[Room] = []
    rows: list[list[_Spec]] = []

    for band in bands:
        row: list[_Spec] = []
        x = 0.0
        for spec in band:
            if spec.width > site_width:
                state.warn(
                    f"warn-clamp-{spec.id}",
                    f"{spec.name} ({spec.width:g} ft) is wider than the site — clamped to {site_width:g} ft.",
                )
                spec.width = site_width
            if x + spec.width > site_width + 1e-9:
                rows.append(row)
                row = []
                x = 0.0
            row.append(spec)
            x += spec.width + GAP
        if row:
            rows.append(row)

    total_depth = sum(max(s.depth for s in row) for row in rows)
    scale = 1.0
    if total_depth > site_depth:
        scale = site_depth / total_depth
        state.warn(
            "warn-depth-compressed",
            f"The program needs {total_depth:g} ft of depth but the site has "
            f"{site_depth:g} ft — room depths compressed by {round((1 - scale) * 100)}%.",
        )

    y = 0.0
    for row in rows:
        row_depth = max(s.depth for s in row) * scale
        x = 0.0
        for spec in row:
            depth = max(MIN_ROOM_DIM, round(spec.depth * scale, 1))
            placed.append(
                Room(
                    id=spec.id,
                    name=spec.name,
                    type=spec.type,
                    x=round(x, 1),
                    y=round(y, 1),
                    width=round(spec.width, 1),
                    depth=min(depth, round(row_depth, 1)),
                    level=level,
                )
            )
            x += spec.width + GAP
        y += row_depth

    return placed


def _openings(
    rooms: list[Room], site_width: float, state: _GenState
) -> tuple[list[Door], list[Window]]:
    doors: list[Door] = []
    windows: list[Window] = []
    built_depth = max((r.y + r.depth for r in rooms), default=0.0)

    entry_room = next(
        (r for r in rooms if r.type in ("living", "cafe_seating", "office")),
        rooms[0] if rooms else None,
    )

    for room in rooms:
        # Doors: entrance on the entry room, north (corridor-side) door elsewhere.
        if room.type != "parking":
            width = 3.5 if room is entry_room else (2.5 if room.type in ("bathroom", "storage") else 3.0)
            width = min(width, max(2.0, room.width - 1.0))
            offset = round(max(0.5, (room.width - width) / 2 if room is entry_room else 1.0), 1)
            doors.append(
                Door(
                    id=f"door-{room.id}",
                    room_id=room.id,
                    wall="north",
                    offset=offset,
                    width=width,
                )
            )

        # Windows on exterior walls (site perimeter / rear of the built mass).
        if room.type in ("parking", "storage"):
            continue
        win_width = 1.5 if room.type == "bathroom" else min(4.0, max(2.0, room.width - 2.0))
        sides: list[tuple[str, float]] = []
        if room.x <= 1e-9:
            sides.append(("west", room.depth))
        if abs(room.x + room.width - site_width) <= 1e-9:
            sides.append(("east", room.depth))
        if abs(room.y + room.depth - built_depth) <= 1e-9:
            sides.append(("south", room.width))
        if room.y <= 1e-9 and room is not entry_room:
            sides.append(("north", room.width))
        for side, wall_len in sides[:2]:
            length = 1.5 if room.type == "bathroom" else min(win_width, max(1.5, wall_len - 2.0))
            windows.append(
                Window(
                    id=f"win-{room.id}-{side}",
                    room_id=room.id,
                    wall=side,  # type: ignore[arg-type]
                    offset=round(max(0.5, (wall_len - length) / 2), 1),
                    width=round(length, 1),
                )
            )

    if entry_room is not None and entry_room.y > 1e-9:
        state.warn(
            "warn-entry-not-front",
            f"{entry_room.name} is not on the entrance edge — circulation may be indirect.",
            severity="info",
        )

    return doors, windows


def _multi_floor_bands(
    req: DesignRequirements, state: _GenState
) -> list[tuple[int, list[list[_Spec]]]]:
    """Return (level_index, bands) pairs for multi-floor residential buildings.

    Ground floor: public + service zones + stair core.
    Upper floors: private zone (bedrooms/baths) distributed evenly + stair core.
    """
    front: list[_Spec] = []
    if req.parking:
        front.append(_spec("parking", "Parking", "parking", "parking"))
    if req.building_kind == "studio":
        front.append(_spec("studio", "Studio", "living", "studio_room"))
    else:
        front.append(_spec("living", "Living Room", "living", "living"))
    if req.balcony:
        front.append(_spec("balcony", "Balcony", "balcony", "balcony"))

    service: list[_Spec] = []
    service.append(
        _spec(
            "kitchen",
            "Kitchenette" if req.building_kind == "studio" else "Kitchen",
            "kitchen",
            "kitchenette" if req.building_kind == "studio" else "kitchen",
        )
    )
    if req.dining:
        service.append(_spec("dining", "Dining", "dining", "dining"))
    baths_left = req.bathrooms
    if baths_left > 0:
        service.append(_spec("bath-1", "Common Bath", "bathroom", "bathroom"))
        baths_left -= 1
    if req.study:
        service.append(_spec("study", "Study", "study", "study"))
    if req.storage:
        service.append(_spec("storage", "Storage", "storage", "storage"))

    private: list[_Spec] = []
    for i in range(req.bedrooms):
        if i == 0:
            private.append(_spec("bed-master", "Master Bedroom", "bedroom", "master_bedroom"))
        else:
            private.append(_spec(f"bed-{i + 1}", f"Bedroom {i + 1}", "bedroom", "bedroom"))
        if baths_left > 0:
            bath_id = f"bath-{req.bathrooms - baths_left + 1}"
            label = "Attached Bath" if i == 0 else f"Bath {req.bathrooms - baths_left + 1}"
            private.append(_spec(bath_id, label, "bathroom", "bathroom"))
            baths_left -= 1

    n_upper = req.floors - 1
    ground_bands = [b for b in [front, service] if b]
    ground_bands = ground_bands + [[_stair_spec(0)]]
    result: list[tuple[int, list[list[_Spec]]]] = [(0, ground_bands)]

    if private and n_upper > 0:
        chunk = max(1, (len(private) + n_upper - 1) // n_upper)
        for floor_idx in range(1, req.floors):
            slice_start = (floor_idx - 1) * chunk
            slice_end = min(slice_start + chunk, len(private))
            floor_private = private[slice_start:slice_end]
            if not floor_private:
                break
            result.append((floor_idx, [floor_private, [_stair_spec(floor_idx)]]))

    return result


_KIND_LABELS = {
    "apartment": "Apartment",
    "villa": "Villa",
    "studio": "Studio Apartment",
    "duplex": "Duplex",
    "cafe": "Small Cafe",
    "office": "Office Layout",
}


def _project_name(req: DesignRequirements) -> str:
    label = _KIND_LABELS.get(req.building_kind, "Project")
    if req.building_kind in ("apartment", "villa", "duplex") and req.bedrooms > 0:
        return f"{req.bedrooms}BHK {label} Concept"
    return f"{label} Concept"


def generate_floorplan(req: DesignRequirements) -> tuple[ArchitectureProject, str]:
    """Generate a validated-shape project plus a human summary."""
    state = _GenState()

    # ── Setback inset (Phase 27.2) ─────────────────────────────────────────────
    # Rooms are packed into the usable envelope inside the setbacks.
    # Setback values default to NBC urban residential (front 9.84 ft, side 4.92 ft, rear 9.84 ft).
    usable_w = max(MIN_ROOM_DIM, req.site_width - 2 * req.side_setback)
    usable_d = max(MIN_ROOM_DIM, req.site_depth - req.front_setback - req.rear_setback)
    x_offset = req.side_setback
    y_offset  = req.front_setback

    if usable_w < req.site_width - 1e-3 or usable_d < req.site_depth - 1e-3:
        state.warn(
            "warn-setback-applied",
            f"Setbacks applied: front {req.front_setback:g} ft, sides {req.side_setback:g} ft, "
            f"rear {req.rear_setback:g} ft → usable envelope {usable_w:g} × {usable_d:g} ft.",
            severity="info",
        )

    if req.building_kind == "cafe":
        bands = _cafe_program(req, state)
        building_type = "commercial"
    elif req.building_kind == "office":
        bands = _office_fallback_program(req, state)
        building_type = "commercial"
    else:
        bands = _residential_program(req, state)
        building_type = "residential"

    if req.floors > 1 and building_type == "residential":
        level_bands_list = _multi_floor_bands(req, state)
        if req.size_modifier != 1.0:
            m = req.size_modifier
            for _, bands_for_level in level_bands_list:
                for band in bands_for_level:
                    for spec in band:
                        if spec.type != "stair":
                            spec.width = max(MIN_ROOM_DIM, round(spec.width * m, 1))
                            spec.depth = max(MIN_ROOM_DIM, round(spec.depth * m, 1))
        rooms = []
        doors = []
        windows = []
        for level_idx, bands_for_level in level_bands_list:
            level_rooms = _pack_bands(bands_for_level, usable_w, usable_d, state, level=level_idx)
            # Shift rooms into the setback-inset position
            for r in level_rooms:
                r.x = round(r.x + x_offset, 2)
                r.y = round(r.y + y_offset, 2)
            rooms.extend(level_rooms)
            d, w = _openings(level_rooms, req.site_width, state)
            doors.extend(d)
            windows.extend(w)
    else:
        if req.size_modifier != 1.0:
            m = req.size_modifier
            for band in bands:
                for spec in band:
                    spec.width = max(MIN_ROOM_DIM, round(spec.width * m, 1))
                    spec.depth = max(MIN_ROOM_DIM, round(spec.depth * m, 1))
        rooms = _pack_bands(bands, usable_w, usable_d, state)
        for r in rooms:
            r.x = round(r.x + x_offset, 2)
            r.y = round(r.y + y_offset, 2)
        doors, windows = _openings(rooms, req.site_width, state)

    # ── FSI guard (Phase 27.2) ────────────────────────────────────────────────
    site_area = req.site_width * req.site_depth
    built_up  = sum(r.width * r.depth for r in rooms if r.type not in ("parking", "balcony"))
    actual_fsi = built_up / site_area if site_area > 0 else 0.0
    if actual_fsi > req.max_fsi + 1e-4:
        state.warn(
            "warn-fsi-exceeded",
            f"FSI {actual_fsi:.2f} exceeds allowed {req.max_fsi} for this zone. "
            f"Reduce built-up area by ≈ {built_up - req.max_fsi * site_area:.0f} ft² or increase site.",
        )

    for assumption in req.assumptions:
        state.warnings.insert(
            0,
            ProjectWarning(
                id=f"assume-{len(state.warnings)}",
                severity="info",
                message=assumption,
            ),
        )

    levels = [
        Level(
            index=i,
            name="Ground Floor" if i == 0 else f"Floor {i}",
            elevation=round(i * DEFAULT_FLOOR_HEIGHT, 1),
        )
        for i in range(req.floors)
    ]

    project = ArchitectureProject(
        id="generated",  # storage assigns the durable id
        name=_project_name(req),
        units="feet",
        site=Site(width=req.site_width, depth=req.site_depth, orientation=req.orientation),  # type: ignore[arg-type]
        building=Building(
            type=building_type,
            style=req.style,
            floors=req.floors,
            floor_height=DEFAULT_FLOOR_HEIGHT,
        ),
        levels=levels,
        rooms=rooms,
        doors=doors,
        windows=windows,
        parameters=[
            Parameter(key="site_width", label="Site width", value=req.site_width, unit="ft", category="site", min=10, max=300),
            Parameter(key="site_depth", label="Site depth", value=req.site_depth, unit="ft", category="site", min=10, max=300),
            Parameter(key="orientation", label="Orientation", value=req.orientation, category="site"),
            Parameter(key="floors", label="Floors", value=req.floors, category="building", min=1, max=4),
            Parameter(key="floor_height", label="Floor height", value=DEFAULT_FLOOR_HEIGHT, unit="ft", category="building", min=8, max=14),
            Parameter(key="style", label="Style", value=req.style, category="building"),
        ],
        notes=[f"Generated deterministically from: “{req.prompt}”"] if req.prompt else [],
        warnings=state.warnings,
    )

    project = assign_default_materials(project)
    project = place_all_furniture(project)

    # Auto-derive dimension annotations and stair entities (Phase 29.0)
    from app.core.architecture.dimension_engine import AutoDimensionEngine
    project.dimensions = AutoDimensionEngine.derive(project)
    project.stairs = AutoDimensionEngine.derive_stair_entities(project)

    built = sum(r.width * r.depth for r in rooms)
    summary = (
        f"Generated a {project.name.lower().removesuffix(' concept')} on a "
        f"{req.site_width:g} × {req.site_depth:g} ft {req.orientation}-facing site — "
        f"{len(rooms)} rooms, {built:g} ft² built-up."
    )
    return project, summary
