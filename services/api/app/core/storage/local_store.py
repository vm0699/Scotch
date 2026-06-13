"""Local filesystem ProjectStore.

Layout (the `local-user` segment is the cloud open door — real user ids
replace it when auth lands in Phase 18):

    {data_dir}/users/{user_id}/projects/{project_id}/project.json
    {data_dir}/users/{user_id}/projects/{project_id}/exports/
    {data_dir}/users/{user_id}/projects/{project_id}/exports/manifest.json

Writes are atomic (temp file + os.replace) so a crash never leaves a
half-written project on disk.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.models import ArchitectureProject, DesignOption, ExportManifest
from app.core.storage.base import (
    LOCAL_USER_ID,
    ProjectNotFoundError,
    ProjectStore,
    ProjectSummary,
    StoredProject,
    summarize,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LocalProjectStore(ProjectStore):
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def _project_dir(self, user_id: str, project_id: str) -> Path:
        return self.data_dir / "users" / user_id / "projects" / project_id

    def _project_file(self, user_id: str, project_id: str) -> Path:
        return self._project_dir(user_id, project_id) / "project.json"

    def _write_json(self, path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)

    def _read(self, user_id: str, project_id: str) -> StoredProject:
        file = self._project_file(user_id, project_id)
        if not file.exists():
            raise ProjectNotFoundError(project_id)
        return StoredProject.model_validate_json(file.read_text(encoding="utf-8"))

    def _save(self, user_id: str, stored: StoredProject) -> None:
        self._write_json(
            self._project_file(user_id, stored.id),
            stored.model_dump_json(indent=2),
        )

    # ── ProjectStore interface ──────────────────────────────────────

    def create_project(
        self,
        name: str,
        prompt: str | None = None,
        project: ArchitectureProject | None = None,
        user_id: str = LOCAL_USER_ID,
    ) -> StoredProject:
        now = _now()
        stored = StoredProject(
            id=f"proj-{uuid4().hex[:12]}",
            name=name.strip() or "Untitled Project",
            prompt=prompt,
            created_at=now,
            updated_at=now,
            project=project,
        )
        self._save(user_id, stored)
        return stored

    def list_projects(self, user_id: str = LOCAL_USER_ID) -> list[ProjectSummary]:
        projects_dir = self.data_dir / "users" / user_id / "projects"
        if not projects_dir.exists():
            return []
        summaries = []
        for entry in projects_dir.iterdir():
            file = entry / "project.json"
            if file.exists():
                stored = StoredProject.model_validate_json(
                    file.read_text(encoding="utf-8")
                )
                summaries.append(summarize(stored))
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def get_project(
        self, project_id: str, user_id: str = LOCAL_USER_ID
    ) -> StoredProject:
        return self._read(user_id, project_id)

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        prompt: str | None = None,
        project: ArchitectureProject | None = None,
        options: list[DesignOption] | None = None,
        user_id: str = LOCAL_USER_ID,
    ) -> StoredProject:
        stored = self._read(user_id, project_id)
        if name is not None:
            stored.name = name.strip() or stored.name
        if prompt is not None:
            stored.prompt = prompt
        if project is not None:
            stored.project = project
        if options is not None:
            stored.options = options
        stored.updated_at = _now()
        self._save(user_id, stored)
        return stored

    def delete_project(self, project_id: str, user_id: str = LOCAL_USER_ID) -> None:
        directory = self._project_dir(user_id, project_id)
        if not directory.exists():
            raise ProjectNotFoundError(project_id)
        shutil.rmtree(directory)

    def save_export_manifest(
        self,
        project_id: str,
        manifest: ExportManifest,
        user_id: str = LOCAL_USER_ID,
    ) -> None:
        if not self._project_file(user_id, project_id).exists():
            raise ProjectNotFoundError(project_id)
        manifest_file = (
            self._project_dir(user_id, project_id) / "exports" / "manifest.json"
        )
        manifests: list[dict] = []
        if manifest_file.exists():
            manifests = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifests.append(json.loads(manifest.model_dump_json()))
        self._write_json(manifest_file, json.dumps(manifests, indent=2))

    def list_export_manifests(
        self, project_id: str, user_id: str = LOCAL_USER_ID
    ) -> list[ExportManifest]:
        if not self._project_file(user_id, project_id).exists():
            raise ProjectNotFoundError(project_id)
        manifest_file = (
            self._project_dir(user_id, project_id) / "exports" / "manifest.json"
        )
        if not manifest_file.exists():
            return []
        raw: list[dict] = json.loads(manifest_file.read_text(encoding="utf-8"))
        return [ExportManifest.model_validate(entry) for entry in raw]

    def get_export_path(
        self, project_id: str, filename: str, user_id: str = LOCAL_USER_ID
    ) -> Path:
        if not self._project_file(user_id, project_id).exists():
            raise ProjectNotFoundError(project_id)
        return self._project_dir(user_id, project_id) / "exports" / filename
