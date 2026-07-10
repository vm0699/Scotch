"""Scotch sync protocol — bidirectional model synchronisation.

External tools (SketchUp, Revit, Rhino) push a SyncPayload after the user
edits their local copy; the engine merges it into the canonical model,
runs validation, and returns the updated project plus a diff summary.

The inverse direction (pull) projects the canonical model into a minimal
SyncContract that plugins use to reconstruct or reposition geometry.
"""

from app.core.sync.engine import project_to_sync_contract, push_sync
from app.core.sync.models import (
    ConflictItem,
    SyncContract,
    SyncDiff,
    SyncPayload,
    SyncRoom,
)

__all__ = [
    "ConflictItem",
    "SyncContract",
    "SyncDiff",
    "SyncPayload",
    "SyncRoom",
    "project_to_sync_contract",
    "push_sync",
]
