"""Scotch ↔ Rhino Bidirectional Sync — Phase 27.6

RhinoPython script implementing the Phase 25 sync protocol against a local
Scotch backend.  Run from Rhino 7 / 8:
  Tools → PythonScript → Edit → open this file → Run Script

Two modes:
  PUSH=False (default) — PULL: GET /projects/{id}/sync → rebuild Rhino geometry.
  PUSH=True            — PUSH: read Scotch layer → POST /projects/{id}/sync.

Layers created on pull:
  Scotch::Rooms::{room_type}  — one AnnotatedBox (Surface) per room
  Scotch::Labels               — text dot labels (name + area)

On push the script reads AnnotatedBox objects from layers named
"Scotch::Rooms::*" and constructs SyncRoom payloads from their bounding boxes.

Grasshopper cluster spec (see docs/integrations/rhino.md):
  Inputs:  project_id <str>, push <bool>, api_url <str>
  Output:  result_json <str>  (raw SyncContract or SyncPushResponse JSON)
  Cluster wraps this script via PythonScript GH component.
"""

from __future__ import annotations

import json
import math

try:
    # Rhino 7/8 — Python 3
    from urllib.request import Request, urlopen
    from urllib.error import URLError
except ImportError:
    # IronPython 2 fallback (Rhino 6)
    from urllib2 import Request, urlopen, URLError  # type: ignore[no-reattr,import]

import rhinoscriptsyntax as rs

# ── USER CONFIG ────────────────────────────────────────────────────────────────
PROJECT_ID = "local-user"       # Scotch project ID (from workspace URL)
API_BASE   = "http://localhost:8000"
PUSH       = False              # False = pull from Scotch; True = push Rhino → Scotch
LATITUDE   = 20.0               # degrees N (India default for sun context)
# ──────────────────────────────────────────────────────────────────────────────

_LAYER_ROOT  = "Scotch::Rooms"
_LAYER_LABEL = "Scotch::Labels"

# Rhino unit scale to feet
_unit = rs.UnitSystem()
if _unit == 2:      # meters
    FT = 0.3048
elif _unit == 8:    # feet
    FT = 1.0
else:               # mm or unknown
    FT = 304.8


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _get(path: str):
    url = f"{API_BASE}{path}"
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        rs.MessageBox(
            f"Cannot reach Scotch backend:\n{url}\n\nError: {exc}\n\n"
            "Make sure the backend is running:\n"
            "  cd services/api\n  uvicorn app.main:app --reload --port 8000",
            title="Scotch — connection error",
        )
        return None


def _post(path: str, payload: dict):
    url = f"{API_BASE}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        rs.MessageBox(
            f"Scotch sync POST failed:\n{url}\n\nError: {exc}",
            title="Scotch — push error",
        )
        return None


# ── Layer management ───────────────────────────────────────────────────────────

def _ensure_layer(name: str, color=None) -> str:
    if not rs.IsLayer(name):
        rs.AddLayer(name, color=color)
    return name


def _room_layer(room_type: str) -> str:
    parent = _ensure_layer(_LAYER_ROOT)
    child  = f"{_LAYER_ROOT}::{room_type}"
    if not rs.IsLayer(child):
        rs.AddLayer(child, parent=parent)
    return child


def _label_layer() -> str:
    return _ensure_layer(_LAYER_LABEL)


# ── Geometry helpers ───────────────────────────────────────────────────────────

def _box_from_room(room: dict) -> object | None:
    """Create a box for a room (x/y in feet, converted to Rhino units)."""
    x  = room["x"]  * FT
    y  = room["y"]  * FT
    w  = room["width"]  * FT
    d  = room["depth"]  * FT
    h  = 3.0 * FT          # default ceiling height, ft

    corners = [
        [x,     y,     0],
        [x + w, y,     0],
        [x + w, y + d, 0],
        [x,     y + d, 0],
        [x,     y,     h],
        [x + w, y,     h],
        [x + w, y + d, h],
        [x,     y + d, h],
    ]
    return rs.AddBox(corners)


def _label_for_room(room: dict):
    """Place a TextDot at the room centroid."""
    cx = (room["x"] + room["width"]  / 2) * FT
    cy = (room["y"] + room["depth"]  / 2) * FT
    area = room["width"] * room["depth"]
    text = f"{room['name']}\n{area:.0f} ft²"
    dot = rs.AddTextDot(text, [cx, cy, 0.1 * FT])
    if dot:
        rs.ObjectLayer(dot, _label_layer())
    return dot


# ── PULL — Scotch → Rhino ──────────────────────────────────────────────────────

def pull():
    print(f"Pulling sync contract for project '{PROJECT_ID}' …")
    contract = _get(f"/projects/{PROJECT_ID}/sync")
    if contract is None:
        return

    rooms = contract.get("rooms", [])
    if not rooms:
        rs.MessageBox(
            "Scotch returned an empty room list. Generate a project first.",
            title="Scotch — empty project",
        )
        return

    # Purge old Scotch objects
    existing = rs.ObjectsByLayer(_LAYER_ROOT) or []
    for obj in existing:
        rs.DeleteObject(obj)
    existing_labels = rs.ObjectsByLayer(_LAYER_LABEL) or []
    for obj in existing_labels:
        rs.DeleteObject(obj)

    created = 0
    for room in rooms:
        layer = _room_layer(room.get("type", "room"))
        box_id = _box_from_room(room)
        if box_id:
            rs.ObjectLayer(box_id, layer)
            rs.ObjectName(box_id, room["id"])
            created += 1
        _label_for_room(room)

    rs.ZoomExtents()
    print(f"Pull complete — {created} rooms imported from project '{PROJECT_ID}'.")
    rs.MessageBox(
        f"Pulled {created} room(s) from Scotch project '{PROJECT_ID}'.\n\n"
        "Rooms are on Scotch::Rooms::<type> layers.\n"
        "Edit geometry, then re-run with PUSH=True to sync back.",
        title="Scotch — pull complete",
    )


# ── PUSH — Rhino → Scotch ──────────────────────────────────────────────────────

def _scotch_rooms_from_rhino() -> list[dict]:
    """Collect all objects on Scotch::Rooms layers and extract their bboxes."""
    sync_rooms: list[dict] = []
    layers = rs.LayerNames() or []
    for lname in layers:
        if not lname.startswith(_LAYER_ROOT):
            continue
        rtype = lname.split("::")[-1] if "::" in lname else "room"
        objs = rs.ObjectsByLayer(lname) or []
        for obj in objs:
            bb = rs.BoundingBox(obj)
            if bb is None:
                continue
            mn, mx = bb[0], bb[6]
            x_ft  = mn[0] / FT
            y_ft  = mn[1] / FT
            w_ft  = (mx[0] - mn[0]) / FT
            d_ft  = (mx[1] - mn[1]) / FT
            # Retrieve Scotch ID from object name (set during pull)
            rid = rs.ObjectName(obj) or f"rhino-{obj}"
            sync_rooms.append({
                "id":    rid,
                "name":  rtype,
                "type":  rtype,
                "x":     round(x_ft, 3),
                "y":     round(y_ft, 3),
                "width": round(w_ft, 3),
                "depth": round(d_ft, 3),
                "level": 0,
            })
    return sync_rooms


def push():
    print(f"Pushing Rhino rooms to Scotch project '{PROJECT_ID}' …")
    rooms = _scotch_rooms_from_rhino()
    if not rooms:
        rs.MessageBox(
            "No Scotch::Rooms objects found in this Rhino document.\n\n"
            "Pull from Scotch first (set PUSH=False and re-run).",
            title="Scotch — no rooms to push",
        )
        return

    payload = {"rooms": rooms, "source": "rhino"}
    result = _post(f"/projects/{PROJECT_ID}/sync", payload)
    if result is None:
        return

    added    = len(result.get("added",    []))
    updated  = len(result.get("updated",  []))
    flagged  = len(result.get("flagged",  []))
    conflicts = result.get("conflicts", [])

    msg = (
        f"Push complete for project '{PROJECT_ID}'.\n\n"
        f"  Added:   {added}\n"
        f"  Updated: {updated}\n"
        f"  Flagged: {flagged}\n"
    )
    if conflicts:
        msg += f"\n{len(conflicts)} conflict(s) detected:\n"
        for c in conflicts[:5]:
            msg += (
                f"  {c['room_name']}.{c['field']}: "
                f"Scotch={c['scotch_value']:.1f}, "
                f"Rhino={c['incoming_value']:.1f} "
                f"(Δ{c['delta']:+.1f})\n"
            )
        if len(conflicts) > 5:
            msg += f"  … and {len(conflicts) - 5} more.\n"
        msg += "\nReload workspace in Scotch to review conflicts."
    else:
        msg += "\nNo conflicts — all rooms accepted."

    print(msg)
    rs.MessageBox(msg, title="Scotch — push complete")


# ── Grasshopper entry point ────────────────────────────────────────────────────

def run_gh(project_id: str, push_mode: bool = False, api_url: str = API_BASE) -> str:
    """Grasshopper cluster entry point — returns JSON string result.

    Cluster inputs:
      project_id  (string panel)
      push_mode   (boolean toggle)
      api_url     (string panel, default http://localhost:8000)
    Cluster output:
      result_json (string)

    Wire result_json into a JSON Path GH component to extract individual
    room geometry parameters for parametric Grasshopper manipulation.
    """
    global PROJECT_ID, API_BASE, PUSH
    PROJECT_ID = project_id
    API_BASE   = api_url.rstrip("/")
    PUSH       = push_mode

    if push_mode:
        rooms = _scotch_rooms_from_rhino()
        result = _post(f"/projects/{project_id}/sync", {"rooms": rooms, "source": "rhino_gh"})
    else:
        result = _get(f"/projects/{project_id}/sync")

    return json.dumps(result or {}, indent=2)


# ── Script entry ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if PUSH:
        push()
    else:
        pull()
