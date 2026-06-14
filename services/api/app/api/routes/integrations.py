"""Integrations API — Phase 15.

GET /integrations/sketchup/extension  →  scotch_importer.rbz (zip of the
    extension files: scotch_importer.rb + scotch/ subfolder).

The .rbz format is just a zip; SketchUp Extension Manager accepts it directly.
"""

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Absolute path to the integrations/ folder at the repo root.
_INTEGRATIONS_ROOT = Path(__file__).resolve().parents[5] / "integrations"
_SKETCHUP_ROOT = _INTEGRATIONS_ROOT / "sketchup"


def _build_extension_zip() -> bytes:
    """Zip the scotch_importer.rb + scotch/ folder into a .rbz byte string."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Top-level registration file
        reg_file = _SKETCHUP_ROOT / "scotch_importer.rb"
        if reg_file.exists():
            zf.write(reg_file, "scotch_importer.rb")

        # scotch/ subfolder
        scotch_dir = _SKETCHUP_ROOT / "scotch"
        if scotch_dir.is_dir():
            for rb_file in sorted(scotch_dir.glob("*.rb")):
                zf.write(rb_file, f"scotch/{rb_file.name}")

    return buf.getvalue()


@router.get("/sketchup/extension")
def download_sketchup_extension() -> StreamingResponse:
    """Download the Scotch SketchUp extension as a .rbz file.

    The caller saves it as `scotch_importer.rbz` and installs it via
    SketchUp's Extension Manager (Window > Extension Manager > Install Extension).
    """
    data = _build_extension_zip()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="scotch_importer.rbz"',
            "Content-Length": str(len(data)),
        },
    )


@router.get("/sketchup/extension/files")
def list_extension_files() -> dict:
    """List the files that will be included in the extension zip."""
    files: list[str] = []
    reg_file = _SKETCHUP_ROOT / "scotch_importer.rb"
    if reg_file.exists():
        files.append("scotch_importer.rb")

    scotch_dir = _SKETCHUP_ROOT / "scotch"
    if scotch_dir.is_dir():
        for rb_file in sorted(scotch_dir.glob("*.rb")):
            files.append(f"scotch/{rb_file.name}")

    return {"extension": "scotch_importer.rbz", "version": "1.0.0", "files": files}
