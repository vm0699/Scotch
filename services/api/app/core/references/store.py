"""Phase 39 — File-based persistence for ReferenceAsset sidecars.

Layout:
    {data_dir}/users/{uid}/projects/{project_id}/references/{asset_id}.json  ← metadata
    {data_dir}/users/{uid}/projects/{project_id}/references/files/{filename}  ← binary file

Writes are atomic (temp + os.replace). Deleting an asset removes both.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.references.models import ReferenceAsset, ScaleCalibration, ScaleStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReferenceStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    # ── Path helpers ──────────────────────────────────────────────────────────

    def _refs_dir(self, user_id: str, project_id: str) -> Path:
        return self.data_dir / "users" / user_id / "projects" / project_id / "references"

    def _files_dir(self, user_id: str, project_id: str) -> Path:
        return self._refs_dir(user_id, project_id) / "files"

    def _meta_file(self, user_id: str, project_id: str, asset_id: str) -> Path:
        return self._refs_dir(user_id, project_id) / f"{asset_id}.json"

    def _write_meta(self, path: Path, asset: ReferenceAsset) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(asset.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(
        self,
        user_id: str,
        project_id: str,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        reference_type: str = "reference_image",
        notes: str = "",
    ) -> ReferenceAsset:
        asset_id = f"ref-{uuid4().hex[:12]}"

        # Write binary file
        files_dir = self._files_dir(user_id, project_id)
        files_dir.mkdir(parents=True, exist_ok=True)
        # Make file_name safe (no path separators)
        safe_name = Path(file_name).name.replace("..", "").strip()
        # Prefix with asset_id to avoid collisions
        stored_name = f"{asset_id}_{safe_name}"
        file_path = files_dir / stored_name
        file_path.write_bytes(file_bytes)

        asset = ReferenceAsset(
            id=asset_id,
            project_id=project_id,
            file_name=safe_name,
            file_path=stored_name,
            mime_type=mime_type,
            file_size_bytes=len(file_bytes),
            reference_type=reference_type,  # type: ignore[arg-type]
            notes=notes,
        )
        self._write_meta(self._meta_file(user_id, project_id, asset_id), asset)
        return asset

    def list(self, user_id: str, project_id: str) -> list[ReferenceAsset]:
        refs_dir = self._refs_dir(user_id, project_id)
        if not refs_dir.exists():
            return []
        result: list[ReferenceAsset] = []
        for f in sorted(refs_dir.glob("ref-*.json"), reverse=True):
            try:
                result.append(ReferenceAsset.model_validate_json(f.read_text(encoding="utf-8")))
            except Exception:
                pass
        return result

    def get(self, user_id: str, project_id: str, asset_id: str) -> ReferenceAsset:
        meta = self._meta_file(user_id, project_id, asset_id)
        if not meta.exists():
            raise KeyError(f"Reference asset '{asset_id}' not found")
        return ReferenceAsset.model_validate_json(meta.read_text(encoding="utf-8"))

    def update(self, user_id: str, project_id: str, asset: ReferenceAsset) -> ReferenceAsset:
        asset.updated_at = _now()
        self._write_meta(self._meta_file(user_id, project_id, asset.id), asset)
        return asset

    def delete(self, user_id: str, project_id: str, asset_id: str) -> None:
        asset = self.get(user_id, project_id, asset_id)
        # Remove binary file
        bin_file = self._files_dir(user_id, project_id) / asset.file_path
        if bin_file.exists():
            bin_file.unlink()
        # Remove metadata
        self._meta_file(user_id, project_id, asset_id).unlink(missing_ok=True)

    def get_file_path(self, user_id: str, project_id: str, asset_id: str) -> Path:
        asset = self.get(user_id, project_id, asset_id)
        return self._files_dir(user_id, project_id) / asset.file_path

    def set_calibration(
        self,
        user_id: str,
        project_id: str,
        asset_id: str,
        calibration: ScaleCalibration,
    ) -> ReferenceAsset:
        asset = self.get(user_id, project_id, asset_id)
        asset.calibration = calibration
        asset.scale_status = "calibrated"
        return self.update(user_id, project_id, asset)

    def add_extracted_entity(
        self,
        user_id: str,
        project_id: str,
        asset_id: str,
        entity_type: str,
        geometry: dict,
        label: str | None = None,
        confidence: float = 1.0,
    ):
        from app.core.references.models import ExtractedEntity
        asset = self.get(user_id, project_id, asset_id)
        entity = ExtractedEntity(
            id=f"ent-{uuid4().hex[:8]}",
            entity_type=entity_type,
            geometry=geometry,
            label=label,
            confidence=confidence,
        )
        asset.extracted_entities.append(entity)
        return self.update(user_id, project_id, asset)


_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_instance: ReferenceStore | None = None


def get_reference_store() -> ReferenceStore:
    global _instance
    if _instance is None:
        _instance = ReferenceStore(_DEFAULT_DATA_DIR)
    return _instance
