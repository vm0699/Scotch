"""Room schedule exporters — Phase 13.4.

Produces JSON and CSV schedules with gross and carpet areas.
"""

import csv
import io
import json
from pathlib import Path

from app.core.models import ArchitectureProject


def _schedule_rows(project: ArchitectureProject) -> list[dict]:
    unit = "ft" if project.units == "feet" else "m"
    rows = []
    for i, room in enumerate(project.rooms, 1):
        gross  = round(room.width * room.depth, 2)
        carpet = round(gross * 0.85, 2)
        rows.append({
            "no":          i,
            "name":        room.name,
            "type":        room.type,
            "floor":       room.level + 1,
            "width":       room.width,
            "depth":       room.depth,
            "unit":        unit,
            "gross_area":  gross,
            "carpet_area": carpet,
        })
    return rows


def export_schedule_json(project: ArchitectureProject, output_path: Path) -> bytes:
    rows = _schedule_rows(project)
    payload = {
        "project":            project.name,
        "units":              project.units,
        "total_rooms":        len(rows),
        "total_gross_area":   round(sum(r["gross_area"] for r in rows), 2),
        "total_carpet_area":  round(sum(r["carpet_area"] for r in rows), 2),
        "rooms":              rows,
    }
    data = json.dumps(payload, indent=2).encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return data


def export_schedule_csv(project: ArchitectureProject, output_path: Path) -> bytes:
    rows = _schedule_rows(project)
    unit = "ft" if project.units == "feet" else "m"
    u2   = f"{unit}²"
    fields = ["No", "Room Name", "Type", "Floor",
              f"Width ({unit})", f"Depth ({unit})",
              f"Gross Area ({u2})", f"Carpet Area ({u2})"]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for r in rows:
        writer.writerow({
            "No":                 r["no"],
            "Room Name":          r["name"],
            "Type":               r["type"],
            "Floor":              r["floor"],
            f"Width ({unit})":    r["width"],
            f"Depth ({unit})":    r["depth"],
            f"Gross Area ({u2})": r["gross_area"],
            f"Carpet Area ({u2})":r["carpet_area"],
        })

    data = buf.getvalue().encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return data
