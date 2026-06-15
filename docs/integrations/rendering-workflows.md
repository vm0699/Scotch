# Rendering Workflows — Scotch Integration Guide

This document covers how to take a Scotch export into each supported render engine: **Lumion**, **D5 Render**, **Enscape**, **V-Ray**, and **Blender**. It also documents the material naming convention and camera preset system.

---

## 1. Material Naming Convention (render-ready hierarchy)

All Scotch exports use a consistent naming scheme so render engines can auto-map materials by object name:

| Object / group prefix | Material | Render engine target |
|---|---|---|
| `Scotch_Wall_<room>` | `Scotch_Wall` — off-white matte paint, roughness 0.70 | Wall surfaces |
| `Scotch_Floor_<room>` | `Scotch_Floor` — polished stone, roughness 0.50 | Floor interior |
| `Scotch_Roof` | `Scotch_Roof` — concrete, roughness 0.85 | Roof slab |
| `Scotch_Glass_<room>_Door_*` | `Scotch_Glass` — clear glass, roughness 0.05 | Door openings |
| `Scotch_Glass_<room>_Win_*` | `Scotch_Glass` — clear glass, roughness 0.05 | Window openings |
| `Scotch_Ground` | `Scotch_Ground` — landscaping, roughness 0.90 | Site ground plane |
| `Scotch_Room_<type>` | Per-room type (bedroom, kitchen, etc.) | Interior floors |

Color and roughness hints are stored in `project.materials` and carried directly into Blender (Principled BSDF) and SketchUp material definitions. GLTF exports name each mesh object using this scheme so KHR_materials can be auto-assigned.

---

## 2. Camera Presets

The `GET /projects/{id}/cameras` endpoint returns 5 render-ready camera suggestions derived from your site geometry:

| Preset name | Type | Description |
|---|---|---|
| `exterior_quarter` | Perspective (45°) | NE corner, elevated — classic architectural 3/4 view |
| `top_ortho` | Orthographic | Top-down plan view for aerial renders |
| `street_eye` | Perspective (60°) | Street-level from entrance side at 5.5 ft eye height |
| `living_interior` | Perspective (75°) | Interior of the living room |
| `balcony_view` | Perspective (65°) | From balcony looking into building (or NW corner if no balcony) |

Camera positions use `[plan_x, height, plan_y]` which maps directly to three.js `[x, y, z]`. The 3D viewer toolbar shows a **Camera** icon when a saved project is open — click to jump to any preset.

---

## 3. Blender (Native)

Scotch exports a self-contained `.py` script (`POST /projects/{id}/exports/blender`) that rebuilds the full scene.

### Run interactively
```
1. Open Blender → Scripting workspace
2. File → Open → select floor_plan_blender.py
3. Run Script (▶)
```

### Run headless
```
blender --background --python floor_plan_blender.py
# Output: /tmp/scotch_render/0001.png  (EEVEE, 1920×1080)
```

### Scene structure
| Collection | Contents |
|---|---|
| `Scotch_Site` | Ground slab (`Scotch_Ground`) |
| `Scotch_Walls` | Room wall boxes (`Scotch_Wall_<room>`) |
| `Scotch_Floors` | Room interior volumes — hidden after Boolean |
| `Scotch_Roof` | Roof slab |
| `Scotch_Glass` | Door and window glass openings |
| `Scotch_Lighting` | Sun key · Area fill · Rim light |
| `Scotch_Cameras` | 5 presets with Track-To constraints |

### Render engines
- **EEVEE** (default) — fast, near-real-time
- **Cycles** — uncomment `scene.render.engine = 'CYCLES'` for path-traced quality
- **Cycles settings**: 256 samples + denoising already included (commented out)

### Apply Boolean modifiers
After import, select each `Scotch_Wall_<room>` object → Properties → Modifiers → Apply all Boolean modifiers to hollow the rooms.

---

## 4. Lumion

Lumion imports via **.skp** (SketchUp) or **.fbx**.

### Via SketchUp (recommended)
1. Export from Scotch: `POST /projects/{id}/exports/sketchup` → `floor_plan.rb`
2. In SketchUp: Extensions → Ruby Console → Open file → Run
3. File → Save As → `.skp`
4. In Lumion: Import → SketchUp file
5. **Material reassignment**: Lumion shows all SketchUp materials by name — the Scotch naming scheme (`Scotch_Wall`, `Scotch_Roof`, etc.) lets you bulk-assign in the Materials panel.

### Via FBX
- Export `.skp` → SketchUp's File → Export → 3D Model → `.fbx`
- Import into Lumion with the FBX dialog

### Camera starting points
- Use exterior_quarter position as a starting point for Lumion's Camera Path
- Street-level preview from `street_eye` camera preset

---

## 5. D5 Render

D5 imports via **.skp** (live-link plugin) or **.gltf / .glb**.

### Via SketchUp live-link
1. Install the D5 Converter for SketchUp
2. Import the Scotch `.rb` script into SketchUp (see above)
3. Use D5's "Sync" button for live updates

### Via GLTF (render-ready)
1. Open the workspace 3D tab → click the **Box** (GLTF) button to export `massing.gltf`
2. In D5: File → Import → GLTF/GLB
3. Mesh objects are named `Scotch_Wall_<room>`, `Scotch_Glass_*`, etc. — use D5's material picker to assign render materials by object name.

### Material tips
- Assign D5's Plaster/Render material to all `Scotch_Wall_*` objects
- Assign D5's Glass material to all `Scotch_Glass_*` objects
- Use roughness hint from `project.materials` as a starting point for D5's roughness slider

---

## 6. Enscape (via SketchUp live-link)

Enscape integrates directly inside SketchUp — the Scotch workflow is:

1. Export `floor_plan.rb` from Scotch
2. Run in SketchUp (Ruby Console or Extensions → Scotch Importer)
3. Launch Enscape from the SketchUp Extensions menu
4. Live-link updates as you edit the SketchUp model

### Camera views in Enscape
- Set up Enscape Viewpoints matching the 5 Scotch camera suggestions (use coordinates from `GET /projects/{id}/cameras`)
- `exterior_quarter`: high-angle exterior → good for still renders
- `street_eye`: 5.5 ft eye height → exterior walkthrough starting point
- `living_interior`: interior walkthrough

### Material reassignment
Enscape reads SketchUp materials — the Scotch names (`Scotch_Wall`, `Scotch_Glass`, etc.) appear in the Enscape Material Editor, where you can assign PBR textures.

---

## 7. V-Ray (via Rhino or SketchUp)

### Via Rhino + V-Ray for Rhino
1. Export `floor_plan_rhino.py` from Scotch: `POST /projects/{id}/exports/rhino`
2. Run in Rhino: Tools → PythonScript → Run
3. V-Ray panel → Render — geometry, layers, and camera suggestions are all set
4. The script sets layers (`Scotch::Walls`, `Scotch::Roof`, etc.) which V-Ray reads for material assignment

### Via SketchUp + V-Ray for SketchUp
1. Import via `.rb` as above
2. V-Ray for SketchUp reads SketchUp materials directly by name
3. Assign V-Ray materials to `Scotch_Wall`, `Scotch_Floor`, `Scotch_Roof`, `Scotch_Glass`

### Camera
- Rhino script includes camera presets at the same positions as `GET /projects/{id}/cameras`
- V-Ray Physical Camera: set ISO 200, Shutter 1/125s, F/8 for daylight exterior

---

## 8. Quick Reference

| Engine | Best import path | Material mapping | Live-link? |
|---|---|---|---|
| Blender | `.py` script (native) | Principled BSDF by object name | No (re-run script) |
| Lumion | `.skp` via SketchUp | Material name from Scotch | No |
| D5 Render | `.gltf` or `.skp` | Object/mesh name | Yes (via SketchUp) |
| Enscape | `.skp` via SketchUp live-link | SketchUp material name | Yes |
| V-Ray | `.py` via Rhino | Rhino layer name | No |

---

## 9. Tips for All Engines

- **Scale**: Scotch works in feet. All exporters convert to the target unit (metres for Blender/GLTF, inches for SketchUp). Verify your render engine project units match.
- **Boolean modifiers**: In Blender, apply Boolean modifiers before exporting to other formats (FBX, GLTF) to solidify the hollow room walls.
- **Sun direction**: Use `site.orientation` from the project to orient the sun correctly. East-facing entrance → afternoon sun from the west.
- **Camera FOV**: `exterior_quarter` = 45°, `street_eye` = 60°, `living_interior` = 75°. These map to focal lengths of approximately 47 mm, 32 mm, 24 mm on a 35 mm sensor.
- **HDRI sky**: For Blender/D5/V-Ray, replace the flat sky color with an HDRI matching the site orientation. Noon summer sky works well for most residential exteriors.
