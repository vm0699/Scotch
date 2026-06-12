# Scotch

**AI-native architecture design platform — text-to-design for architecture.**

Scotch lets architects, architecture students, interior designers, and small studios type natural-language prompts and generate **editable architectural designs**: a validated universal architecture model, architectural-standard 2D floor plans, 3D massing, CADAM-style editable parameters (panel + on-canvas), and exports into professional workflows (AutoCAD via DXF, SketchUp, Revit, Rhino, Blender, render engines, Adobe suite).

```
prompt → requirement parser → ArchitectureProject JSON → validator
       → editable parameters → 2D SVG floor plan → 3D massing
       → export adapters → software integrations
```

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router) · React · TypeScript · Tailwind CSS v4 · shadcn/ui · SVG 2D · React Three Fiber 3D (Phase 8) |
| Backend | Python · FastAPI · Pydantic v2 · local filesystem storage |
| AI | Provider abstraction: deterministic rule-based (no key needed) / Anthropic / OpenAI-compatible (Phase 9) |

## Repository Structure

```
RARCH/
  docs/                       # product brief, PRD, roadmap (live status), questionnaire
  apps/web/                   # Next.js frontend
    src/app/                  #   routes: / (landing), /dashboard, /workspace
    src/components/           #   layout components (TopBar, status) + shadcn ui/
    src/features/api/         #   typed backend client + status hook
  services/api/               # FastAPI backend
    app/main.py               #   app factory (CORS, routers)
    app/config.py             #   pydantic-settings (SCOTCH_* env vars)
    app/api/routes/           #   endpoints (health; projects/generate arrive in Phases 3–5)
    app/core/                 #   models, validation, generation (arrive in Phases 3–5)
    app/data/                 #   local project storage (gitignored)
    tests/                    #   pytest suite
```

## Setup

Prerequisites: Node 18+ (tested on 22), Python 3.10+ (tested on 3.13), npm.

```powershell
# Frontend dependencies
cd apps/web
npm install

# Backend environment
cd services/api
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# Environment variables (optional — defaults work locally)
copy .env.example .env
```

## Running

From the repo root, in two terminals:

```powershell
npm run dev:api    # FastAPI on http://localhost:8000
npm run dev:web    # Next.js on http://localhost:3000
```

Or directly:

```powershell
cd services/api; .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
cd apps/web; npm run dev
```

Open http://localhost:3000 — the top bar on the dashboard/workspace shows a live backend status indicator (green = online, red = offline).

## Interface (Phase 2)

- **Dashboard** (`/dashboard`) — product home: six starter templates (2BHK Apartment, 3BHK Villa, Studio, Small Cafe, Office, Duplex) with schematic thumbnails and prompt payloads, sample recent-project cards, and a Local-engine status card.
- **Workspace** (`/workspace`) — CADAM-style three-panel editor:
  - *Design Brief*: prompt textarea (Ctrl+Enter), template selector that fills the prompt, deterministic/AI mode control, Generate button.
  - *Preview*: 2D Plan / 3D Massing tabs over a drafting dot-grid canvas with zoom in/out/fit controls.
  - *Design Data*: parameters, room schedule with built-up total, export buttons (enabled in Phase 7), warnings + assumptions.
- **Floor plan renderer** ([floor-plan-svg.tsx](apps/web/src/features/plan/floor-plan-svg.tsx)) — architectural SVG: dashed site boundary, poché walls, door swing arcs, window symbols, room labels with sizes/areas, dimension lines with slash ticks, orientation-aware north arrow.

### Mock project (until Phases 3–5)

The workspace currently renders a centralized sample — a typed `ArchitectureProject` ([types.ts](apps/web/src/features/project/types.ts), [mock-architecture-project.ts](apps/web/src/features/project/mock-architecture-project.ts)): a 2BHK on a 30×50 ft east-facing site with 8 positioned rooms, doors, windows, parameters, notes, and warnings. Field names are snake_case to mirror the backend Pydantic JSON one-to-one, so the Phase 3 backend swap is a data-source change, not a refactor. Pressing **Generate** (or opening a project card) loads this sample.

### Current limitations

- Generation is mocked — the prompt isn't parsed yet (Phase 5).
- Projects don't persist; dashboard project cards are samples (Phase 4).
- Parameters are read-only (editing + on-canvas editing in Phase 6); exports disabled (Phase 7); 3D tab is a placeholder (Phase 8).

## API

| Endpoint | Description |
|---|---|
| `GET /health` | `{"app":"scotch","status":"ok","version":"0.1.0"}` |
| `GET /projects/sample` | Canonical validated 2BHK `ArchitectureProject` (validator advisories merged into `warnings`) |
| `POST /projects` | Create a project `{name, prompt?}` → `StoredProject` envelope |
| `GET /projects` | List project summaries (id, name, prompt, timestamps, room count, site label) |
| `GET /projects/{id}` | Load a stored project |
| `PATCH /projects/{id}` | Update name/prompt/design data (design is validated; 422 with errors if invalid) |
| `DELETE /projects/{id}` | Delete the project and its exports |
| `POST /generate/from-prompt` | `{prompt}` → `{project, summary, warnings}` — deterministic prompt-to-floorplan, no AI key needed |
| `POST /generate/regenerate` | `{project, changes}` → `{project, summary, warnings}` — applies parameter/room edits, re-packs the layout, revalidates (422 on out-of-range) |

Interactive API docs (FastAPI): http://localhost:8000/docs

## ArchitectureProject JSON (the universal model)

Defined in [services/api/app/core/models/project.py](services/api/app/core/models/project.py) (Pydantic v2), mirrored one-to-one by [apps/web/src/features/project/types.ts](apps/web/src/features/project/types.ts). Every feature — generation, editing, previews, exports, plugins — reads and writes this shape:

```jsonc
{
  "id": "sample-2bhk-east",
  "name": "2BHK Apartment Concept",
  "units": "feet",                                   // "feet" | "meters"
  "site": { "width": 30, "depth": 50, "orientation": "east" },
  "building": { "type": "residential", "style": "modern minimal", "floors": 1, "floor_height": 10 },
  "levels": [{ "index": 0, "name": "Ground Floor", "elevation": 0 }],
  "rooms": [                                          // x/y = top-left on plan; y=0 at entrance edge
    { "id": "living", "name": "Living Room", "type": "living", "x": 10, "y": 0, "width": 14, "depth": 12, "level": 0 }
  ],
  "walls": [],                                        // explicit segments (rooms imply walls until Phase 5+)
  "doors": [                                          // wall is plan-local: north=top/entrance, south, east, west
    { "id": "door-main", "room_id": "living", "wall": "north", "offset": 5, "width": 3.5 }
  ],
  "windows": [{ "id": "win-living", "room_id": "living", "wall": "north", "offset": 9.5, "width": 4 }],
  "materials": [],
  "parameters": [
    { "key": "site_width", "label": "Site width", "value": 30, "unit": "ft", "category": "site", "editable": true }
  ],
  "notes": ["Entrance assumed on the east edge per site orientation."],
  "warnings": [{ "id": "warn-open-area", "severity": "info", "message": "…" }]
}
```

Validation ([services/api/app/core/validation/validator.py](services/api/app/core/validation/validator.py)) enforces unique room ids, rooms inside the site, level references, and opening references/fit — and emits advisory warnings (overlaps, oversized openings, large unbuilt area). Schema constraints (positive dimensions, enum fields) live on the models themselves.

## Project Storage (local-first, cloud-ready)

Projects persist as JSON under the backend:

```
services/api/app/data/users/local-user/projects/{project_id}/project.json
services/api/app/data/users/local-user/projects/{project_id}/exports/      # Phase 7
```

Each `project.json` is a `StoredProject` envelope: `{id, name, prompt, created_at, updated_at, project}` where `project` is the ArchitectureProject (or `null` before first generation). Writes are atomic (temp file + rename).

**Cloud open door:** all access goes through the `ProjectStore` interface ([base.py](services/api/app/core/storage/base.py)) with an explicit `user_id` on every call (today always `local-user`). The backend is chosen by `SCOTCH_STORAGE_BACKEND` via [factory.py](services/api/app/core/storage/factory.py) — a cloud implementation (S3/Supabase/database, Phase 18) is a new class and a settings change; no API or frontend restructuring.

## Deterministic Generation (Phase 5)

Prompt → plan with **no AI key**, in three steps under `services/api/app/core/architecture/`:

1. **[requirement_parser.py](services/api/app/core/architecture/requirement_parser.py)** — regex/keyword extraction of site size, orientation, building kind (apartment / villa / studio / duplex / cafe / office), bedrooms, bathrooms, floors, style, and parking/balcony/dining/study/storage flags. Missing values get smart defaults (30×50 ft, east-facing, 2BHK…) and every default is recorded as an assumption.
2. **[defaults.py](services/api/app/core/architecture/defaults.py)** — the locked room-size library (living 14×12, kitchen 8×10, master 12×13, bath 5×8…).
3. **[floorplan_generator.py](services/api/app/core/architecture/floorplan_generator.py)** — zoned band packing along the site depth: public entrance band (parking, living/seating, balcony), service band (kitchen, dining, common bath, study, storage), private bands (bedrooms with interleaved attached baths). Rooms wrap to new bands when site width runs out; oversized rooms are clamped and deep programs compressed — always with a visible warning. Doors (entrance centered on the entry room) and perimeter windows are derived from the placed geometry. Cafe gets its own program; office prompts fall back to a generic open plan with an info warning until office logic lands.

Assumptions surface as info warnings in the UI; the result is validated before it leaves the API and saved to the open project.

## Testing

```powershell
npm run test:api     # backend pytest suite
npm run build:web    # frontend type-check + production build
npm run lint:web     # frontend lint
```

## Documentation

- [docs/README.md](docs/README.md) — documentation index
- [docs/product/roadmap.md](docs/product/roadmap.md) — Phases 0–20 staged roadmap with live status
- [docs/product/prd.md](docs/product/prd.md) — product requirements
- [docs/product/brief.md](docs/product/brief.md) — product brief and vision

## Current Phase Status

**Phases 1–6 COMPLETE** — local skeleton, CADAM-like UI shell, universal data model, cloud-ready storage, prompt-to-floorplan generation with no AI key, and **CADAM-style editing**: click any room (on the plan or in the schedule) to edit it via an inline popover or the panel; site/building parameters editable with bounds; every edit re-packs the layout, revalidates, updates the preview, and persists (72 backend tests).

**Next: Phase 7 — Export MVP** (JSON, layered SVG, PNG, and DXF exports with a tracked manifest). See the [roadmap](docs/product/roadmap.md).
