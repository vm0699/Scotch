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

**Phase 1 — Local Working Skeleton MVP: COMPLETE.**
Backend and frontend run locally, `/health` works, the UI reflects live backend status, and landing → dashboard → workspace navigation is in place.

**Next: Phase 2 — CADAM-Like UI Shell MVP** (design system, dashboard UI, three-panel workspace, mock project, SVG floor plan renderer). See the [roadmap](docs/product/roadmap.md).
