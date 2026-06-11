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
| Frontend | Next.js (App Router) · React · TypeScript · Tailwind CSS · shadcn/ui · SVG 2D · React Three Fiber 3D |
| Backend | Python · FastAPI · Pydantic v2 · local filesystem storage |
| AI | Provider abstraction: deterministic rule-based (no key needed) / Anthropic / OpenAI-compatible |

## Repository Structure

```
RARCH/
  docs/             # product brief, PRD, roadmap (live status), questionnaire
  apps/web/         # Next.js frontend
  services/api/     # FastAPI backend
```

## Setup

Prerequisites: Node 18+ (tested on 22), Python 3.10+ (tested on 3.13), npm.

```powershell
# 1. Frontend dependencies (installed by create-next-app; if cloning fresh:)
cd apps/web
npm install

# 2. Backend environment
cd services/api
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# 3. Environment variables (optional for now)
copy .env.example .env
```

## Running

From the repo root:

```powershell
npm run dev:api    # FastAPI on http://localhost:8000  (available from Stage 1.2)
npm run dev:web    # Next.js on http://localhost:3000
```

Or directly:

```powershell
cd services/api; .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
cd apps/web; npm run dev
```

Health check (from Stage 1.2): `GET http://localhost:8000/health` → `{"app":"scotch","status":"ok","version":"0.1.0"}`

## Testing

```powershell
npm run test:api   # backend pytest suite
```

## Documentation

- [docs/README.md](docs/README.md) — documentation index
- [docs/product/roadmap.md](docs/product/roadmap.md) — staged roadmap with live status
- [docs/product/prd.md](docs/product/prd.md) — product requirements

## Current Phase Status

**Phase 1 — Local Working Skeleton MVP: Stages 1.1 (Repository Setup) and 1.3 (Frontend Base App) complete.**
Stage 1.2 (Backend Health API) was deferred and is required before Stage 1.4 (Frontend API Client). See the [roadmap](docs/product/roadmap.md) for the full Phase 0–20 plan.
