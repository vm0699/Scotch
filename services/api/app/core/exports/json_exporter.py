"""Stage 7.1 — JSON export.

Serialises the full ArchitectureProject as pretty-printed JSON and writes it
to the given output path, returning the file bytes.
"""

from pathlib import Path

from app.core.models import ArchitectureProject


def export_json(project: ArchitectureProject, output_path: Path) -> bytes:
    data = project.model_dump_json(indent=2).encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return data
