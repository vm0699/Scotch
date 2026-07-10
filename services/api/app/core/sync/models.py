"""Sync protocol data models.

SyncRoom     — one room's position, size, and identity.
SyncPayload  — what a plugin sends (rooms array from the host tool).
SyncContract — what Scotch returns on a pull (canonical projection).
ConflictItem — a field that differed by more than CONFLICT_TOLERANCE.
SyncDiff     — full summary of what the push changed.

The protocol is append-only and forward-compatible: unknown fields in the
payload are ignored so older plugins keep working against newer backends.
"""

from pydantic import BaseModel, Field

CONFLICT_TOLERANCE = 0.5  # feet — delta above which a change is flagged
MIN_ROOM_DIM = 4.0  # feet — minimum width or depth; matches floorplan_generator.py


class SyncRoom(BaseModel):
    """Minimal room representation shared by push and pull.

    Coordinates (x, y) are the top-left corner in plan space; width runs
    along X, depth along Y — identical to ArchitectureProject.Room.
    """

    id: str
    name: str
    type: str
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    level: int = Field(default=0, ge=0)


class SyncPayload(BaseModel):
    """What a plugin sends to POST /projects/{id}/sync."""

    rooms: list[SyncRoom]
    source: str = "sketchup"  # "sketchup" | "revit" | "rhino" | "web"


class SyncContract(BaseModel):
    """What Scotch returns on GET /projects/{id}/sync (pull direction)."""

    project_id: str
    rooms: list[SyncRoom]
    source_version: str | None = None  # ISO-8601 updated_at of the stored project


class ConflictItem(BaseModel):
    """One field that changed by more than CONFLICT_TOLERANCE feet."""

    room_id: str
    room_name: str
    field: str  # "x" | "y" | "width" | "depth"
    scotch_value: float
    incoming_value: float
    delta: float


class SyncDiff(BaseModel):
    """Summary of all changes made by a push_sync call."""

    added: list[str] = []    # room IDs created from the payload
    updated: list[str] = []  # room IDs whose geometry/name changed
    flagged: list[str] = []  # room IDs in Scotch but absent from payload (not deleted)
    conflicts: list[ConflictItem] = []  # large dimensional changes flagged for review
