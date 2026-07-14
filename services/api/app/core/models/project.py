"""ArchitectureProject — the universal architecture model.

Single source of truth for generation, editing, previews, exports, and
integrations. The frontend mirrors these models one-to-one in
apps/web/src/features/project/types.ts; keep both in sync.

Plan space: x runs across the site width, y along the site depth with
y = 0 at the entrance edge. Door/window walls are plan-local:
north = top edge (entrance side), south = bottom, west = left, east = right.
"""

from datetime import datetime, timezone
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

Units = Literal["feet", "meters"]
Orientation = Literal["north", "south", "east", "west"]
WallSide = Literal["north", "south", "east", "west"]
WarningSeverity = Literal["info", "warning", "error"]
DimensionType = Literal["linear", "room", "external", "opening", "stair"]
DimensionLayer = Literal["dim-external", "dim-room", "dim-opening", "dim-stair"]
MEPSystem = Literal["plumbing", "electrical", "lighting", "ac"]
DetailType = Literal["toilet", "kitchen", "door_window", "wall_section", "tile_layout", "stair", "custom"]


class Site(BaseModel):
    width: float = Field(gt=0, description="Site width in project units")
    depth: float = Field(gt=0, description="Site depth in project units")
    orientation: Orientation = "east"


class Building(BaseModel):
    type: str = "residential"
    style: str = "modern minimal"
    floors: int = Field(default=1, ge=1)
    floor_height: float = Field(default=10, gt=0)


class Level(BaseModel):
    index: int = Field(ge=0)
    name: str
    elevation: float = 0


class Room(BaseModel):
    id: str
    name: str
    type: str
    x: float = Field(ge=0, description="Top-left corner x on the site plan")
    y: float = Field(ge=0, description="Top-left corner y on the site plan")
    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    level: int = Field(default=0, ge=0)


class Wall(BaseModel):
    """Explicit wall segment; optional while rooms imply their own walls."""

    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    thickness: float = Field(default=0.5, gt=0)
    room_id: str | None = None


class Door(BaseModel):
    id: str
    room_id: str
    wall: WallSide
    offset: float = Field(ge=0, description="Distance from the wall start to the opening")
    width: float = Field(gt=0)


class Window(BaseModel):
    id: str
    room_id: str
    wall: WallSide
    offset: float = Field(ge=0)
    width: float = Field(gt=0)


class Material(BaseModel):
    id: str
    name: str
    target: str = Field(description="What the material applies to, e.g. wall, floor, roof, glass")
    finish: str | None = None
    base_color: str = "#F5F4F2"   # hex color hint for render engines
    roughness: float = Field(default=0.5, ge=0.0, le=1.0)
    metallic: float = Field(default=0.0, ge=0.0, le=1.0)


class CameraSuggestion(BaseModel):
    """A derived camera preset for rendering.

    position / target use plan-space + height coordinates [plan_x, height, plan_y]
    which map directly to three.js [x, y, z] (plan_y → Blender Y, height → Blender Z).
    Values are in project units (feet by default).
    """

    name: str
    type: Literal["perspective", "orthographic"]
    position: list[float]   # [plan_x, height, plan_y]
    target: list[float]     # [plan_x, height, plan_y]
    fov: float = 50.0       # degrees; 0 for orthographic
    description: str = ""


class Parameter(BaseModel):
    key: str
    label: str
    value: str | float | int
    unit: str | None = None
    category: Literal["site", "building", "room"]
    editable: bool = True
    target_id: str | None = None
    min: float | None = None
    max: float | None = None


class ProjectWarning(BaseModel):
    id: str
    severity: WarningSeverity = "info"
    message: str


class FurnitureItem(BaseModel):
    """One piece of furniture placed in a room.

    x / y are the top-left corner of the placed footprint in plan space (feet).
    width / depth are the placed footprint dimensions AFTER rotation is applied
    (so the bounding box is always axis-aligned).
    rotation is the display angle (0 / 90 / 180 / 270) used only for SVG symbol
    rendering — the footprint is already in placed coordinates.
    height is the 3D block height for massing / export.
    """

    id: str
    type: str
    label: str = ""
    room_id: str
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    rotation: int = Field(default=0, description="Symbol rotation: 0 | 90 | 180 | 270")
    height: float = Field(default=2.5, gt=0, description="3D height in project units")
    # ── Phase 43: catalog-backed interior furniture ──────────────────────────
    catalog_id: str | None = Field(
        default=None, description="Links to a CatalogItem (real GLB mesh); None = legacy box render"
    )
    material_overrides: dict[str, str] = Field(
        default_factory=dict, description="material_slot -> Material.id, for recolor/retexture"
    )
    z: float = Field(default=0.0, ge=0, description="Height off floor in project units (wall/ceiling/tabletop items)")


# ── Phase 29: Dimension entities ─────────────────────────────────────────────


class DimensionEntity(BaseModel):
    """One dimension annotation derived by AutoDimensionEngine.

    p1 / p2 are [x, y] in plan-space project units.
    value is the numeric span in project units; label is the display string.
    """

    id: str
    dim_type: DimensionType = "room"
    p1: list[float]   # [x, y]
    p2: list[float]   # [x, y]
    value: float
    label: str
    layer: DimensionLayer = "dim-room"


class StairEntity(BaseModel):
    """Detailed stair parameters for working-drawing output.

    Links to a stair Room by room_id. Defaults reflect a typical residential
    stair: 13 risers × ~7″ rise, ~10″ tread, 4 ft wide.
    """

    id: str
    room_id: str
    risers: int = Field(default=13, ge=2, le=24)
    riser_height: float = Field(default=0.583, gt=0, description="ft — ~7 inches")
    tread_depth: float = Field(default=0.833, gt=0, description="ft — ~10 inches")
    width: float = Field(default=4.0, gt=0, description="ft")
    flight_direction: WallSide = "north"
    stair_type: Literal["straight", "l_shaped", "u_shaped"] = "straight"
    level_from: int = 0
    level_to: int = 1


# ── Phase 29: MEP models ──────────────────────────────────────────────────────


class ServicePoint(BaseModel):
    """One MEP fixture or control point placed in plan space.

    Coordinates (x, y) are in project units (feet by default).
    mount_height is 0 for floor-level, positive for wall-mounted fixtures.
    user_override = True means the user moved this point; regen preserves it.
    """

    id: str
    system: MEPSystem
    kind: str   # "sink" | "wc" | "basin" | "shower" | "switch" | "socket" | "light" | "ac_unit" | …
    room_id: str
    x: float
    y: float
    mount_height: float = Field(default=0.0, ge=0.0)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    needs_review: bool = False
    user_override: bool = False
    label: str = ""


class ServiceRoute(BaseModel):
    """Advisory pipe/cable route as a polyline.

    polyline is a list of [x, y] points in plan-space project units.
    Marked needs_review=True because routes are conceptual/advisory only.
    """

    id: str
    system: MEPSystem
    polyline: list[list[float]]
    kind: str   # "supply" | "drain" | "circuit" | "branch"
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    needs_review: bool = True


class PlumbingPlan(BaseModel):
    points: list[ServicePoint] = []
    routes: list[ServiceRoute] = []
    warnings: list[str] = []
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    needs_review: bool = True


class ElectricalPlan(BaseModel):
    points: list[ServicePoint] = []
    routes: list[ServiceRoute] = []
    warnings: list[str] = []
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    needs_review: bool = True


class LightingPlan(BaseModel):
    points: list[ServicePoint] = []
    warnings: list[str] = []
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    needs_review: bool = True


class ACPlan(BaseModel):
    points: list[ServicePoint] = []
    warnings: list[str] = []
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    needs_review: bool = True


class MEPPlan(BaseModel):
    """Container for all four MEP systems.

    generated = False until MEPGenerator runs.
    stale = True when rooms change after MEP was generated (warning shown).
    All conceptual/advisory — not engineering-certified. Every output carries
    confidence + needs_review; professional review is required before construction.
    """

    plumbing: PlumbingPlan = Field(default_factory=PlumbingPlan)
    electrical: ElectricalPlan = Field(default_factory=ElectricalPlan)
    lighting: LightingPlan = Field(default_factory=LightingPlan)
    ac: ACPlan = Field(default_factory=ACPlan)
    generated: bool = False
    stale: bool = False


# ── Phase 30: Detail Drawing primitives ──────────────────────────────────────


class LinePrimitive(BaseModel):
    kind: Literal["line"] = "line"
    p1: list[float]
    p2: list[float]
    layer: str = "outline"
    style: str = "solid"
    weight: float = 0.5


class ArcPrimitive(BaseModel):
    kind: Literal["arc"] = "arc"
    center: list[float]
    radius: float
    start_angle: float = 0.0
    end_angle: float = 360.0
    layer: str = "outline"


class TextPrimitive(BaseModel):
    kind: Literal["text"] = "text"
    pos: list[float]
    text: str
    height: float = 0.2
    layer: str = "annotation"
    anchor: str = "center"


class DimPrimitive(BaseModel):
    kind: Literal["dim"] = "dim"
    p1: list[float]
    p2: list[float]
    value: float
    label: str
    layer: str = "dim"


class HatchPrimitive(BaseModel):
    kind: Literal["hatch"] = "hatch"
    boundary: list[list[float]]
    pattern: str = "ANSI31"
    scale: float = 1.0
    layer: str = "hatch"
    angle: float = 45.0


DetailPrimitive = Annotated[
    Union[LinePrimitive, ArcPrimitive, TextPrimitive, DimPrimitive, HatchPrimitive],
    Field(discriminator="kind"),
]


class DetailDrawing(BaseModel):
    id: str
    name: str
    detail_type: DetailType = "custom"
    source_object_ids: list[str] = []
    primitives: list[DetailPrimitive] = []
    canvas_width: float = 10.0
    canvas_height: float = 10.0
    scale: str = "1:20"
    view: str = "plan"
    warnings: list[str] = []
    annotations: list[str] = []
    confidence: float = 0.85
    needs_review: bool = True
    stale: bool = False


# ── Phase 31: Material / BOQ / Cost models ───────────────────────────────────


class TileSpec(BaseModel):
    """Tile specification for a room or project-wide default.

    size_w / size_h are tile dimensions in inches.
    rate_per_sqft is in project currency (INR assumed); 0 = missing rate.
    wastage_pct is an additional percentage added to quantity (e.g. 10 = 10% waste).
    """

    id: str
    label: str = ""
    size_w: float = Field(default=24.0, gt=0, description="Tile width in inches")
    size_h: float = Field(default=24.0, gt=0, description="Tile height in inches")
    rate_per_sqft: float = Field(default=0.0, ge=0.0, description="Rate in project currency per sqft")
    wastage_pct: float = Field(default=10.0, ge=0.0, le=100.0)


class RoomFinish(BaseModel):
    room_id: str
    floor_material: str = "tile"
    floor_tile_spec_id: str | None = None
    wall_material: str = "paint"
    ceiling_material: str = "paint"
    wall_tile_spec_id: str | None = None


# ── Phase 43: Interior Design Studio ─────────────────────────────────────────


class RoomInterior(BaseModel):
    """Per-room interior-furnishing status. One entry per room that has ever
    been furnished through /interior/generate — absent = never furnished."""

    room_id: str
    status: str = Field(default="empty", description='"empty" | "designed" | "stale"')
    style: str = ""
    mode: str = Field(default="deterministic", description='"deterministic" | "ai" | "hybrid"')
    last_generated_at: str = ""
    warnings: list[str] = Field(default_factory=list)


class RateEntry(BaseModel):
    category: str
    item: str
    unit: str
    rate: float = 0.0
    source: str = "manual"


class MaterialPlan(BaseModel):
    """Project-level material assignments and rate table.

    generated = False until QuantityEngine runs.
    stale = True when rooms/openings change after BOQ was generated.
    """

    tile_specs: list[TileSpec] = []
    room_finishes: list[RoomFinish] = []
    editable_rates: list[RateEntry] = []
    assumptions: list[str] = []
    generated: bool = False
    stale: bool = False


class BOQItem(BaseModel):
    """One line in the Bill of Quantities.

    source_object_ids traces the item back to rooms/doors/windows/furniture/fixtures.
    rate = 0 means the rate is missing (excluded from totals with a warning).
    """

    id: str
    category: str  # "flooring" | "wall_tile" | "paint" | "doors" | "windows" | "plumbing" | "electrical" | "furniture"
    description: str
    source_object_ids: list[str] = []
    unit: str
    quantity: float
    rate: float = 0.0
    amount: float = 0.0
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    needs_review: bool = False
    editable: bool = True


class CategoryTotal(BaseModel):
    category: str
    total: float


class CostPlan(BaseModel):
    """Aggregated BOQ and cost summary.

    generated = False until QuantityEngine.build_boq() runs.
    missing_rates lists category+item strings for items with rate=0.
    assumptions are surfaced in UI as "estimated at standard rates" notes.
    """

    boq_items: list[BOQItem] = []
    category_totals: list[CategoryTotal] = []
    grand_total: float = 0.0
    missing_rates: list[str] = []
    assumptions: list[str] = []
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    needs_review: bool = True
    generated: bool = False


# ── Phase 33 — Client brief ───────────────────────────────────────────────────

class ClientBrief(BaseModel):
    """Client brief — inline in ArchitectureProject, versions with the design."""
    family_name: str = ""
    family_size: int = 0
    lifestyle: str = ""
    budget_level: Literal["economy", "standard", "premium"] = "standard"
    budget_inr: float = 0.0
    style_preference: str = ""
    vastu_preference: bool = False
    parking_preference: Literal["none", "two_wheeler", "car", "both"] = "car"
    future_expansion: bool = False
    special_needs: list[str] = Field(default_factory=list)
    material_preference: str = ""
    notes: str = ""


# ── Phase 34: Revision metadata ───────────────────────────────────────────────

class RevisionMeta(BaseModel):
    """Revision tracker embedded in ArchitectureProject.

    revision_number increments each time a client change is applied.
    exports_stale is set True whenever the design changes after exports were
    generated, and cleared when exports are re-run.
    """

    revision_number: int = 0
    note: str = ""
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    affected_sheets: list[str] = Field(default_factory=list)
    exports_stale: bool = False
    stale_reason: str = ""


def _default_revision_meta() -> RevisionMeta:
    return RevisionMeta()


# ── Phase 40: Feasibility / Yield Analysis ────────────────────────────────────


class FeasibilityOption(BaseModel):
    """One feasibility variant (compact / balanced / spacious / etc.)."""

    name: str  # "compact" | "balanced" | "spacious" | "future_expansion" | "rental_friendly"
    label: str
    unit_count: int = 1
    unit_type: str = "2BHK"
    unit_sizes_sqft: list[float] = []
    coverage_pct: float = 0.0
    built_up_area: float = 0.0
    parking_slots: int = 0
    description: str = ""
    trade_offs: list[str] = []


class Feasibility(BaseModel):
    """Residential-plot feasibility analysis (TestFit-lite). Advisory only."""

    site_area: float = 0.0
    usable_footprint: float = 0.0
    coverage_pct: float = 0.0
    fsi_far: float = 1.5
    buildable_area: float = 0.0
    floors: int = 1
    parking_estimate: int = 1
    options: list[FeasibilityOption] = []
    missing_inputs: list[str] = []
    warnings: list[str] = []
    assumptions: list[str] = []
    confidence: float = 0.8
    needs_review: bool = True
    generated: bool = False
    road_width_ft: float = 0.0


class ArchitectureProject(BaseModel):
    id: str
    name: str
    units: Units = "feet"
    site: Site
    building: Building
    levels: list[Level] = []
    rooms: list[Room] = []
    walls: list[Wall] = []
    doors: list[Door] = []
    windows: list[Window] = []
    furniture: list[FurnitureItem] = []
    materials: list[Material] = []
    parameters: list[Parameter] = []
    notes: list[str] = []
    warnings: list[ProjectWarning] = []
    show_furniture: bool = True
    # Phase 29 additions
    dimensions: list[DimensionEntity] = []
    stairs: list[StairEntity] = []
    mep_plan: MEPPlan = Field(default_factory=MEPPlan)
    show_dimensions: bool = True
    show_mep: bool = False
    # Phase 30 additions
    detail_drawings: list[DetailDrawing] = []
    # Phase 31 additions
    material_plan: MaterialPlan = Field(default_factory=MaterialPlan)
    cost_plan: CostPlan = Field(default_factory=CostPlan)
    # Phase 33 additions
    client_brief: ClientBrief = Field(default_factory=ClientBrief)
    # Phase 34 additions — revision metadata
    revision_meta: "RevisionMeta" = Field(default_factory=lambda: _default_revision_meta())
    # Phase 40 additions — feasibility / yield
    feasibility: "Feasibility" = Field(default_factory=Feasibility)
    # Phase 43 additions — interior design studio (per-room furnishing status)
    room_interiors: list[RoomInterior] = []


class ExportManifest(BaseModel):
    filename: str
    format: str
    path: str
    created_at: datetime


class DesignOption(BaseModel):
    """One compact/balanced/spacious design variant generated from a prompt."""

    option_id: str
    variant: Literal["compact", "balanced", "spacious"]
    score: float = Field(ge=0, le=10)
    summary: str
    warnings: list[ProjectWarning] = []
    preview: ArchitectureProject


# ── Phase 19: Version history ─────────────────────────────────────────────────

VersionChangeType = Literal["generate", "regenerate", "edit", "option", "restore", "sync", "client_change"]


class ProjectVersionMeta(BaseModel):
    """Lightweight version listing entry — no snapshot, for quick display."""

    version_id: str
    created_at: datetime
    change_type: VersionChangeType
    summary: str
    room_count: int = 0
    total_area: float = 0.0
    thumbnail: str | None = None  # compact inline SVG computed from snapshot


class ProjectVersion(BaseModel):
    """Full version with design snapshot — stored as sidecar file per version."""

    version_id: str
    created_at: datetime
    change_type: VersionChangeType
    summary: str
    snapshot: ArchitectureProject
