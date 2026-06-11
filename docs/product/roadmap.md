# Scotch — Staged Roadmap & Status Tracker

This is the live progress tracker. Phases 0–20, each a mini-MVP. Every stage is implemented fully before the next; after each stage a Stage Completion summary is reported and confirmation requested.

Status values: ✅ Done · 🔵 In progress · ⬜ Not started

## Phase 0 — Product Understanding & Plan Lock — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 0.1 Questionnaire | 24-heading questionnaire answered ([questionnaire.md](questionnaire.md)) | ✅ |
| 0.2 PRD | [prd.md](prd.md) | ✅ |
| 0.3 Staged plan | This roadmap + CLAUDE.md + docs structure | ✅ |
| 0.4 Phase 1 approval | Plan approved by product owner (2026-06-12) | ✅ |

## Phase 1 — Local Working Skeleton MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 1.1 Repository setup | Verify Node/Python; git init; monorepo (`apps/web` create-next-app TS/Tailwind/App Router + shadcn/ui; `services/api` FastAPI requirements); root README, .env.example, scripts | ✅ |
| 1.2 Backend health API | `app/main.py`, `config.py`, `api/routes/health.py`; `GET /health` → `{"app":"scotch","status":"ok","version":"0.1.0"}`; CORS; pytest | ✅ |
| 1.3 Frontend base app | Landing (name, tagline, Start Local Project), dashboard shell, workspace shell, navigation | ✅ |
| 1.4 Frontend API client | `src/features/api/client.ts`; typed fetch; backend status indicator with error state | ✅ |
| 1.5 Documentation | README: purpose, stack, structure, run commands, health check, phase status | ✅ |

**Accept:** both servers run; /health works; landing → dashboard → workspace; README accurate.

## Phase 2 — CADAM-Like UI Shell MVP (mock data) — 🔵 In progress

| Stage | Scope | Status |
|---|---|---|
| 2.1 Design system | AppShell, TopBar, Sidebar, Button/Card/Panel/Badge; premium white tokens | ✅ |
| 2.2 Dashboard UI | New Project, Recent Projects, Templates (2BHK, 3BHK Villa, Studio, Small Cafe, Office, Duplex), backend status, settings placeholder | ✅ |
| 2.3 Workspace UI | CADAM 3-panel: prompt/generate/templates · 2D canvas + 3D tab + zoom · parameters/schedule/exports/warnings | ✅ |
| 2.4 Mock ArchitectureProject | Centralized typed mock feeding all panels | ⬜ |
| 2.5 SVG floor plan renderer | Site boundary, double-line walls, labels+areas, dimensions, door swings, window symbols, north arrow | ⬜ |
| 2.6 Docs | UI overview, mock structure, limitations | ⬜ |

**Accept:** presentable CADAM-like shell; mock plan renders; all panels populated.

## Phase 3 — Universal Architecture Data Model MVP — ⬜

| Stage | Scope | Status |
|---|---|---|
| 3.1 Pydantic models | Site, Building, Level, Room, Wall, Door, Window, Material, Parameter, Warning, ArchitectureProject, ExportManifest | ⬜ |
| 3.2 Frontend TS types | Mirrored in `src/features/project/types.ts` | ⬜ |
| 3.3 Validation system | Reusable validator: positive dims, valid units, unique room IDs, rooms inside site, level refs, warnings; pytest | ⬜ |
| 3.4 Sample project factory | Valid 2BHK with rooms/params/doors/windows/warnings | ⬜ |
| 3.5 Sample API | `GET /projects/sample` | ⬜ |
| 3.6 Frontend uses backend | Replace mock with API data | ⬜ |

**Accept:** schema solid; validation works; sample renders from backend; JSON documented.

## Phase 4 — Local Project Storage MVP — ⬜

| Stage | Scope | Status |
|---|---|---|
| 4.1 Storage layout | `data/users/local-user/projects/{id}/project.json` (+ `exports/`) | ⬜ |
| 4.2 Local store service | `core/storage/local_store.py`: create/list/get/update/delete, save_export_manifest | ⬜ |
| 4.3 Project routes | POST/GET `/projects`, GET/PATCH/DELETE `/projects/{id}` | ⬜ |
| 4.4 Dashboard listing | Saved projects from backend | ⬜ |
| 4.5 Creation flow | id, name, created_at, updated_at, prompt, data | ⬜ |
| 4.6 Workspace loading | Load by project ID | ⬜ |
| 4.7 Update flow | Title/data updates persist | ⬜ |

**Accept:** full CRUD + persistence across restart; pytest for store + routes.

## Phase 5 — Deterministic Text-to-Floorplan MVP — ⬜

| Stage | Scope | Status |
|---|---|---|
| 5.1 Requirement parser | `core/architecture/requirement_parser.py`: site, orientation, type, bedrooms, baths, rooms, floors, style, parking, balcony; smart defaults + assumption warnings | ⬜ |
| 5.2 Defaults library | `defaults.py`: living 12x14, kitchen 8x10, bedroom 11x12, master 12x13, bath 5x8, balcony 5x10, parking 10x15, dining 8x10, office 8x10, storage 5x6, cafe seating variable | ⬜ |
| 5.3 Layout generator | `floorplan_generator.py`: zoning rules, inside-site, warnings; residential + small cafe | ⬜ |
| 5.4 Generate API | `POST /generate/from-prompt` → `{project, summary, warnings}` | ⬜ |
| 5.5 Frontend wiring | Generate → plan/schedule/params/warnings + auto-save | ⬜ |
| 5.6 Test prompt set | 2BHK 30x50, studio 20x30, 3BHK villa 40x60, cafe 25x40, office 50x80 (graceful fallback) | ⬜ |

**Accept:** prompt → valid plan with no AI key; panels update; persists; logic documented.

## Phase 6 — Editable Parameters & Regeneration MVP — ⬜

| Stage | Scope | Status |
|---|---|---|
| 6.1 Parameter model | key/label/value/unit/min/max/editable/category/target_entity_id | ⬜ |
| 6.2 Panel editing | number/text/dropdown inputs, units, apply | ⬜ |
| 6.3 Room selection + on-canvas | Click room → highlight + panel + **inline edit popover (CADAM-style)** | ⬜ |
| 6.4 Live preview | Valid edits update SVG + schedule instantly | ⬜ |
| 6.5 Regenerate API | `POST /generate/regenerate` | ⬜ |
| 6.6 Validation on edit | Bounds, positivity, inside-site; warnings | ⬜ |
| 6.7 Persistence | Edited project saves | ⬜ |

**Accept:** edit (panel + canvas) → live preview → regenerate → validate → persist.

## Phase 7 — Export MVP — ⬜

| Stage | Scope | Status |
|---|---|---|
| 7.1 JSON export | Full ArchitectureProject | ⬜ |
| 7.2 Layered SVG export | site/rooms/walls/doors/windows/labels/dimensions groups | ⬜ |
| 7.3 PNG export | Rasterized plan | ⬜ |
| 7.4 Basic DXF | ezdxf; A-SITE, A-WALL, A-DOOR, A-WINDOW, A-ROOM-TEXT, A-DIMS | ⬜ |
| 7.5 Export manifest | filename/format/path/created_at | ⬜ |
| 7.6 Export panel | Download buttons: JSON/SVG/PNG/DXF | ⬜ |

**Accept:** all four formats download + saved under `exports/`; manifest tracked; pytest per exporter.

## Phase 8 — 3D Massing MVP — ⬜

| Stage | Scope | Status |
|---|---|---|
| 8.1 3D data generator | Slabs, wall extrusions, openings, roof, material tags | ⬜ |
| 8.2 R3F viewer | Orbit/zoom/pan/reset; 2D/3D toggle | ⬜ |
| 8.3 Extrusion | Walls from room boundaries, slab, roof plane | ⬜ |
| 8.4 Basic materials | Walls, floors, doors, glass, roof | ⬜ |
| 8.5 Parameter sync | Edits update 3D | ⬜ |
| 8.6 GLTF prep | Export path prepared | ⬜ |

**Accept:** 3D massing renders, syncs with edits, viewer stable.

## Phase 9 — AI Provider Integration MVP — ⬜

| Stage | Scope | Status |
|---|---|---|
| 9.1 Abstraction | `core/ai/provider.py`, `prompt_templates.py`, `schema_repair.py`; deterministic / Anthropic / OpenAI-compatible | ⬜ |
| 9.2 Prompt template | Architecture planning engine → valid ArchitectureProject JSON only | ⬜ |
| 9.3 Validation flow | Parse → validate → repair → deterministic fallback | ⬜ |
| 9.4 Mode toggle | deterministic / AI / hybrid | ⬜ |
| 9.5 Settings UI | Provider, mode, key-configured status | ⬜ |
| 9.6 AI test prompts | 2BHK, villa, studio, cafe, office, duplex | ⬜ |

**Accept:** AI mode works when key present; deterministic always available; bad output handled.

## Phase 10 — Design Options MVP — ⬜

Stages: 10.1 option model (option_id/score/summary/warnings/preview) · 10.2 compact/balanced/spacious generation · 10.3 option preview cards (mini plan, stats) · 10.4 apply selected option · 10.5 save options with project.
**Accept:** 3 options generate, selectable, selected becomes editable active project.

## Phase 11 — Software Export Adapters MVP (SketchUp + Revit prioritized) — ⬜

Stages: 11.1 DXF deepening (entities, text, dims) · 11.2 SketchUp Ruby exporter (.rb: slab, walls, opening placeholders, groups, materials) · 11.3 Revit add-in strategy (pulled up: C# architecture, JSON import flow, element creation plan, sync strategy) · 11.4 Blender Python exporter (walls/floors/materials/cameras/lights) · 11.5 Rhino script strategy.
**Accept:** DXF improved; .rb and .py exporters generate runnable scripts; Revit/Rhino strategy docs complete.

## Phase 12 — Presentation Sheet MVP — ⬜

Stages: 12.1 sheet data model (title, info, plan viewport, notes, schedule, legend, concept text) · 12.2 SVG sheet export · 12.3 PDF sheet export · 12.4 Illustrator-friendly layering · 12.5 Photoshop/InDesign strategy (board templates, PNG assets, PDF package).
**Accept:** sheet exports with plan/title/schedule/notes; structured SVG layers.

## Phase 13 — Architecture Intelligence MVP — ⬜

Stages: 13.1 spatial quality checks (room too small, bath far from bedroom, kitchen placement, ventilation, parking missing, circulation, outside-site, unused area) · 13.2 area calculations (site, built-up, rooms, carpet approx, circulation) · 13.3 optional vastu suggestions (toggle) · 13.4 room schedule export (JSON/CSV/table) · 13.5 intelligence panel UI.
**Accept:** warnings + area calcs + schedule export + optional vastu all working.

## Phase 14 — Revit Plugin MVP — ⬜

Stages: 14.1 C# add-in project setup · 14.2 JSON import · 14.3 element creation (levels, walls, floors, rooms, door/window placeholders) · 14.4 mapping documentation · 14.5 roundtrip strategy.
**Accept:** PoC add-in imports Scotch JSON, creates basic elements; mapping documented. (Live test requires Revit installed.)

## Phase 15 — SketchUp Plugin MVP — ⬜

Stages: 15.1 Ruby script improvement · 15.2 extension shell · 15.3 JSON import · 15.4 model creation (slabs/walls/doors/windows/labels/groups/materials) · 15.5 workflow documentation.
**Accept:** extension/script builds the model in SketchUp; documented.

## Phase 16 — Rhino / Grasshopper MVP — ⬜

Stages: 16.1 Rhino Python script export · 16.2 massing import · 16.3 Grasshopper parameter strategy · 16.4 parametric facade prototype (if feasible).
**Accept:** Rhino workflow exists; GH strategy documented.

## Phase 17 — Rendering Workflow MVP — ⬜

Stages: 17.1 render-friendly export (named/grouped hierarchy) · 17.2 material metadata · 17.3 camera suggestions (exterior, top, street, living room, balcony) · 17.4 Blender automation (scene/cameras/lights/materials/render settings) · 17.5 workflow docs (Lumion, D5, Enscape, V-Ray, Blender).
**Accept:** render-ready exports + Blender automation + documented engine workflows.

## Phase 18 — Cloud & Account MVP (preparation) — ⬜

Stages: 18.1 auth strategy (local user → Google login, ownership) · 18.2 database strategy (Postgres/Mongo, metadata, history) · 18.3 cloud storage strategy (S3/Supabase) · 18.4 local/cloud storage abstraction · 18.5 cloud-ready API structure.
**Accept:** local mode untouched; abstractions + strategy docs in place.

## Phase 19 — Versioning & History MVP — ⬜

Stages: 19.1 version model (version_id, created_at, change_type, summary, snapshot) · 19.2 history timeline UI · 19.3 restore version · 19.4 compare strategy (plan/param/area diffs).
**Accept:** history records, displays, restores.

## Phase 20 — Product Completion & QA MVP — ⬜

Stages: 20.1 full end-to-end QA · 20.2 error handling (API errors, toasts, loading/empty states) · 20.3 performance (SVG/3D/generation/loading/exports) · 20.4 UI final polish · 20.5 final documentation (overview, setup, architecture, data model, API, exports, integrations, roadmap, limitations) · 20.6 demo script (open → new project → 2BHK prompt → generate → edit dims → regenerate → 3D → export SVG/JSON → integration roadmap).
**Accept:** product runs end-to-end, presentable, documented, demo works.
