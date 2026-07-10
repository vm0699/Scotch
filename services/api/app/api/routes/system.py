"""System API — local environment probing for the marketing site.

GET /system/integrations  →  which desktop host apps (Revit, SketchUp, Rhino,
    Blender) are installed on this machine. Powers the live "Detected on this
    PC" badge on the landing page. Browser code can't see local installs; only
    this local backend can, so the badge is meaningful only while the backend
    is running.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.system import detect_integrations

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/integrations", summary="Detect installed desktop host apps")
def get_integrations() -> dict:
    """Probe the OS for installed host apps. Always 200; never raises."""
    return detect_integrations()
