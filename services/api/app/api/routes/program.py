"""Program grid endpoint — Phase 21.

GET /projects/{id}/program → ProgramTable

A read-only projection of the ArchitectureProject model structured as a
Snaptrude-style program table: one site block + one row per room + totals.
No new storage — computed live from the stored project.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth.context import get_current_user_id
from app.core.storage import ProjectNotFoundError, ProjectStore, get_project_store

router = APIRouter(prefix="/projects", tags=["program"])


class ProgramSiteRow(BaseModel):
    width: float
    depth: float
    orientation: str
    floors: int
    floor_height: float


class ProgramRoomRow(BaseModel):
    id: str
    name: str
    type: str
    width: float
    depth: float
    area: float
    level: int


class ProgramTotals(BaseModel):
    built_up_area: float
    site_area: float
    coverage_pct: float
    room_count: int


class ProgramTable(BaseModel):
    site: ProgramSiteRow
    rooms: list[ProgramRoomRow]
    totals: ProgramTotals


@router.get("/{project_id}/program", response_model=ProgramTable)
def get_program(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    user_id: str = Depends(get_current_user_id),
) -> ProgramTable:
    """Return the program table for a project (read-only projection of the model)."""
    try:
        stored = store.get_project(project_id, user_id=user_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if stored.project is None:
        raise HTTPException(
            status_code=409,
            detail="Project has no design data — generate a floor plan first.",
        )

    project = stored.project
    site_area = round(project.site.width * project.site.depth, 1)
    built_up = round(sum(r.width * r.depth for r in project.rooms), 1)
    coverage_pct = round(built_up / site_area * 100, 1) if site_area > 0 else 0.0

    return ProgramTable(
        site=ProgramSiteRow(
            width=project.site.width,
            depth=project.site.depth,
            orientation=project.site.orientation,
            floors=project.building.floors,
            floor_height=project.building.floor_height,
        ),
        rooms=[
            ProgramRoomRow(
                id=room.id,
                name=room.name,
                type=room.type,
                width=room.width,
                depth=room.depth,
                area=round(room.width * room.depth, 1),
                level=room.level,
            )
            for room in project.rooms
        ],
        totals=ProgramTotals(
            built_up_area=built_up,
            site_area=site_area,
            coverage_pct=coverage_pct,
            room_count=len(project.rooms),
        ),
    )
