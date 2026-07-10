# Scotch

**AI-native architecture design platform — text-to-design for architecture.**

Scotch lets architects, students, and small studios type natural-language prompts and get **editable architectural designs**: a validated universal data model, architectural-standard 2D floor plans, 3D massing, CADAM-style editable parameters (panel + on-canvas), professional exports, software integrations, and full version history.

```
prompt → requirement parser → ArchitectureProject JSON → validator
       → editable parameters → 2D SVG floor plan → 3D massing (R3F)
       → export adapters → software integrations / plugins
```

**Status: v1.0-beta — all 20 phases complete.**

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · shadcn/ui · Sonner toasts |
| 2D | SVG floor plan renderer (walls, door swings, window symbols, dimensions, north arrow) |
| 3D | React Three Fiber · Three.js · OrbitControls · GLTF export |
| Backend | Python · FastAPI · Pydantic v2 · local filesystem storage |
| AI | Provider abstraction: deterministic rule-based (no key) / Anthropic / OpenAI-compatible |
| Plugins | SketchUp `.rbz` extension · Revit C# add-in · RhinoPython · Blender Python |

---

## Repository Structure

```
RARCH/
  CLAUDE.md                        # Claude Code instructions
  README.md                        # this file
  .env.example                     # env var template
  docs/
    product/                       # brief, PRD, roadmap (live), QA checklist, demo script
    architecture/                  # auth, database, cloud, API readiness strategies
    integrations/                  # SketchUp, Revit, Rhino, Blender, rendering, sheets
  apps/web/                        # Next.js frontend
    src/app/                       #   routes: / (landing), /dashboard, /workspace
    src/components/                #   design-system + workspace panels
    src/features/                  #   api client, project types, 2D plan, 3D massing
  services/api/                    # FastAPI backend
    app/main.py                    #   app factory (CORS, all routers)
    app/config.py                  #   pydantic-settings (SCOTCH_* env vars)
    app/api/routes/                #   endpoints (health, projects, generate, exports,
                                   #             intelligence, cameras, integrations,
                                   #             settings, versions)
    app/core/                      #   models, validation, architecture, ai, storage, exports
    app/data/                      #   local project storage (gitignored)
    tests/                         #   384 pytest cases
  integrations/
    sketchup/                      # installable .rbz extension
    rhino/                         # facade prototype
  plugins/
    revit/                         # C# add-in (ScotchRevit)
```

---

## Setup

**Prerequisites:** Node 18+ (tested on 22), Python 3.10+ (tested on 3.13), npm.

```powershell
# Frontend
cd apps/web
npm install

# Backend
cd services/api
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# Environment variables (optional — defaults work for local mode)
copy .env.example .env
# Edit .env to add ANTHROPIC_API_KEY for AI generation mode
```

---

## Running

```powershell
# Two terminals from the repo root:
npm run dev:api   # FastAPI on http://localhost:8000
npm run dev:web   # Next.js on http://localhost:3000
```

Or directly:

```powershell
cd services/api; .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
cd apps/web; npm run dev
```

Open **http://localhost:3000**.

---

## Interface

### Dashboard (`/dashboard`)
- Six starter templates: 2BHK Apartment, 3BHK Villa, Studio, Small Cafe, Office, Duplex.
- New Project dialog; recent projects with live listing, delete with confirm.
- Backend status card (green = API online).

### Workspace (`/workspace?project={id}`)

**Left — Design Brief:**
- Prompt textarea (Ctrl+Enter submits).
- Template selector that pre-fills the prompt.
- Generation mode: Deterministic (no API key) / AI / Hybrid.
- Generate button + "compare compact · balanced · spacious options" link.
- Status notice banner for generation summaries.

**Centre — Preview:**
- **2D Plan tab** — architectural SVG: dashed site boundary, poché walls, door swing arcs, window symbols, room labels with area, dimension lines, north arrow. Click a room to select and open an inline CADAM-style edit popover. Zoom in/out/fit controls.
- **3D Massing tab** — React Three Fiber viewer: walls extruded to floor height, roof slab, ground, door glass insets; OrbitControls; camera preset dropdown (exterior quarter, top ortho, street eye, interior, balcony); GLTF export.

**Right — Design Data:**
- **Selection** — room editor inline (name, width, depth) when a room is selected.
- **Parameters** — site/building/room parameter table, all editable.
- **Room Schedule** — all rooms with size, area, built-up total; click row to select on plan.
- **Intelligence** — area summary, spatial quality checks, optional Vastu Shastra analysis.
- **History** — reverse-chronological version list with colour-coded change-type badge, mini SVG thumbnail, room count/area, restore button (two-step confirm).
- **Exports** — all formats (see below).
- **Warnings** — design validation advisories and assumptions.

---

## Exports

| Format | Description |
|--------|-------------|
| **JSON** | Full `ArchitectureProject` — the universal data model |
| **SVG** | Layered floor plan (site/rooms/walls/doors/windows/labels/dims) — Illustrator-compatible |
| **PNG** | Rasterized plan at 2× scale (Pillow) |
| **DXF** | AutoCAD-ready: layers A-SITE/A-WALL/A-DOOR/A-WINDOW/A-ROOM-TEXT/A-HATCH/A-ANNO/A-DIMS |
| **SketchUp (.rb)** | Ruby script: hollow rooms, materials by type, door/window voids, roof slab, camera |
| **Blender (.py)** | Python script: BooleanDifference rooms, Principled BSDF, lights, 5 cameras, EEVEE/Cycles |
| **Rhino (.py)** | RhinoPython: unit detection, layer setup, BooleanDifference walls/openings, roof |
| **Sheet SVG** | A3 presentation board: title block, plan viewport, room schedule, legend, notes |
| **Sheet PDF** | A3 print-ready board (reportlab) |
| **Schedule JSON** | Room schedule with gross + carpet areas |
| **Schedule CSV** | Room schedule for Excel / Google Sheets |
| **GLTF** | 3D massing direct from the viewer (Three.js GLTFExporter) |

---

## API Reference

Interactive docs at **http://localhost:8000/docs** (Swagger).

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `{"app":"scotch","status":"ok","version":"..."}` |

### Projects

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects` | Create project `{name, prompt?}` → `StoredProject` |
| GET | `/projects` | List project summaries (id, name, prompt, timestamps, room_count, site_label) |
| GET | `/projects/sample` | Validated 2BHK sample `ArchitectureProject` |
| GET | `/projects/{id}` | Load stored project |
| PATCH | `/projects/{id}` | Update name/prompt/project/options/change_type/version_summary |
| DELETE | `/projects/{id}` | Delete project + exports |

### Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate/from-prompt` | `{prompt, mode?}` → `{project, summary, warnings}` |
| POST | `/generate/options` | `{prompt, mode?}` → `{options: DesignOption[]}` (compact/balanced/spacious) |
| POST | `/generate/regenerate` | `{project, changes}` → `{project, summary, warnings}` |

### Exports

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/exports/{format}` | Trigger export → `ExportManifest` |
| GET | `/projects/{id}/exports` | List export manifests |
| GET | `/projects/{id}/exports/{filename}` | Download export file |

Supported formats: `json`, `svg`, `png`, `dxf`, `sketchup`, `blender`, `rhino`, `sheet_svg`, `sheet_pdf`, `schedule_json`, `schedule_csv`.

### Intelligence

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{id}/intelligence?vastu=false` | Area summary + spatial checks + optional Vastu analysis |
| GET | `/projects/{id}/cameras` | Derived camera presets (5 viewpoints) |

### Version History

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{id}/versions` | List versions (reverse-chronological) `→ ProjectVersionMeta[]` |
| GET | `/projects/{id}/versions/{vid}` | Full version with snapshot `→ ProjectVersion` |
| POST | `/projects/{id}/versions/{vid}/restore` | Restore snapshot as active (append-only) `→ StoredProject` |
| GET | `/projects/{id}/versions/{a}/diff/{b}` | Structural diff (added/removed/resized rooms) `→ VersionDiff` |

### Integrations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/integrations/sketchup/extension` | Download `.rbz` extension package |
| GET | `/integrations/sketchup/extension/files` | Extension file manifest |

### Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings/generation` | Mode, provider, key-configured status |

---

## ArchitectureProject JSON (the universal model)

Defined in [`services/api/app/core/models/project.py`](services/api/app/core/models/project.py) (Pydantic v2), mirrored 1:1 by [`apps/web/src/features/project/types.ts`](apps/web/src/features/project/types.ts). Every feature reads/writes this shape:

```jsonc
{
  "id": "proj-abc123",
  "name": "2BHK Client Brief",
  "units": "feet",                    // "feet" | "meters"
  "site": { "width": 30, "depth": 50, "orientation": "east" },
  "building": { "type": "residential", "style": "modern", "floors": 1, "floor_height": 10 },
  "levels": [{ "index": 0, "name": "Ground Floor", "elevation": 0 }],
  "rooms": [
    { "id": "living", "name": "Living Room", "type": "living",
      "x": 10, "y": 0, "width": 14, "depth": 12, "level": 0 }
  ],
  "walls": [],             // explicit wall segments (rooms imply walls)
  "doors": [{ "id": "d-main", "room_id": "living", "wall": "north", "offset": 5, "width": 3.5 }],
  "windows": [{ "id": "w-liv", "room_id": "living", "wall": "east", "offset": 2, "width": 4 }],
  "materials": [{ "id": "m-wall", "name": "Plaster", "target": "wall",
                  "base_color": "#F5F4F2", "roughness": 0.85, "metallic": 0.0 }],
  "parameters": [
    { "key": "site_width", "label": "Site width", "value": 30, "unit": "ft",
      "category": "site", "editable": true, "min": 10, "max": 200 }
  ],
  "notes": ["Entrance assumed on the east edge per site orientation."],
  "warnings": [{ "id": "warn-open-area", "severity": "info", "message": "…" }]
}
```

---

## Storage

**Local-first:**
```
services/api/app/data/users/local-user/projects/{project_id}/
  project.json           # StoredProject envelope
  exports/               # export files + manifest.json
  versions/              # {version_id}.json sidecars (Phase 19)
```

**Cloud-ready:** all access goes through `ProjectStore` ABC with an explicit `user_id`. Set `SCOTCH_STORAGE_BACKEND=cloud` to swap backends; `CloudProjectStore` is a stub for the cloud implementation (Phase 18+).

---

## Deterministic Generation

Prompt → plan with **no AI key**, in three steps under `services/api/app/core/architecture/`:

1. **Requirement parser** — extracts site size, orientation, building kind, bedrooms, baths, floors, style, parking, balcony, dining, study, storage. Missing values get smart defaults (30×50 ft, east-facing) logged as assumption warnings.
2. **Defaults library** — locked room-size table: living 14×12, kitchen 8×10, master 12×13, bath 5×8, balcony 6×10, parking 10×15, etc.
3. **Layout generator** — zoned band packing: public band (parking, living, balcony) · service band (kitchen, dining, baths) · private bands (bedrooms). Rooms wrap on site width; oversized rooms are clamped with warnings. Doors and perimeter windows derived from placed geometry.

---

## Software Integrations

| Tool | Integration | Guide |
|------|-------------|-------|
| **SketchUp** | One-shot `.rb` export + installable `.rbz` extension with JSON import | [`docs/integrations/sketchup-workflow.md`](docs/integrations/sketchup-workflow.md) |
| **Rhino 7+** | RhinoPython export + Grasshopper parameter strategy | [`docs/integrations/rhino-grasshopper-strategy.md`](docs/integrations/rhino-grasshopper-strategy.md) |
| **Revit 2024** | C# add-in (Levels→Walls→Floors→Rooms→Doors→Windows) + round-trip sync | [`docs/integrations/revit-mapping.md`](docs/integrations/revit-mapping.md) |
| **Blender** | Python script: full scene automation, lights, cameras, EEVEE/Cycles | [`docs/integrations/rendering-workflows.md`](docs/integrations/rendering-workflows.md) |
| **Lumion / D5 / Enscape** | Via SketchUp or GLTF + material reassignment guide | [`docs/integrations/rendering-workflows.md`](docs/integrations/rendering-workflows.md) |
| **AutoCAD** | DXF with named layers, hatches, dimension strings | export panel |
| **Illustrator / InDesign** | A3 sheet SVG with named layers; Sheet PDF | export panel |

---

## Testing

```powershell
npm run test:api     # 384 backend pytest cases
npm run build:web    # TypeScript type-check + production build
npm run lint:web     # ESLint
```

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| [`docs/product/roadmap.md`](docs/product/roadmap.md) | Phases 0–20 with stage-level status (live tracker) |
| [`docs/product/prd.md`](docs/product/prd.md) | Product Requirement Document |
| [`docs/product/brief.md`](docs/product/brief.md) | Product brief and vision |
| [`docs/product/qa-checklist.md`](docs/product/qa-checklist.md) | Full QA flow checklist |
| [`docs/product/demo-script.md`](docs/product/demo-script.md) | 8-minute live demo script |
| [`docs/product/version-compare-strategy.md`](docs/product/version-compare-strategy.md) | Version diff model and future compare UI |
| [`docs/architecture/auth-strategy.md`](docs/architecture/auth-strategy.md) | OAuth / JWT cloud auth plan |
| [`docs/architecture/database-strategy.md`](docs/architecture/database-strategy.md) | Postgres / Mongo trade-off, schema |
| [`docs/architecture/cloud-storage-strategy.md`](docs/architecture/cloud-storage-strategy.md) | S3 / Supabase layout |
| [`docs/architecture/cloud-api-readiness.md`](docs/architecture/cloud-api-readiness.md) | Route audit, pagination, ownership |
| [`docs/integrations/sketchup-workflow.md`](docs/integrations/sketchup-workflow.md) | SketchUp install + use guide |
| [`docs/integrations/revit-mapping.md`](docs/integrations/revit-mapping.md) | Revit add-in field mapping |
| [`docs/integrations/revit-addin-strategy.md`](docs/integrations/revit-addin-strategy.md) | Revit add-in architecture |
| [`docs/integrations/rhino-grasshopper-strategy.md`](docs/integrations/rhino-grasshopper-strategy.md) | Rhino + GH parameter strategy |
| [`docs/integrations/rendering-workflows.md`](docs/integrations/rendering-workflows.md) | Blender, Lumion, D5, Enscape, V-Ray |
| [`docs/integrations/presentation-sheets-strategy.md`](docs/integrations/presentation-sheets-strategy.md) | Illustrator / InDesign workflow |

---

## Known Limitations (v1.0-beta)

- **Office program:** uses a generic open-plan fallback (full office generator is post-beta).
- **Room ID stability:** full regeneration creates new room IDs — history diffs will show all rooms as added+removed. Semantic matching is planned for v1.1.
- **Cloud backend:** `CloudProjectStore` is a stub (raises `NotImplementedError`). Everything runs local-only. Cloud deployment is Phase 18+ work.
- **Plugin live testing:** requires the host application (SketchUp, Rhino, Revit, Blender) installed locally. Code and docs are delivered; live install is a manual step.
- **No session auth:** all data belongs to `local-user`. Multi-user is a cloud feature.
- **Version history pagination:** no limit on version list; acceptable for typical project sizes.
