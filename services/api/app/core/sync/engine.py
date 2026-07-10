"""Sync engine — merge and project logic for the round-trip protocol.

push_sync(project, payload) → (updated_project, diff)
    Merges a SyncPayload from an external tool into the canonical model.
    Matching is by stable room ID (established in Phase 21).
    New IDs → add to project.  Missing IDs → flag (never auto-delete).
    Large dimensional changes (> CONFLICT_TOLERANCE) are flagged as conflicts
    and still applied — the version snapshot created by the caller is the
    safety net.

project_to_sync_contract(project, project_id, version_ts) → SyncContract
    Projects the canonical model into the minimal SyncRoom representation
    that plugins use to reconstruct or reposition geometry.
"""

from __future__ import annotations

import copy

from app.core.models.project import ArchitectureProject, Room
from app.core.sync.models import (
    CONFLICT_TOLERANCE,
    MIN_ROOM_DIM,
    ConflictItem,
    SyncContract,
    SyncDiff,
    SyncPayload,
    SyncRoom,
)


def project_to_sync_contract(
    project: ArchitectureProject,
    project_id: str,
    version_ts: str | None = None,
) -> SyncContract:
    """Return the minimal SyncContract projection of *project*."""
    rooms = [
        SyncRoom(
            id=room.id,
            name=room.name,
            type=room.type,
            x=room.x,
            y=room.y,
            width=room.width,
            depth=room.depth,
            level=room.level,
        )
        for room in project.rooms
    ]
    return SyncContract(project_id=project_id, rooms=rooms, source_version=version_ts)


def push_sync(
    project: ArchitectureProject,
    payload: SyncPayload,
) -> tuple[ArchitectureProject, SyncDiff]:
    """Merge *payload* into *project* and return the updated copy plus a diff.

    Raises ValueError if any incoming room fails the MIN_ROOM_DIM guard or if
    the merged model fails ArchitectureProject Pydantic validation.
    """
    # Guard: reject sub-minimum dimensions before touching the model.
    for sr in payload.rooms:
        if sr.width < MIN_ROOM_DIM or sr.depth < MIN_ROOM_DIM:
            raise ValueError(
                f"Room '{sr.id}' has dimension below minimum {MIN_ROOM_DIM} ft "
                f"(width={sr.width}, depth={sr.depth})"
            )

    # Index existing rooms by stable ID.
    existing: dict[str, Room] = {r.id: r for r in project.rooms}
    incoming_ids: set[str] = {sr.id for sr in payload.rooms}

    diff = SyncDiff()
    updated_rooms: list[Room] = list(project.rooms)  # preserve order

    for sr in payload.rooms:
        if sr.id in existing:
            old = existing[sr.id]
            changed = False

            # Detect conflicts (large deltas) before applying.
            for field in ("x", "y", "width", "depth"):
                old_val = getattr(old, field)
                new_val = getattr(sr, field)
                delta = abs(new_val - old_val)
                if delta > CONFLICT_TOLERANCE:
                    diff.conflicts.append(
                        ConflictItem(
                            room_id=sr.id,
                            room_name=sr.name,
                            field=field,
                            scotch_value=old_val,
                            incoming_value=new_val,
                            delta=round(delta, 3),
                        )
                    )

            # Apply updates.
            if (
                old.name != sr.name
                or old.x != sr.x
                or old.y != sr.y
                or old.width != sr.width
                or old.depth != sr.depth
                or old.level != sr.level
            ):
                idx = next(i for i, r in enumerate(updated_rooms) if r.id == sr.id)
                updated_rooms[idx] = old.model_copy(
                    update={
                        "name": sr.name,
                        "x": sr.x,
                        "y": sr.y,
                        "width": sr.width,
                        "depth": sr.depth,
                        "level": sr.level,
                    }
                )
                changed = True

            if changed:
                diff.updated.append(sr.id)
        else:
            # New room from the plugin — add it.
            new_room = Room(
                id=sr.id,
                name=sr.name,
                type=sr.type,
                x=sr.x,
                y=sr.y,
                width=sr.width,
                depth=sr.depth,
                level=sr.level,
            )
            updated_rooms.append(new_room)
            diff.added.append(sr.id)

    # Rooms present in model but absent from payload → flag only.
    for room_id in existing:
        if room_id not in incoming_ids:
            diff.flagged.append(room_id)

    # Rebuild project with updated rooms via Pydantic copy (validated).
    updated = project.model_copy(update={"rooms": updated_rooms})
    return updated, diff
