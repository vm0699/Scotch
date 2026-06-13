"""ArchitectureProject — the universal architecture model.

Single source of truth for generation, editing, previews, exports, and
integrations. The frontend mirrors these models one-to-one in
apps/web/src/features/project/types.ts; keep both in sync.

Plan space: x runs across the site width, y along the site depth with
y = 0 at the entrance edge. Door/window walls are plan-local:
north = top edge (entrance side), south = bottom, west = left, east = right.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Units = Literal["feet", "meters"]
Orientation = Literal["north", "south", "east", "west"]
WallSide = Literal["north", "south", "east", "west"]
WarningSeverity = Literal["info", "warning", "error"]


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
    materials: list[Material] = []
    parameters: list[Parameter] = []
    notes: list[str] = []
    warnings: list[ProjectWarning] = []


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
