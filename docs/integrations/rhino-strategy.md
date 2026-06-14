# Rhino + Grasshopper Strategy — Scotch Integration

> **Phase 11.5 / 16 strategy document.**  
> Full implementation lands in Phase 16; this document specifies the workflow so the Rhino Python exporter (Phase 11.5) can be aligned with it.

---

## 1. Overview

Scotch integrates with Rhino and Grasshopper via two complementary paths:

| Path | Trigger | Output |
|---|---|---|
| **RhinoPython script** | Export → "Rhino (.py)" button | `.py` file run inside Rhino's Python editor |
| **Grasshopper definition** | Provided as a template `.gh` file | Sliders/panels fed from Scotch JSON; parametric model |

The Rhino path is ideal for **massing + wall geometry**. The Grasshopper path is ideal for **parametric exploration** (changing site width or room count drives the entire model).

---

## 2. RhinoPython Script Approach

### 2.1 API surface

Rhino 7/8 exposes `rhinoscriptsyntax` (RS) and `Rhino.Geometry` (RG) in Python:

```python
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
```

### 2.2 What the script creates

```
Scene
  └── Layer: Scotch::Site       — site boundary curve
  └── Layer: Scotch::Rooms      — room boxes (surfaces or solids)
  └── Layer: Scotch::Openings   — door/window void boxes
  └── Layer: Scotch::Roof       — roof surface
  └── Layer: Scotch::Dims       — annotation + leader text
```

### 2.3 Script structure

```python
import json, rhinoscriptsyntax as rs, Rhino.Geometry as rg
from datetime import datetime

# 1. Load project
with open(r"C:\path\to\scotch_project.json") as f:
    proj = json.load(f)

FT = 304.8  # feet → millimetres (Rhino default unit)

# 2. Layers
for name in ["Scotch::Site","Scotch::Rooms","Scotch::Openings","Scotch::Roof","Scotch::Dims"]:
    if not rs.IsLayer(name):
        rs.AddLayer(name)

# 3. Site boundary
site_pts = [(0,0,0),(proj["site"]["width"]*FT,0,0),
            (proj["site"]["width"]*FT,proj["site"]["depth"]*FT,0),
            (0,proj["site"]["depth"]*FT,0)]
rs.AddPolyline(site_pts + [site_pts[0]])
rs.ObjectLayer(rs.LastCreatedObjects()[0], "Scotch::Site")

# 4. Rooms — create solid boxes
WALL_H = proj["building"]["floor_height"] * FT
WALL_T = 0.5 * FT
for room in proj["rooms"]:
    x, y = room["x"]*FT, room["y"]*FT
    w, d = room["width"]*FT, room["depth"]*FT
    box = rg.Box(
        rg.Plane.WorldXY,
        rg.Interval(x - WALL_T/2, x + w + WALL_T/2),
        rg.Interval(y - WALL_T/2, y + d + WALL_T/2),
        rg.Interval(0, WALL_H)
    )
    brep_id = rs.AddBox(...)
    rs.ObjectLayer(brep_id, "Scotch::Rooms")
    rs.ObjectName(brep_id, room["name"])

# 5. Door/window voids (Boolean Difference)
for door in proj["doors"]:
    room = next(r for r in proj["rooms"] if r["id"] == door["room_id"])
    void_brep = _door_void_box(room, door, WALL_H, WALL_T, FT)
    # Store as void object; subtract from room walls using rs.BooleanDifference

# 6. Roof slab
# 7. Annotations / text dots for room names
```

### 2.4 Unit strategy

Rhino's default template unit is **millimetres**. The script converts feet × 304.8. If the Rhino document is already in feet/metres, conversion is adjusted via:

```python
unit_factor = 304.8  # default mm
if rs.UnitSystem() == 2:   # metres
    unit_factor = FT_TO_M  # 0.3048
elif rs.UnitSystem() == 8: # feet
    unit_factor = 1.0
```

### 2.5 Boolean operations

Rhino Boolean Difference is reliable for cutting door/window openings:

```python
void_ids = [...]  # list of void box IDs
wall_ids  = [...]  # list of wall solid IDs
rs.BooleanDifference(wall_ids, void_ids)
```

If Boolean fails (overlapping geometry tolerance), fall back to `rs.MeshBooleanDifference` on the mesh representation.

---

## 3. Grasshopper Parameter Strategy

### 3.1 Overview

A Grasshopper definition (`.gh`) reads the Scotch JSON and exposes all room dimensions as **Number Slider** inputs. Changes to sliders drive live geometry updates.

### 3.2 Data flow

```
JSON File (path input)
    ↓
  Jolt / GH JSON component (Human plugin or Elefront)
  → deserialise rooms / site
    ↓
  Parameter sliders (auto-generated per room: Width, Depth)
    ↓
  Geometry: Surface from Room Boundary → Extrude → Brep
    ↓
  Baked geometry → Rhino model
```

### 3.3 Parametric components (GH definitions)

| GH Component | Purpose |
|---|---|
| `Read File` | load `scotch_project.json` |
| `DeconstructBrep` | extract room faces |
| `Number Slider` (per room) | override width/depth |
| `Rectangle` → `Extrude` | room wall box |
| `Boolean Difference` | cut openings |
| `Bake` button | push to Rhino model |
| `Scotch Export` (custom) | POST updated values to Scotch API |

### 3.4 Custom GH cluster: "Scotch Sync"

A custom cluster (GH group saved as a `.ghuser` file):
- **Input**: Scotch JSON path + rooms data tree
- **Output**: updated room widths/depths after slider changes
- **Sync**: on button press, HTTP POST to `http://localhost:8000/generate/regenerate` with changed parameters

This enables live round-trips: Grasshopper parameter changes → Scotch validation → updated 3D model.

---

## 4. Phase 16 Implementation Sequence

| Stage | Scope |
|---|---|
| 16.1 | RhinoPython script export (site + rooms + openings + roof + dims) |
| 16.2 | Massing import validation (run script, verify geometry in Rhino) |
| 16.3 | Grasshopper definition template (rooms as sliders, basic sync) |
| 16.4 | Parametric facade prototype (window density slider, bay-spacing GH definition) |

---

## 5. Plugin recommendations for users

| Plugin | Purpose | Required? |
|---|---|---|
| **Human** | better JSON reading in GH | Optional |
| **Elefront** | rich attribute management | Optional |
| **Rhino.Inside.Revit** | push Rhino geometry to Revit | Optional |
| **VisualARQ** | architectural objects in Rhino | Optional |

---

## 6. Limitations

- **Rhino Boolean reliability**: complex room layouts with tight tolerances may need manual cleanup.
- **GH live sync**: requires Scotch backend running locally. Cloud version in Phase 18.
- **Grasshopper sliders**: auto-generated definitions require Human or equivalent plugin; base template ships with the plugin-free workaround using data internalized.
- **Revit via Rhino.Inside**: this integration is covered separately in the Revit strategy; do not duplicate.
