"""SQLite project index — Phase 18.2.

A fast listing accelerator that avoids scanning the project directory tree
to populate the dashboard. Stores one row per (user_id, project_id) with
the summary fields needed for ProjectSummary, ordered by updated_at DESC.

Usage:
  The LocalProjectStore can optionally be composed with this index.
  The Cloud backend will use Postgres instead (see database-strategy.md).

Interface:
  ProjectIndex (ABC-like base class)
  SqliteProjectIndex — SQLite3 implementation (ships with Python, zero deps)

Parity guarantee:
  For any set of projects written via LocalProjectStore, the SqliteProjectIndex
  returns list() results equivalent to LocalProjectStore.list_projects().
  The parity test in test_cloud_readiness.py verifies this invariant.
"""

import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from app.core.storage.base import ProjectSummary


class ProjectIndex(ABC):
    """Interface for a fast project listing index.

    Implementations must maintain eventual consistency with the authoritative
    store (LocalProjectStore / CloudProjectStore). The index is only used for
    listing; all reads/writes of full project data still go through ProjectStore.
    """

    @abstractmethod
    def upsert(self, user_id: str, summary: ProjectSummary) -> None:
        """Insert or replace a project summary row."""
        ...

    @abstractmethod
    def remove(self, user_id: str, project_id: str) -> None:
        """Delete a project row from the index."""
        ...

    @abstractmethod
    def list(self, user_id: str) -> list[ProjectSummary]:
        """Return all project summaries for user_id, newest first."""
        ...


class SqliteProjectIndex(ProjectIndex):
    """SQLite-backed project index.

    Schema:
      project_index (user_id TEXT, project_id TEXT, name TEXT, prompt TEXT,
                     created_at TEXT, updated_at TEXT,
                     room_count INTEGER, site_label TEXT,
                     PRIMARY KEY (user_id, project_id))

    created_at / updated_at are stored as ISO-8601 UTC strings so ordering
    works with plain string comparison (no datetime type needed in SQLite).
    """

    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS project_index (
            user_id     TEXT NOT NULL,
            project_id  TEXT NOT NULL,
            name        TEXT NOT NULL,
            prompt      TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            room_count  INTEGER DEFAULT 0,
            site_label  TEXT,
            PRIMARY KEY (user_id, project_id)
        )
    """
    _CREATE_IDX = """
        CREATE INDEX IF NOT EXISTS idx_user_updated
        ON project_index (user_id, updated_at DESC)
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(self._CREATE_TABLE)
            conn.execute(self._CREATE_IDX)

    @staticmethod
    def _to_iso(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    @staticmethod
    def _from_iso(s: str) -> datetime:
        return datetime.fromisoformat(s)

    def upsert(self, user_id: str, summary: ProjectSummary) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO project_index
                  (user_id, project_id, name, prompt,
                   created_at, updated_at, room_count, site_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    summary.id,
                    summary.name,
                    summary.prompt,
                    self._to_iso(summary.created_at),
                    self._to_iso(summary.updated_at),
                    summary.room_count,
                    summary.site_label,
                ),
            )

    def remove(self, user_id: str, project_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM project_index WHERE user_id = ? AND project_id = ?",
                (user_id, project_id),
            )

    def list(self, user_id: str) -> list[ProjectSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT project_id, name, prompt,
                       created_at, updated_at, room_count, site_label
                FROM   project_index
                WHERE  user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()

        return [
            ProjectSummary(
                id=row["project_id"],
                name=row["name"],
                prompt=row["prompt"],
                created_at=self._from_iso(row["created_at"]),
                updated_at=self._from_iso(row["updated_at"]),
                room_count=row["room_count"] or 0,
                site_label=row["site_label"],
            )
            for row in rows
        ]
