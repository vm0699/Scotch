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
    bands: list[list[_Spec]], site_width: float, site_depth: float, state: _GenState
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
                    level=0,
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

    if req.building_kind == "cafe":
        bands = _cafe_program(req, state)
        building_type = "commercial"
    elif req.building_kind == "office":
        bands = _office_fallback_program(req, state)
        building_type = "commercial"
    else:
        bands = _residential_program(req, state)
        building_type = "residential"

    if req.size_modifier != 1.0:
        m = req.size_modifier
        for band in bands:
            for spec in band:
                spec.width = max(MIN_ROOM_DIM, round(spec.width * m, 1))
                spec.depth = max(MIN_ROOM_DIM, round(spec.depth * m, 1))

    rooms = _pack_bands(bands, req.site_width, req.site_depth, state)
    doors, windows = _openings(rooms, req.site_width, state)

    for assumption in req.assumptions:
        state.warnings.insert(
            0,
            ProjectWarning(
                id=f"assume-{len(state.warnings)}",
                severity="info",
                message=assumption,
            ),
        )

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
        levels=[Level(index=0, name="Ground Floor", elevation=0)],
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

    built = sum(r.width * r.depth for r in rooms)
    summary = (
        f"Generated a {project.name.lower().removesuffix(' concept')} on a "
        f"{req.site_width:g} × {req.site_depth:g} ft {req.orientation}-facing site — "
        f"{len(rooms)} rooms, {built:g} ft² built-up."
    )
    return project, summary
