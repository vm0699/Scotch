# Session Handoff — Implement Phases 11, 12, 13, 14

> Updated 2026-06-13 at the close of Phase 10. Read [CLAUDE.md](../CLAUDE.md) first, then this file. Live status tracker: [docs/product/roadmap.md](product/roadmap.md).

## Where the product stands (Phases 0–10 ✅)

Scotch is a working local product end-to-end. Every stage of the core pipeline is live:

```
prompt → requirement parser → ArchitectureProject JSON → validator
       → 2D SVG floor plan (architectural grade) → 3D massing (R3F/Three.js)
       → on-canvas + panel editing → regenerate → JSON/SVG/PNG/DXF export
       → AI generation (Anthropic/OpenAI-compatible/hybrid) → design options (compact/balanced/spacious)
```

- **Run:** `npm run dev:api` (FastAPI :8000) + `npm run dev:web` (Next.js :3000). Tests: `npm run test:api`.
- **149 backend pytest cases**, all green. Strict TypeScript, clean builds.
- **Working tree clean** at commit `5bba39b` (`Phase 10: Design Options MVP`).
- **Process the user expects:** whole phase done in one run with per-stage commits; send PushNotification at phase close with the Stage Completion Format (Phase / Stage / Summary / Files created / Files modified / How to test / What works / Limitations / Next stage). Ask "Should I continue?" between stages. Never ship "basic" UI — CADAM-grade only.

### Phases completed

| Phase | What was built |
|---|---|
| 0–4 | Product plan, local skeleton, CADAM UI shell, universal data model, project CRUD storage |
| 5 | Deterministic text-to-floorplan: requirement parser → zoned band-packing generator → validated project |
| 6 | Editable parameters: panel editor + on-canvas popover (CADAM-style click-to-edit), regeneration API |
| 7 | Export MVP: JSON, layered SVG, PNG (Pillow direct-draw), DXF (ezdxf); manifest tracking; download panel |
| 8 | 3D massing: R3F viewer in the 3D tab; slab/wall/glass boxes from project geometry; GLTF export button |
| 9 | AI provider integration: DeterministicProvider / AnthropicProvider / OpenAICompatibleProvider / HybridProvider; schema repair; deterministic/AI/hybrid mode toggle; settings UI; keys never echoed |
| 10 | Design options: compact (0.82×) / balanced (1.0×) / spacious (1.20×) variants; OptionsPanel with mini SVG plan cards; apply → active design; options persisted with project |

---

## Load-bearing architecture facts

**Read these before touching any code. Violations cause silent divergence.**

### The data model

- `ArchitectureProject` is the single source of truth. Pydantic: [`services/api/app/core/models/project.py`](../services/api/app/core/models/project.py). TypeScript mirror: [`apps/web/src/features/project/types.ts`](../apps/web/src/features/project/types.ts) (snake_case, 1:1 — never let them drift).
- `DesignOption(option_id, variant, score, summary, warnings, preview: ArchitectureProject)` was added in Phase 10.
- `StoredProject` carries `project: ArchitectureProject | None` and `options: list[DesignOption] = []`. Stored at `app/data/users/local-user/projects/{id}/project.json`.
- Key relationships: `Room.id` is the foreign key for `Door.room_id`, `Window.room_id`, `Parameter.target_id`, `Wall.room_id`. Every change that touches IDs must stay consistent.

### Plan geometry

- **x** across site width, **y** along site depth, **y = 0 is the entrance edge (drawn at the top of the SVG)**. Door/window `wall` is plan-local: north = top/entrance, south = bottom, west = left, east = right.
- Units: **feet** everywhere (default). `SCALE = 12` px/ft in the SVG renderer. `WALL_T = 0.5` ft. `MARGIN = 64` px around the site for dimensions + north arrow.
- The 3D viewer maps plan `(x, y)` → Three.js `(x, z)` (y-up). `building.floor_height` drives wall extrusion height.

### Generator internals

`floorplan_generator.py` — zoned band-packing. Key helpers:
- `_Spec(id, name, type, width, depth)` — a room before it has a position.
- `_GenState.warnings` — collects all generation warnings.
- `_pack_bands(bands, site_width, site_depth, state) -> list[Room]` — row-wrap packing; emits depth-compression warning when total depth > site depth. **Reused by `regenerate.py` and `options_generator.py` — reuse, don't duplicate.**
- `_openings(rooms, site_width, state) -> (doors, windows)` — derives door swings + window symbols from room positions.
- `DesignRequirements.size_modifier: float = 1.0` — multiply all `_Spec` widths/depths by this before packing. Set to 0.82/1.0/1.20 by the options generator.

### Validation

`core/validation/validator.py` — shared by generation, regeneration, PATCH, and export routes. Returns `ValidationResult(valid, errors, warnings)`. Routes merge `result.warnings` into `project.warnings` (deduped by `.id`). **Any new endpoint that reads or generates a project must run the validator.**

### Storage layer

`ProjectStore` ABC (`core/storage/base.py`) — `user_id` threaded everywhere (`local-user` for now). `LocalProjectStore` at `core/storage/local_store.py`: atomic writes via temp-file + `os.replace`. `save_export_manifest(project_id, manifest)` appends to `exports/manifest.json`. Tests: `app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)`.

### AI providers

`core/ai/` — `AIProvider` ABC → `DeterministicProvider` / `AnthropicProvider` / `OpenAICompatibleProvider` / `HybridProvider`. SDKs lazy-imported so the server runs without them installed. `schema_repair.py` strips markdown fences, extracts JSON, validates with Pydantic + validator; on failure raises `ValueError` which `HybridProvider` catches and falls back to deterministic. Keys: `SCOTCH_ANTHROPIC_API_KEY` / `SCOTCH_OPENAI_API_KEY`. Mode: `SCOTCH_GENERATION_MODE` (deterministic/ai/hybrid).

### API routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/projects` | Create stored project |
| GET/PATCH/DELETE | `/projects/{id}` | Project CRUD (PATCH validates design + merges options) |
| POST | `/generate/from-prompt` | Single generation (deterministic/ai/hybrid) |
| POST | `/generate/options` | 3-variant options (always deterministic) |
| POST | `/generate/regenerate` | Apply parameter edits |
| POST | `/projects/{id}/exports/{format}` | Trigger export (json/svg/png/dxf) |
| GET | `/projects/{id}/exports` | List export manifests |
| GET | `/projects/{id}/exports/{filename}` | FileResponse download |
| GET | `/settings/generation` | Provider config booleans (keys never echoed) |

### Frontend structure

- `workspace.tsx` — owns all state: `project`, `storedId`, `prompt`, `generationMode`, `designOptions`, `showOptions`, `selectedOptionId`, `selectedRoomId`, `editBusy`, `notice`.
- `client.ts` — sole fetch layer. `apiRequest` helper wraps all calls.
- `FloorPlanSvg` — pure SVG renderer, `SCALE=12 px/ft`. `planPixelSize(project)` gives SVG dimensions.
- `OptionsPanel` — mini SVG plans via inline `<rect>` per room (no SCALE, uses viewBox).
- `MassingViewer` — R3F, always `next/dynamic` with `ssr: false`.

### Gotchas to avoid

- **PowerShell 5.1:** no `&&`; use `;` or `if ($?)`. Commit messages via `@'…'@` here-strings (closing `'@` at column 0).
- **CRLF warnings** on every commit: noise; ignore.
- **Preview screenshots** sometimes time out — use `preview_snapshot` for structure verification; use `preview_eval` for DOM queries.
- **Next.js HMR vs stale cache:** if changes aren't picked up, `preview_stop` + `preview_start` to get a fresh process. Clear `.next` if needed: `Remove-Item -Recurse -Force apps/web/.next`.
- **TypeScript curly-quote trap:** the Write/Edit tools sometimes insert Unicode `"..."` instead of ASCII `"..."` inside TypeScript string literals. Use single quotes for string values or verify with `npx tsc --noEmit`.
- **Backend restart:** the `api` preview server doesn't hot-reload on import-path changes (only source file changes). Always `preview_stop` + `preview_start` after adding new route modules.
- **`lru_cache` on `get_settings`:** cached per process; tests use `dependency_overrides`, not env mutation.
- **Route order matters:** `/projects/sample` must be registered before `/projects/{id}` in the router to avoid shadowing.

---

## Phase 11 — Software Export Adapters MVP

**Goal:** Improved DXF, runnable SketchUp Ruby script, Blender Python script, and strategy docs for Revit and Rhino. Accept: DXF improved; `.rb` and `.py` exporters generate runnable scripts; Revit/Rhino strategy docs complete.

### Stage 11.1 — DXF deepening

The existing `core/exports/dxf_exporter.py` (Phase 7) draws rooms as LWPOLYLINE rects and labels as TEXT. Deepen it:

- **Wall polylines:** use `ezdxf` LWPOLYLINE on layer `A-WALL` with the room boundary closed (5-point path: all 4 corners + back to start). Add a thin inner offset (poché effect: 0.5 ft) as a second LWPOLYLINE.
- **Door arcs:** for each `Door`, draw the swing arc on `A-DOOR`: use `msp.add_arc(center, radius, start_angle, end_angle)`. The swing radius equals the door width; center = door hinge point derived from `room.x/y + wall offset`.
- **Window lines:** two parallel lines on `A-WINDOW` representing the glazing unit, computed from `Window.wall + offset + width`.
- **Room labels:** use MTEXT (not TEXT) on `A-ROOM-TEXT` for multi-line labels: room name + area (`{name}\n{area:.0f} ft²`).
- **Dimension lines:** site width and depth as proper DXF DIMENSION entities (linear dimension) on `A-DIMS`; use `ezdxf`'s `dimstyle` mechanism.
- **Tests:** read back the DXF with `ezdxf.readfile()`, assert entity types/layers/counts.

### Stage 11.2 — SketchUp Ruby exporter

Create `core/exports/sketchup_exporter.py` that writes a `.rb` file (SketchUp Ruby script).

Structure of the generated `.rb`:

```ruby
# Generated by Scotch — {project.name}
# Run via: Extensions > Developer > Ruby Console > load 'path/to/file.rb'

model = Sketchup.active_model
entities = model.active_entities
model.start_operation('Scotch Import', true)

# Materials
wall_mat = model.materials.add('ScotchWall')
wall_mat.color = Sketchup::Color.new(248, 247, 245)
# ... floor, glass, roof

FLOOR_HEIGHT = {floor_height}  # feet

# Rooms as extruded boxes
# {for each room}
group = entities.add_group
room_ents = group.entities
pts = [ ... 4 base corners ... ]
face = room_ents.add_face(pts)
face.pushpull(-FLOOR_HEIGHT * 12)  # SketchUp uses inches
group.name = '{room.name}'

# Floor slab
# ... site footprint as flat face

model.commit_operation
```

Key notes:
- SketchUp uses **inches** internally — multiply all ft values by 12.
- Rooms as groups named after `room.name`.
- Doors/windows: add guide-line rectangles on the wall face (openings as cut placeholders — actual `opening?` method cuts are complex, mark them with a guide or a face with a distinct material).
- Write the file via `core/storage` path: `exports/{project_id}_sketchup.rb`; register in the manifest.
- Add `POST /projects/{id}/exports/sketchup` endpoint.
- Frontend: add a "SketchUp" download button in the export panel.
- Tests: parse the `.rb` as text; assert all room names appear, `pushpull` appears, `start_operation` appears.

### Stage 11.3 — Revit strategy doc

Revit integration is C#-based and requires a live Revit install to test. For this phase, produce:

1. `docs/integrations/revit-strategy.md` — detailed plan covering:
   - Add-in architecture (`.addin` manifest, `IExternalCommand`, `Application.DocumentOpened` hook).
   - JSON import flow: read Scotch project JSON, create `Level` elements, `Wall` by `Line` + `WallType`, `Floor` from site outline, `Room` bounded by walls, `FamilyInstance` placeholders for doors/windows.
   - Element mapping table: Scotch `Room.type` → Revit category (Living Room → `OST_Rooms`, Kitchen → `OST_Rooms`, etc.).
   - Sync strategy: project GUID stored as `SharedParameter` on the Revit model for future round-trip.
2. A skeleton C# project stub (a `.csproj` file and empty `ScotchImportCommand.cs`) committed to `integrations/revit/` so the architecture is concrete.

### Stage 11.4 — Blender Python exporter

Create `core/exports/blender_exporter.py` that writes a `.py` file (Blender Python script).

Structure of the generated script:

```python
# Generated by Scotch — {project.name}
# Run via: Blender > Scripting tab > Open > Run Script

import bpy, mathutils

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

def make_material(name, color_rgb, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color_rgb, 1.0)
    bsdf.inputs['Alpha'].default_value = alpha
    return mat

# Materials
wall_mat = make_material('Wall', (0.97, 0.96, 0.96))
# floor, roof, glass ...

SCALE = 0.3048  # 1 ft = 0.3048 m (Blender is metric)
FLOOR_H = {floor_height} * SCALE

# Rooms as mesh cubes (scaled boxes)
# {for each room}
bpy.ops.mesh.primitive_cube_add(...)
obj = bpy.context.active_object
obj.name = '{room.name}'
obj.dimensions = (room.width * SCALE, room.depth * SCALE, FLOOR_H)
obj.location = (...)

# Camera suggestions
bpy.ops.object.camera_add(location=(cx, cy, eye_z), rotation=(...))
```

Key notes:
- Use metric (multiply ft × 0.3048 for meters).
- Include 3 camera suggestions: top-down orthographic, exterior 3/4 view, street-level perspective.
- Add `POST /projects/{id}/exports/blender` endpoint.
- Frontend: "Blender" download button.
- Tests: parse `.py` text; assert `make_material`, room names, `SCALE` line.

### Stage 11.5 — Rhino strategy doc

Produce `docs/integrations/rhino-strategy.md` covering:
- Rhino Python (RhinoScriptSyntax via `rhinoscriptsyntax`) vs. Rhino.Inside approaches.
- Script structure: add mesh surfaces per room, extrude walls, add door/window openings as subtracted polysurfaces.
- Grasshopper parameter strategy: Scotch JSON → GH Data → Room geometry via gh components.
- File to commit: `integrations/rhino/scotch_import.py` skeleton (room surface + extrusion loop).

---

## Phase 12 — Presentation Sheet MVP

**Goal:** A full-bleed A1/A3 architectural sheet combining plan, title block, room schedule, notes, and legend — exportable as SVG and PDF. Accept: sheet exports with plan/title/schedule/notes; structured SVG layers.

### Stage 12.1 — Sheet data model

Add `SheetLayout` Pydantic model in `core/models/` (or a new `sheet.py`):

```python
class SheetLayout(BaseModel):
    title: str
    project_name: str
    drawn_by: str = "Scotch"
    date: str          # ISO date string
    scale_label: str   # e.g. "1:100"
    paper_size: Literal["A1", "A3"] = "A3"
    plan_viewport: dict  # x, y, width, height in mm on the sheet
    notes: list[str] = []
    concept_text: str = ""
    # Derived from project; included here for easy serialisation
    room_schedule: list[dict]  # [{name, width, depth, area}]
```

Add TypeScript mirror to `types.ts`.

### Stage 12.2 — SVG sheet exporter

`core/exports/sheet_svg_exporter.py`:

- A3 = 420 × 297 mm at 3.78 px/mm (≈ 1587 × 1122 px at 96dpi). A1 = 841 × 594 mm.
- Structure: one root `<svg>` with named groups `<g id="frame|title-block|plan|schedule|notes|legend|north-arrow">`.
- **Title block** (bottom strip, ~60mm tall): project name, drawn-by, date, scale, north arrow.
- **Plan viewport:** embed the architectural floor plan SVG (from Phase 7's SVG exporter, already layered) as a nested `<g>` scaled + translated into the plan viewport rect. Do not re-render; call `svg_exporter.generate_svg(project)` and embed its interior `<g>` groups.
- **Room schedule** (right column, ~60mm wide): table with room name, size, area. Simple `<rect>` + `<text>` grid.
- **Notes / concept text** (below plan or in a designated zone).
- **Legend:** room-type colour key matching the plan fills.
- Output: write to `exports/{project_id}_sheet.svg`; add to manifest.

### Stage 12.3 — PDF sheet export

`core/exports/sheet_pdf_exporter.py`:

- Use `reportlab` (already likely in the export requirements path; if not, add it). Or use `svglib` + `reportlab` to convert the sheet SVG to PDF.
- Preferred: `svglib.svg2rlg(sheet_svg_path)` → `reportlab.graphics.renderPDF.drawToFile(drawing, pdf_path)`.
- If `svglib` is unreliable, fall back to Pillow PNG rasterize → reportlab PDF (acceptable for MVP; note the limitation).
- Endpoint: `POST /projects/{id}/exports/sheet_svg` and `POST /projects/{id}/exports/sheet_pdf`.
- Frontend: "Sheet SVG" and "Sheet PDF" buttons in the export panel.

### Stage 12.4 — Illustrator-friendly layering

The sheet SVG produced in 12.2 must be Illustrator-importable:
- All layer groups use `id=` attributes (Illustrator reads `id` as layer names).
- No CSS `var()` references — all colors are hex or `rgb()` literals.
- Text uses system-safe fonts (`Arial`, `Georgia`) or embed the subset if feasible.
- Verify by opening in a browser (SVG renders cleanly) and checking `id` attributes in the output.

### Stage 12.5 — Photoshop/InDesign strategy doc

`docs/integrations/sheets-strategy.md`:
- Photoshop: export PNG assets (plan render at 300dpi, 2× Pillow PNG) + a PSD-compatible layered TIFF strategy.
- InDesign: place the sheet SVG as a linked object; Scotch exports the PDF as a print-ready asset.
- Board templates: reference workflow (Scotch → SVG/PDF → InDesign master page).
- Tests: sheet exporter file exists, `<g id="plan">` in SVG, PDF file non-empty.

---

## Phase 13 — Architecture Intelligence MVP

**Goal:** Automated spatial quality checks, area calculations, optional vastu suggestions, and room schedule export. Accept: warnings + area calcs + schedule export + optional vastu all working.

### Stage 13.1 — Spatial quality checks

Create `core/intelligence/spatial_checks.py`:

```python
def run_spatial_checks(project: ArchitectureProject) -> list[ProjectWarning]:
```

Checks to implement (each emits a `ProjectWarning` with a unique `id` like `intel-bath-access`, severity info/warning):

| Check | Condition | Message |
|---|---|---|
| Room too small | Any room area < 40 ft² | "{name} is very small ({area:.0f} ft²) — minimum recommended is 40 ft²." |
| Bath near bedroom | Attached bath not adjacent (y-overlap) to its bedroom | "Attached Bath is not adjacent to its bedroom — circulation may require a corridor." |
| Kitchen placement | Kitchen in the private zone (y > site_depth * 0.6) | "Kitchen is in the private zone — consider moving it to the service zone for better workflow." |
| Parking inside | Parking room fully inside the building mass (not on north edge) | "Parking appears to be inside the building — verify it has direct access from the street." |
| No entry room | No room with type `living`, `cafe_seating`, or `office` at `y ≈ 0` | "No entry room detected on the entrance edge — consider placing the living room at the front." |
| Unused site area | Total built area < site_area × 0.35 | "Only {pct:.0f}% of the site is built-up — there may be significant unused area." |
| Overlapping rooms | Any two rooms overlap (x/y rect intersection) | "Rooms {a} and {b} overlap — layout may have a geometry error." |

Integrate into the generate and regenerate pipelines: after validation, run `run_spatial_checks(project)`, dedup against existing warning IDs, extend `project.warnings`. The validator already checks geometry — spatial checks add programme-quality advice.

### Stage 13.2 — Area calculations

Create `core/intelligence/area_calc.py`:

```python
class AreaReport(BaseModel):
    site_area: float
    built_up_area: float
    room_areas: dict[str, float]   # room_id → area ft²
    carpet_area: float             # built_up × 0.85 (proxy — no structural walls yet)
    circulation_area: float        # site_area - built_up_area (open/corridor approx)
    floor_area_ratio: float        # built_up / site_area
```

Expose via a new `GET /projects/{id}/analysis` endpoint returning `AreaReport`. Also add to the `DataPanel` — a new "Analysis" section below Warnings showing the key figures (site area, built-up, FAR, carpet approx).

### Stage 13.3 — Optional vastu suggestions

Create `core/intelligence/vastu.py`:

```python
def vastu_suggestions(project: ArchitectureProject) -> list[ProjectWarning]:
```

Vastu rules to implement (severity `info`, id prefix `vastu-`):

| Rule | Condition | Suggestion |
|---|---|---|
| Kitchen in SE | Kitchen not in south-east quadrant (x > width/2, y > depth/2) | "Vastu: Kitchen is traditionally placed in the south-east — consider relocating." |
| Master bedroom SW | Master bedroom not in south-west quadrant | "Vastu: Master Bedroom is traditionally placed in the south-west." |
| Entrance north/east | Site orientation not north or east | "Vastu: North or east-facing entrances are considered most auspicious." |
| Bathroom NW/SE | Bathrooms not in north-west or south-east | "Vastu: Bathrooms are traditionally placed in the north-west or south-east." |
| Study NE | Study (if present) not in north-east quadrant | "Vastu: Study or prayer room in the north-east is considered auspicious." |

Vastu is **opt-in**: add `SCOTCH_VASTU_SUGGESTIONS=false` env flag (default off). When enabled, merge vastu warnings into the generate/regenerate pipeline after spatial checks. Frontend: toggle in the right panel (Warnings section — a checkbox "Show Vastu suggestions"). Wire via a new `POST /generate/from-prompt` field `vastu: bool = False` or a settings toggle.

### Stage 13.4 — Room schedule export

Add `GET /projects/{id}/schedule` endpoint returning:

```json
{
  "project_name": "2BHK Apartment Concept",
  "units": "feet",
  "rooms": [
    {"id": "living", "name": "Living Room", "type": "living", "width": 14, "depth": 12, "area": 168, "level": 0}
  ],
  "totals": {"rooms": 7, "built_up_area": 1050, "carpet_area": 892}
}
```

Also `GET /projects/{id}/schedule.csv` → CSV download (use Python `csv` module; no extra deps).

Frontend: "Schedule CSV" button in the exports panel; schedule table in the DataPanel already shows room data — add a "Download as CSV" link below it.

### Stage 13.5 — Intelligence panel UI

Redesign the right-panel "Warnings" section into a tabbed "Analysis" section:

Tabs: **Checks** (spatial quality warnings, grouped by severity) | **Areas** (AreaReport figures with a mini bar chart or text breakdown) | **Schedule** (the room table with a CSV download link).

The Warnings section currently lives in `data-panel.tsx`. Wrap it in a tab group using the existing shadcn `Tabs` component (already used elsewhere). Keep the existing warnings rendering, add Area display, and the download link.

---

## Phase 14 — Revit Plugin MVP

**Goal:** A working C# Revit add-in that imports a Scotch project JSON and creates basic Revit elements. Accept: PoC add-in imports Scotch JSON, creates basic elements; mapping documented. Note: live testing requires Revit 2024+ installed.

### Stage 14.1 — C# add-in project setup

Create `integrations/revit/ScotchRevitAddin/` with:

- `ScotchRevitAddin.csproj` — targets `net48` (Revit 2024 runs on .NET Framework 4.8); references `RevitAPI.dll` and `RevitAPIUI.dll` (document their expected path in a comment; not included in repo).
- `ScotchRevitAddin.addin` — the manifest file Revit reads from `%APPDATA%\Autodesk\Revit\Addins\2024\`.
- `ScotchImportCommand.cs` — `IExternalCommand` skeleton with `Execute()` method.
- `README.md` in the folder — how to build, where to put the `.addin` file, and how to test.
- No actual Revit APIs are called in the skeleton — just the structure and imports. The remaining stages add the logic.

### Stage 14.2 — JSON import

In `ScotchImportCommand.cs`:

```csharp
public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
{
    // 1. Open file dialog → select project.json
    var dialog = new OpenFileDialog { Filter = "Scotch JSON|*.json" };
    if (dialog.ShowDialog() != DialogResult.OK) return Result.Cancelled;

    // 2. Deserialize (use System.Text.Json or Newtonsoft.Json)
    var json = File.ReadAllText(dialog.FileName);
    var project = JsonSerializer.Deserialize<ScotchProject>(json);

    // 3. Call import logic
    ImportProject(commandData.Application.ActiveUIDocument.Document, project);
    return Result.Succeeded;
}
```

Add `ScotchProject.cs` — C# POCO mirrors of the key Scotch JSON fields (id, name, units, site, building, rooms with id/name/type/x/y/width/depth/level). Only deserialize what Revit needs; omit walls/doors/windows for now (they come from room geometry).

### Stage 14.3 — Element creation

`RevitImporter.cs` — `ImportProject(Document doc, ScotchProject project)`:

```csharp
using (Transaction t = new Transaction(doc, "Scotch Import")) {
    t.Start();

    // 1. Level: create one Level per project.levels entry
    Level groundLevel = Level.Create(doc, 0.0);
    groundLevel.Name = "Ground Floor (Scotch)";

    // 2. Rooms: Revit rooms need bounded walls first, or use 
    //    Room.Create directly with a UV point (places unenclosed room tag).
    //    MVP: place Room elements at room centroids.
    foreach (var room in project.rooms) {
        double cx = FtToRevit(room.x + room.width / 2);
        double cy = FtToRevit(room.y + room.depth / 2);
        var pt = new UV(cx, cy);
        Room revitRoom = doc.Create.NewRoom(groundLevel, pt);
        revitRoom.Name = room.name;
    }

    // 3. Walls: for each room, create 4 wall segments from room boundaries.
    //    Use Wall.Create(doc, line, wallTypeId, levelId, height, 0, false, false).
    foreach (var room in project.rooms) {
        double h = FtToRevit(project.building.floor_height);
        // ... create 4 Line objects for room boundary walls
    }

    // 4. Floor slab: site outline as Floor using Floor.Create.

    t.Commit();
}
```

Conversion: Revit uses **decimal feet** internally (not inches like SketchUp). `FtToRevit(x)` = `x` (already feet). Levels use elevation in feet.

### Stage 14.4 — Mapping documentation

`docs/integrations/revit-mapping.md`:

| Scotch field | Revit element | Revit API call | Notes |
|---|---|---|---|
| `Room` | `Room` | `Document.Create.NewRoom(level, UV)` | Placed at room centroid; bounded by walls |
| `Room` boundary | `Wall` | `Wall.Create(doc, line, wallTypeId, levelId, height, 0, false, false)` | 4 walls per room |
| `Site` outline | `Floor` | `Floor.Create(doc, curveLoop, floorTypeId, levelId)` | Ground slab |
| `Building.floor_height` | Level elevation | `Level.Create(doc, elevation)` | One per floor |
| `Door` | `FamilyInstance` | `doc.Create.NewFamilyInstance(face, doorType, host, level, StructuralType.NonStructural)` | Requires door family loaded |
| `Window` | `FamilyInstance` | Same pattern | Requires window family |
| `project.id` | `SharedParameter` | Custom shared param on `ProjectInformation` | For future round-trip |

### Stage 14.5 — Roundtrip strategy

`docs/integrations/revit-roundtrip.md`:

- **Scotch → Revit:** Scotch project JSON → C# add-in → Revit model. Documented in 14.3.
- **Revit → Scotch (future):** read Revit `Room` elements (using `FilteredElementCollector`), export bounding box as Scotch `Room`, write JSON. The `ScotchProjectId` shared parameter identifies the source project.
- **Sync conflicts:** if the Revit model is edited and re-exported to Scotch, the `project.id` is preserved; the Scotch backend can PATCH the stored project. Rooms added in Revit get new IDs; rooms deleted in Revit are removed.
- **Limitations of this phase:** no door/window family loading (they need the correct Revit family files present); no floor type lookup (uses first available floor type); no MEP/structure elements.

---

## Execution order for phases 11–14

```
Phase 11:
  11.1 DXF deepening (improve existing exporter + tests) → commit
  11.2 SketchUp .rb exporter + endpoint + frontend button → commit
  11.3 Revit strategy doc + C# skeleton → commit
  11.4 Blender .py exporter + endpoint + frontend button → commit
  11.5 Rhino strategy doc + skeleton → commit + PushNotification

Phase 12:
  12.1 SheetLayout model (Pydantic + TS) → commit
  12.2 SVG sheet exporter (embed plan SVG, title block, schedule, notes) → commit
  12.3 PDF sheet exporter (svglib/reportlab or Pillow fallback) → commit
  12.4 Illustrator-friendly layering verification + fixes → commit
  12.5 Photoshop/InDesign strategy doc → commit + PushNotification

Phase 13:
  13.1 Spatial quality checks + integrate into generate/regenerate pipelines → commit
  13.2 Area calculations + /analysis endpoint + DataPanel display → commit
  13.3 Vastu suggestions (opt-in, env flag + frontend toggle) → commit
  13.4 Room schedule export (JSON + CSV endpoints + frontend button) → commit
  13.5 Intelligence panel UI (tabbed Checks/Areas/Schedule in DataPanel) → commit + PushNotification

Phase 14:
  14.1 C# add-in project structure + addin manifest → commit
  14.2 JSON import + ScotchProject C# model → commit
  14.3 Element creation (rooms, walls, floor slab) → commit
  14.4 Mapping documentation → commit
  14.5 Roundtrip strategy doc → commit + PushNotification
```

**Notes on Phase 14:** The C# project won't be buildable in CI without Revit SDK DLLs — commit the project file with an explanatory note that `RevitAPI.dll` and `RevitAPIUI.dll` must be copied from a Revit 2024 install. The phase is complete when the code is correct and the docs are thorough, even if a live round-trip test isn't possible without Revit installed.

After Phase 14, the product covers the full export and intelligence surface. Next phases (15 SketchUp plugin, 16 Rhino, 17 Rendering, 18 Cloud, 19 Versioning, 20 QA) follow the same pattern — read the roadmap for their stage breakdowns.
