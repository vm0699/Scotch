"""System probing — detect locally installed desktop host apps.

The browser cannot see what is installed on the user's machine; only this
local backend can. `detect.detect_integrations()` reports whether the host
apps the Scotch integrations target (Revit, SketchUp, Rhino, Blender) are
present on this computer, so the marketing site can show a live
"Detected on this PC" badge.
"""

from app.core.system.detect import detect_integrations

__all__ = ["detect_integrations"]
