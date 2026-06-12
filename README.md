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

Interactive API docs (FastAPI): http://localhost:8000/docs

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

**Phases 1–2 COMPLETE** — local skeleton (backend + frontend + health), and the CADAM-like UI shell: design system, dashboard with templates, three-panel workspace, mock ArchitectureProject, and the architectural SVG floor plan renderer.

**Next: Phase 3 — Universal Architecture Data Model MVP** (backend Pydantic models, reusable validation, sample-project factory + API, frontend switches from mock to backend data). See the [roadmap](docs/product/roadmap.md).
