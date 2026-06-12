"""Storage contract for Scotch projects.

Every storage backend — the local filesystem today, cloud object storage or
a database later (Phase 18) — implements ProjectStore. Callers never touch
the filesystem directly; they go through the interface with an explicit
user_id, so cloud auth and multi-user ownership slot in without API changes.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel

from app.core.models import ArchitectureProject, ExportManifest

LOCAL_USER_ID = "local-user"


class ProjectNotFoundError(LookupError):
    def __init__(self, project_id: str):
        super().__init__(f"Project '{project_id}' not found")
        self.project_id = project_id


class StoredProject(BaseModel):
    """Persistence envelope around the universal model."""

    id: str
    name: str
    prompt: str | None = None
    created_at: datetime
    updated_at: datetime
    project: ArchitectureProject | None = None


class ProjectSummary(BaseModel):
    """Lightweight listing row for dashboards."""

    id: str
    name: str
    prompt: str | None = None
    created_at: datetime
    updated_at: datetime
    room_count: int = 0
    site_label: str | None = None


def summarize(stored: StoredProject) -> ProjectSummary:
    project = stored.project
    return ProjectSummary(
        id=stored.id,
        name=stored.name,
        prompt=stored.prompt,
        created_at=stored.created_at,
        updated_at=stored.updated_at,
        room_count=len(project.rooms) if project else 0,
        site_label=(
            f"{project.site.width:g} × {project.site.depth:g} "
            f"{'ft' if project.units == 'feet' else 'm'}"
            if project
            else None
        ),
    )


class ProjectStore(ABC):
    @abstractmethod
    def create_project(
        self,
        name: str,
        prompt: str | None = None,
        project: ArchitectureProject | None = None,
        user_id: str = LOCAL_USER_ID,
    ) -> StoredProject: ...

    @abstractmethod
    def list_projects(self, user_id: str = LOCAL_USER_ID) -> list[ProjectSummary]: ...

    @abstractmethod
    def get_project(
        self, project_id: str, user_id: str = LOCAL_USER_ID
    ) -> StoredProject: ...

    @abstractmethod
    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        prompt: str | None = None,
        project: ArchitectureProject | None = None,
        user_id: str = LOCAL_USER_ID,
    ) -> StoredProject: ...

    @abstractmethod
    def delete_project(self, project_id: str, user_id: str = LOCAL_USER_ID) -> None: ...

    @abstractmethod
    def save_export_manifest(
        self,
        project_id: str,
        manifest: ExportManifest,
        user_id: str = LOCAL_USER_ID,
    ) -> None: ...
