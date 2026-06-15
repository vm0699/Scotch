"""Local filesystem ProjectStore.

Layout (the `local-user` segment is the cloud open door — real user ids
replace it when auth lands in Phase 18):

    {data_dir}/users/{user_id}/projects/{project_id}/project.json
    {data_dir}/users/{user_id}/projects/{project_id}/exports/
    {data_dir}/users/{user_id}/projects/{project_id}/exports/manifest.json
    {data_dir}/users/{user_id}/projects/{project_id}/versions/{version_id}.json

Writes are atomic (temp file + os.replace) so a crash never leaves a
half-written project on disk.

Phase 19: version sidecars live under versions/ to keep project.json lean.
Each sidecar is a full ProjectVersion (metadata + snapshot). The thumbnail
is computed on the fly during list_versions; it is NOT stored in the sidecar.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.models import ArchitectureProject, DesignOption, ExportManifest
from app.core.models.project import ProjectVersion, ProjectVersionMeta, VersionChangeType
from app.core.storage.base import (
    LOCAL_USER_ID,
    ProjectNotFoundError,
    ProjectStore,
    ProjectSummary,
    StoredProject,
    VersionNotFoundError,
    summarize,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Thumbnail generator ───────────────────────────────────────────────────────

_ROOM_COLORS: dict[str, str] = {
    "living":         "#fef3c7",
    "dining":         "#fde68a",
    "kitchen":        "#d1fae5",
    "bedroom":        "#dbeafe",
    "master_bedroom": "#ede9fe",
    "bathroom":       "#cffafe",
    "balcony":        "#d9f99d",
    "parking":        "#e5e7eb",
    "storage":        "#f3f4f6",
    "study":          "#fef9c3",
    "foyer":          "#fce7f3",
    "corridor":       "#f3f4f6",
    "seating":        "#fef3c7",
    "service":        "#f3f4f6",
}
_DEFAULT_ROOM_COLOR = "#f3f4f6"


def _thumbnail(project: ArchitectureProject) -> str:
    """Compact 100×100 viewBox inline SVG showing room fills — ~400 bytes."""
    sw = project.site.width or 30
    sd = project.site.depth or 30
    sx = 96 / sw
    sy = 96 / sd
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">',
             '<rect x="0" y="0" width="100" height="100" fill="#f8f7f5" stroke="#d6d3d1" stroke-width="1.5"/>']
    for room in project.rooms:
        x = round(room.x * sx + 2, 1)
        y = round(room.y * sy + 2, 1)
        w = round(room.width * sx, 1)
        h = round(room.depth * sy, 1)
        color = _ROOM_COLORS.get(room.type.lower().replace(" ", "_"), _DEFAULT_ROOM_COLOR)
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="#a8a29e" stroke-width="0.8"/>')
    parts.append('</svg>')
    return "".join(parts)


# ── Default summary ───────────────────────────────────────────────────────────

def _default_summary(change_type: str, project: ArchitectureProject) -> str:
    n = len(project.rooms)
    area = round(sum(r.width * r.depth for r in project.rooms))
    return f"{change_type.capitalize()} — {n} rooms, {area} ft²"


# ── LocalProjectStore ─────────────────────────────────────────────────────────

class LocalProjectStore(ProjectStore):
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    # ── Path helpers ──────────────────────────────────────────────────────────

    def _project_dir(self, user_id: str, project_id: str) -> Path:
        return self.data_dir / "users" / user_id / "projects" / project_id

    def _project_file(self, user_id: str, project_id: str) -> Path:
        return self._project_dir(user_id, project_id) / "project.json"

    def _version_dir(self, user_id: str, project_id: str) -> Path:
        return self._project_dir(user_id, project_id) / "versions"

    def _version_file(self, user_id: str, project_id: str, version_id: str) -> Path:
        return self._version_dir(user_id, project_id) / f"{version_id}.json"

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

    # ── ProjectStore interface ────────────────────────────────────────────────

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
        change_type: VersionChangeType | None = None,
        version_summary: str | None = None,
        user_id: str = LOCAL_USER_ID,
    ) -> StoredProject:
        stored = self._read(user_id, project_id)
        if name is not None:
            stored.name = name.strip() or stored.name
        if prompt is not None:
            stored.prompt = prompt
        if project is not None:
            stored.project = project
            if change_type is not None:
                version = ProjectVersion(
                    version_id=f"v-{uuid4().hex[:12]}",
                    created_at=_now(),
                    change_type=change_type,
                    summary=version_summary or _default_summary(change_type, project),
                    snapshot=project,
                )
                self.append_version(project_id, version, user_id)
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

    # ── Version history (Phase 19) ────────────────────────────────────────────

    def append_version(
        self,
        project_id: str,
        version: ProjectVersion,
        user_id: str = LOCAL_USER_ID,
    ) -> None:
        if not self._project_file(user_id, project_id).exists():
            raise ProjectNotFoundError(project_id)
        self._write_json(
            self._version_file(user_id, project_id, version.version_id),
            version.model_dump_json(indent=2),
        )

    def list_versions(
        self,
        project_id: str,
        user_id: str = LOCAL_USER_ID,
    ) -> list[ProjectVersionMeta]:
        if not self._project_file(user_id, project_id).exists():
            raise ProjectNotFoundError(project_id)
        vdir = self._version_dir(user_id, project_id)
        if not vdir.exists():
            return []
        metas: list[ProjectVersionMeta] = []
        for f in vdir.glob("*.json"):
            ver = ProjectVersion.model_validate_json(f.read_text(encoding="utf-8"))
            area = sum(r.width * r.depth for r in ver.snapshot.rooms)
            metas.append(ProjectVersionMeta(
                version_id=ver.version_id,
                created_at=ver.created_at,
                change_type=ver.change_type,
                summary=ver.summary,
                room_count=len(ver.snapshot.rooms),
                total_area=round(area, 1),
                thumbnail=_thumbnail(ver.snapshot),
            ))
        metas.sort(key=lambda m: m.created_at, reverse=True)
        return metas

    def get_version(
        self,
        project_id: str,
        version_id: str,
        user_id: str = LOCAL_USER_ID,
    ) -> ProjectVersion:
        if not self._project_file(user_id, project_id).exists():
            raise ProjectNotFoundError(project_id)
        vfile = self._version_file(user_id, project_id, version_id)
        if not vfile.exists():
            raise VersionNotFoundError(version_id)
        return ProjectVersion.model_validate_json(vfile.read_text(encoding="utf-8"))
