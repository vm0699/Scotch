"""Cloud storage stub — Phase 18.4.

CloudProjectStore satisfies the ProjectStore ABC so the type system and
factory wiring work today. Every method raises NotImplementedError until a
real cloud implementation (S3/Supabase) is added post-Phase 20.

This class is the contract lock: if ProjectStore grows a new abstract method,
this stub fails to instantiate at import time, surfacing the gap before any
production deployment.

Configuration needed when implemented (set via env / .env):
  SCOTCH_CLOUD_BUCKET      — S3 bucket or Supabase storage bucket name
  SCOTCH_CLOUD_REGION      — AWS/Supabase region (e.g. "us-east-1")
  SCOTCH_CLOUD_ACCESS_KEY  — IAM / service-role key
  SCOTCH_CLOUD_SECRET_KEY  — corresponding secret
  SCOTCH_CLOUD_DB_URL      — Postgres connection string for the metadata index

Expected object layout (mirrors the local tree exactly):
  users/{user_id}/projects/{project_id}/project.json
  users/{user_id}/projects/{project_id}/exports/{filename}
  users/{user_id}/projects/{project_id}/exports/manifest.json

See docs/architecture/cloud-storage-strategy.md for full mapping.
"""

from pathlib import Path

from app.core.models import ArchitectureProject, DesignOption, ExportManifest
from app.core.models.project import ProjectVersion, ProjectVersionMeta, VersionChangeType
from app.core.storage.base import (
    LOCAL_USER_ID,
    ProjectStore,
    ProjectSummary,
    StoredProject,
)


class CloudProjectStore(ProjectStore):
    """Stub cloud backend — raises NotImplementedError on every call.

    Activate via SCOTCH_STORAGE_BACKEND=cloud once the implementation lands.
    """

    def __init__(self, bucket: str = "", region: str = "") -> None:
        self.bucket = bucket
        self.region = region

    # ── ProjectStore interface (all stubs) ────────────────────────────────────

    def create_project(
        self,
        name: str,
        prompt: str | None = None,
        project: ArchitectureProject | None = None,
        user_id: str = LOCAL_USER_ID,
    ) -> StoredProject:
        raise NotImplementedError("CloudProjectStore: create_project not implemented")

    def list_projects(self, user_id: str = LOCAL_USER_ID) -> list[ProjectSummary]:
        raise NotImplementedError("CloudProjectStore: list_projects not implemented")

    def get_project(
        self, project_id: str, user_id: str = LOCAL_USER_ID
    ) -> StoredProject:
        raise NotImplementedError("CloudProjectStore: get_project not implemented")

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
        raise NotImplementedError("CloudProjectStore: update_project not implemented")

    def delete_project(
        self, project_id: str, user_id: str = LOCAL_USER_ID
    ) -> None:
        raise NotImplementedError("CloudProjectStore: delete_project not implemented")

    def save_export_manifest(
        self,
        project_id: str,
        manifest: ExportManifest,
        user_id: str = LOCAL_USER_ID,
    ) -> None:
        raise NotImplementedError(
            "CloudProjectStore: save_export_manifest not implemented"
        )

    def list_export_manifests(
        self, project_id: str, user_id: str = LOCAL_USER_ID
    ) -> list[ExportManifest]:
        raise NotImplementedError(
            "CloudProjectStore: list_export_manifests not implemented"
        )

    def get_export_path(
        self, project_id: str, filename: str, user_id: str = LOCAL_USER_ID
    ) -> Path:
        raise NotImplementedError("CloudProjectStore: get_export_path not implemented")

    def append_version(
        self, project_id: str, version: ProjectVersion, user_id: str = LOCAL_USER_ID
    ) -> None:
        raise NotImplementedError("CloudProjectStore: append_version not implemented")

    def list_versions(
        self, project_id: str, user_id: str = LOCAL_USER_ID
    ) -> list[ProjectVersionMeta]:
        raise NotImplementedError("CloudProjectStore: list_versions not implemented")

    def get_version(
        self, project_id: str, version_id: str, user_id: str = LOCAL_USER_ID
    ) -> ProjectVersion:
        raise NotImplementedError("CloudProjectStore: get_version not implemented")
