"""Version history routes — Phase 19.

GET  /projects/{id}/versions                    → list[ProjectVersionMeta]
GET  /projects/{id}/versions/{version_id}       → ProjectVersion
POST /projects/{id}/versions/{version_id}/restore → StoredProject
GET  /projects/{id}/versions/{a}/diff/{b}       → VersionDiff
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth.context import get_current_user_id
from app.core.models.project import (
    ArchitectureProject,
    ProjectVersion,
    ProjectVersionMeta,
    VersionChangeType,
)
from app.core.storage import (
    ProjectNotFoundError,
    ProjectStore,
    StoredProject,
    VersionNotFoundError,
    get_project_store,
)
from app.core.validation import validate_project

router = APIRouter(prefix="/projects", tags=["versions"])


# ── Diff models ───────────────────────────────────────────────────────────────

class RoomChange(BaseModel):
    room_id: str
    room_name: str
    change: Literal["added", "removed", "resized"]
    old_area: float | None = None
    new_area: float | None = None
    area_delta: float | None = None


class VersionDiff(BaseModel):
    version_a: str
    version_b: str
    added_rooms: list[RoomChange]
    removed_rooms: list[RoomChange]
    resized_rooms: list[RoomChange]
    total_area_delta: float
    total_rooms_delta: int


def _compute_diff(
    ver_a: str, ver_b: str,
    proj_a: ArchitectureProject,
    proj_b: ArchitectureProject,
) -> VersionDiff:
    rooms_a = {r.id: r for r in proj_a.rooms}
    rooms_b = {r.id: r for r in proj_b.rooms}

    added, removed, resized = [], [], []

    for rid, room in rooms_b.items():
        if rid not in rooms_a:
            added.append(RoomChange(
                room_id=rid,
                room_name=room.name,
                change="added",
                new_area=round(room.width * room.depth, 1),
            ))

    for rid, room in rooms_a.items():
        if rid not in rooms_b:
            removed.append(RoomChange(
                room_id=rid,
                room_name=room.name,
                change="removed",
                old_area=round(room.width * room.depth, 1),
            ))

    for rid, rb in rooms_b.items():
        if rid in rooms_a:
            ra = rooms_a[rid]
            if abs(ra.width - rb.width) > 0.05 or abs(ra.depth - rb.depth) > 0.05:
                old = round(ra.width * ra.depth, 1)
                new = round(rb.width * rb.depth, 1)
                resized.append(RoomChange(
                    room_id=rid,
                    room_name=rb.name,
                    change="resized",
                    old_area=old,
                    new_area=new,
                    area_delta=round(new - old, 1),
                ))

    area_a = sum(r.width * r.depth for r in proj_a.rooms)
    area_b = sum(r.width * r.depth for r in proj_b.rooms)

    return VersionDiff(
        version_a=ver_a,
        version_b=ver_b,
        added_rooms=added,
        removed_rooms=removed,
        resized_rooms=resized,
        total_area_delta=round(area_b - area_a, 1),
        total_rooms_delta=len(proj_b.rooms) - len(proj_a.rooms),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{project_id}/versions", response_model=list[ProjectVersionMeta])
def list_versions(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> list[ProjectVersionMeta]:
    try:
        return store.list_versions(project_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/versions/{version_id}", response_model=ProjectVersion)
def get_version(
    project_id: str,
    version_id: str,
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> ProjectVersion:
    try:
        return store.get_version(project_id, version_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{project_id}/versions/{version_id}/restore",
    response_model=StoredProject,
)
def restore_version(
    project_id: str,
    version_id: str,
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> StoredProject:
    """Restore a version snapshot as the active design.

    Restoring appends a 'restore' version (never destroys history).
    """
    try:
        ver = store.get_version(project_id, version_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    snapshot = ver.snapshot
    result = validate_project(snapshot)
    if not result.valid:
        raise HTTPException(
            status_code=422,
            detail={"message": "Snapshot failed validation", "errors": result.errors},
        )

    try:
        stored = store.update_project(
            project_id,
            project=snapshot,
            change_type="restore",
            version_summary=f"Restored to version {version_id} ({ver.change_type})",
            user_id=user_id,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return stored


@router.get(
    "/{project_id}/versions/{version_a}/diff/{version_b}",
    response_model=VersionDiff,
)
def diff_versions(
    project_id: str,
    version_a: str,
    version_b: str,
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> VersionDiff:
    """Return a structured diff between two version snapshots (a→b)."""
    try:
        ver_a = store.get_version(project_id, version_a, user_id=user_id)
        ver_b = store.get_version(project_id, version_b, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _compute_diff(version_a, version_b, ver_a.snapshot, ver_b.snapshot)
