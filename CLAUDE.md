# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product

**Scotch** — an AI-native architecture design platform ("CADAM for architecture"). Users type natural-language prompts and get editable architectural designs: 2D floor plans, 3D massing, and exports into professional tools (AutoCAD via DXF, SketchUp, Revit, Rhino, Blender, render engines, Adobe suite). Tagline: *"Text-to-design for architecture."* The product name is **Scotch** everywhere — code, API responses, UI, docs (the folder name `RARCH` is historical; never use "raccoonArch").

## Core Pipeline (the architecture that everything hangs off)

```
prompt → requirement parser → ArchitectureProject JSON → validator
       → editable parameter model → 2D SVG renderer → 3D renderer (R3F)
       → export adapters → software integrations/plugins
```

**ArchitectureProject JSON is the single source of truth.** Every feature — generation, editing, 2D/3D preview, exports, plugins — reads from and writes to this model. Backend Pydantic models (`services/api/app/core/models/`) define it; frontend TypeScript types (`apps/web/src/features/project/types.ts`) mirror it exactly. Never let the two drift.

Key invariants:
- All generator and AI output is **validated by the backend before** rendering or exporting. The validator is one reusable module shared by generation, editing, and export paths.
- Deterministic rule-based generation must always work with **no AI key**. AI providers (Anthropic / OpenAI-compatible) sit behind an abstraction (`services/api/app/core/ai/provider.py`) with schema repair and deterministic fallback.
- Default units: **feet**. Smart defaults fill prompt gaps (e.g. 30x50 ft east-facing site) and every assumption is surfaced as an editable warning — never silently assumed.
- Storage is local-first: `services/api/app/data/users/local-user/projects/{project_id}/project.json` (+ `exports/` subfolder). The `local-user` segment exists so cloud auth can slot in later without restructuring.

## Repository Layout

```
RARCH/
  CLAUDE.md  README.md  .env.example  package.json
  docs/            # product brief, PRD, roadmap (phase status), questionnaire, integration guides
  apps/web/        # Next.js App Router + TypeScript + Tailwind + shadcn/ui
    src/app/         # routes: landing, dashboard, workspace
    src/components/  # design-system components (AppShell, panels, etc.)
    src/features/    # api client, project types, renderers (SVG 2D, R3F 3D)
  services/api/    # FastAPI + Pydantic v2
    app/main.py  app/config.py
    app/api/routes/  # health, projects, generate, exports
    app/core/        # models, validation, architecture (parser/generator), ai, storage, exports
    app/data/        # local project storage (gitignored)
```

## Commands

- Frontend: `cd apps/web` → `npm run dev` (http://localhost:3000)
- Backend: `cd services/api` → `uvicorn app.main:app --reload --port 8000`
- Backend tests: `cd services/api` → `pytest`
- Health check: `GET http://localhost:8000/health` → `{"app":"scotch","status":"ok","version":"..."}`

(Update this section whenever scripts change; Phase 1 creates them.)

## Phase Execution Rules (critical operating model)

Work proceeds in **Phases 0–20**, each a mini-MVP, defined in [docs/product/roadmap.md](docs/product/roadmap.md). The roadmap tracks current phase/stage status — read it at session start and keep it updated.

- Every stage inside a phase must be **fully implemented** before moving to the next stage.
- After completing each stage, report in the **Stage Completion Format**: Phase / Stage / Summary / Files created / Files modified / How to run-test / What works now / Known limitations / Next recommended stage — then ask: **"Should I continue to the next stage?"** Do not start the next stage without confirmation.
- Each stage carries backend pytest coverage for parser/generator/validation/export logic; frontend is verified manually plus strict TypeScript.

## UI Direction

The interface is modeled on **CADAM / adam.new** (https://github.com/Adam-CAD/CADAM): a premium white, studio-grade product for architects — soft gray borders, professional typography, generous spacing, clean shadows. Never let it feel like a student demo.

Workspace = CADAM 3-panel layout:
- **Left**: prompt input, generate button, template selector, generation mode.
- **Center**: 2D floor plan canvas (architectural standard: double-line walls, door swings, window symbols, dimension lines, room labels + areas, north arrow) with 3D massing tab.
- **Right**: parameter editor, room schedule, exports, warnings.

Parameter editing is **both** panel-driven and **on-canvas** (CADAM signature interaction): clicking a room in the SVG highlights it, loads it in the right panel, *and* opens an inline edit popover near the selection.

## Documentation Conventions

- `docs/product/brief.md` — full normalized product brief (vision, tool targets, completion target).
- `docs/product/prd.md` — locked requirements from the Phase 0 questionnaire.
- `docs/product/roadmap.md` — Phases 0–20 with stage-level status; the live progress tracker.
- `docs/product/questionnaire.md` — Phase 0 Q&A record (decisions of record).
- Integration guides (SketchUp, Revit, Rhino, Blender, rendering, sheets) land under `docs/integrations/` as their phases complete.
- Root `README.md` is the user-facing setup/run guide; update it at each phase's documentation stage.
