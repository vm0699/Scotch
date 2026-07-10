"""Phase 34 — File-based persistence for ClientChangeRequest sidecars.

Layout:
    {data_dir}/users/{uid}/projects/{project_id}/changes/{change_id}.json

Each sidecar is a single ClientChangeRequest (with optional embedded AffectedItems).
Writes are atomic (temp file + os.replace).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.changes.models import ChangeStatus, ClientChangeRequest


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChangeStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def _changes_dir(self, user_id: str, project_id: str) -> Path:
        return self.data_dir / "users" / user_id / "projects" / project_id / "changes"

    def _change_file(self, user_id: str, project_id: str, change_id: str) -> Path:
        return self._changes_dir(user_id, project_id) / f"{change_id}.json"

    def _write(self, path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)

    def create(self, user_id: str, project_id: str, request_text: str, source: str = "client", priority: str = "medium") -> ClientChangeRequest:
        change = ClientChangeRequest(
            id=f"chg-{uuid4().hex[:12]}",
            request_text=request_text,
            source=source,  # type: ignore[arg-type]
            priority=priority,  # type: ignore[arg-type]
        )
        self._write(self._change_file(user_id, project_id, change.id), change.model_dump_json(indent=2))
        return change

    def list(self, user_id: str, project_id: str) -> list[ClientChangeRequest]:
        d = self._changes_dir(user_id, project_id)
        if not d.exists():
            return []
        result = []
        for f in sorted(d.glob("chg-*.json"), reverse=True):
            try:
                result.append(ClientChangeRequest.model_validate_json(f.read_text(encoding="utf-8")))
            except Exception:
                pass
        return result

    def get(self, user_id: str, project_id: str, change_id: str) -> ClientChangeRequest:
        f = self._change_file(user_id, project_id, change_id)
        if not f.exists():
            raise KeyError(f"Change '{change_id}' not found")
        return ClientChangeRequest.model_validate_json(f.read_text(encoding="utf-8"))

    def update(self, user_id: str, project_id: str, change: ClientChangeRequest) -> ClientChangeRequest:
        change.updated_at = _now()
        self._write(self._change_file(user_id, project_id, change.id), change.model_dump_json(indent=2))
        return change

    def set_status(self, user_id: str, project_id: str, change_id: str, status: ChangeStatus) -> ClientChangeRequest:
        change = self.get(user_id, project_id, change_id)
        change.status = status
        return self.update(user_id, project_id, change)

    def delete(self, user_id: str, project_id: str, change_id: str) -> None:
        f = self._change_file(user_id, project_id, change_id)
        if f.exists():
            f.unlink()


_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_instance: ChangeStore | None = None


def get_change_store() -> ChangeStore:
    global _instance
    if _instance is None:
        _instance = ChangeStore(_DEFAULT_DATA_DIR)
    return _instance
