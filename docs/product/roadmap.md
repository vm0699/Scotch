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

## Phase 2 — CADAM-Like UI Shell MVP (mock data) — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 2.1 Design system | AppShell, TopBar, Sidebar, Button/Card/Panel/Badge; premium white tokens | ✅ |
| 2.2 Dashboard UI | New Project, Recent Projects, Templates (2BHK, 3BHK Villa, Studio, Small Cafe, Office, Duplex), backend status, settings placeholder | ✅ |
| 2.3 Workspace UI | CADAM 3-panel: prompt/generate/templates · 2D canvas + 3D tab + zoom · parameters/schedule/exports/warnings | ✅ |
| 2.4 Mock ArchitectureProject | Centralized typed mock feeding all panels | ✅ |
| 2.5 SVG floor plan renderer | Site boundary, poché walls, labels+areas, dimensions, door swings, window symbols, north arrow, zoom | ✅ |
| 2.6 Docs | UI overview, mock structure, limitations | ✅ |

**Accept:** presentable CADAM-like shell; mock plan renders; all panels populated.

## Phase 3 — Universal Architecture Data Model MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 3.1 Pydantic models | Site, Building, Level, Room, Wall, Door, Window, Material, Parameter, Warning, ArchitectureProject, ExportManifest | ✅ |
| 3.2 Frontend TS types | Mirrored in `src/features/project/types.ts` | ✅ |
| 3.3 Validation system | Reusable validator: positive dims, valid units, unique room IDs, rooms inside site, level refs, warnings; pytest | ✅ |
| 3.4 Sample project factory | Valid 2BHK with rooms/params/doors/windows/warnings | ✅ |
| 3.5 Sample API | `GET /projects/sample` | ✅ |
| 3.6 Frontend uses backend | Replace mock with API data (bundled mock kept as offline fallback) | ✅ |

**Accept:** schema solid; validation works; sample renders from backend; JSON documented.

## Phase 4 — Local Project Storage MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 4.1 Storage layout | `data/users/local-user/projects/{id}/project.json` (+ `exports/`) | ✅ |
| 4.2 Local store service | `ProjectStore` ABC (cloud open door) + `LocalProjectStore` with atomic writes, user_id threading, manifest appender; backend picked by `SCOTCH_STORAGE_BACKEND` | ✅ |
| 4.3 Project routes | POST/GET `/projects`, GET/PATCH/DELETE `/projects/{id}` with design validation on PATCH | ✅ |
| 4.4 Dashboard listing | Live project cards (loading/offline/empty states) with delete + confirm dialog | ✅ |
| 4.5 Creation flow | New Project dialog + template cards create stored projects | ✅ |
| 4.6 Workspace loading | Loads name/prompt/design by `?project=` id | ✅ |
| 4.7 Update flow | Generate persists design+prompt; inline title rename persists | ✅ |

**Accept:** full CRUD + persistence across restart; pytest for store + routes.

## Phase 5 — Deterministic Text-to-Floorplan MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 5.1 Requirement parser | `core/architecture/requirement_parser.py`: site, orientation, type, bedrooms, baths, rooms, floors, style, parking, balcony; smart defaults + assumption warnings | ✅ |
| 5.2 Defaults library | `defaults.py`: locked room-size library (living 14x12, kitchen 8x10, bedroom 11x12, master 12x13, bath 5x8, balcony 6x10, parking 10x15, dining 8x10, study 8x10, storage 5x6, cafe seating variable) | ✅ |
| 5.3 Layout generator | `floorplan_generator.py`: zoned band packing (public/service/private), width-wrap, clamp + depth-compression warnings, derived doors/windows; residential + cafe + office fallback | ✅ |
| 5.4 Generate API | `POST /generate/from-prompt` → `{project, summary, warnings}`, validated + advisories merged | ✅ |
| 5.5 Frontend wiring | Generate runs real generation from the prompt, updates all panels, auto-saves to the open project, shows the summary | ✅ |
| 5.6 Test prompt set | All 5 spec prompts valid (office via graceful fallback); zoning, doors, compression, save-flow — 28 cases | ✅ |

**Accept:** prompt → valid plan with no AI key; panels update; persists; logic documented.

## Phase 6 — Editable Parameters & Regeneration MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 6.1 Parameter model | key/label/value/unit/min/max/editable/category/target_id (min/max emitted by generator) | ✅ |
| 6.2 Panel editing | Number/text/orientation-dropdown inputs with units, range styling, single Apply for dirty fields | ✅ |
| 6.3 Room selection + on-canvas | Click room (plan or schedule row) → sky highlight + panel editor + **inline edit popover at the click (CADAM-style)**; Esc/blank-click deselects | ✅ |
| 6.4 Live preview | Regenerate response updates SVG, schedule, parameters, and warnings in one pass | ✅ |
| 6.5 Regenerate API | `POST /generate/regenerate` applies typed changes, re-packs bands, re-derives openings | ✅ |
| 6.6 Validation on edit | Client min/max gating + backend range checks (422) + full validator + recomputed warnings | ✅ |
| 6.7 Persistence | Applied edits PATCH the stored project; verified across reload | ✅ |

**Accept:** edit (panel + canvas) → live preview → regenerate → validate → persist.

## Phase 7 — Export MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 7.1 JSON export | Full ArchitectureProject | ✅ |
| 7.2 Layered SVG export | site/rooms/walls/doors/windows/labels/dimensions groups | ✅ |
| 7.3 PNG export | Rasterized plan (Pillow direct draw, 2× scale) | ✅ |
| 7.4 Basic DXF | ezdxf; A-SITE, A-WALL, A-DOOR, A-WINDOW, A-ROOM-TEXT, A-DIMS | ✅ |
| 7.5 Export manifest | filename/format/path/created_at; list + download API | ✅ |
| 7.6 Export panel | Download buttons JSON/SVG/PNG/DXF; busy spinner; last-export feedback | ✅ |

**Accept:** all four formats download + saved under `exports/`; manifest tracked; pytest per exporter.

## Phase 8 — 3D Massing MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 8.1 3D data generator | `features/massing/massing-data.ts`: ground/floor/roof slabs, 4-wall boxes per room, door + window glass insets; plan(x,y)→three.js(x,z) | ✅ |
| 8.2 R3F viewer | `massing-viewer.tsx` (next/dynamic ssr:false); OrbitControls, ambient+directional lighting, neutral background; reset camera button | ✅ |
| 8.3 Extrusion | Walls from room boundary boxes at building.floor_height, floor + roof slabs from site footprint | ✅ |
| 8.4 Basic materials | meshStandardMaterial palette: wall (#f8f7f5), floor (warm gray), roof (darker), glass (translucent blue), ground | ✅ |
| 8.5 Parameter sync | Viewer derives from `project` prop; useMemo re-runs buildMassingData on every project change — sync is automatic | ✅ |
| 8.6 GLTF prep | GLTFExporter lazy-imported; exportGltf() wired to GLTF button in viewer toolbar; downloads massing.gltf | ✅ |

**Accept:** 3D massing renders, syncs with edits, viewer stable.

## Phase 9 — AI Provider Integration MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 9.1 Abstraction | `core/ai/provider.py`, `prompt_templates.py`, `schema_repair.py`; deterministic / Anthropic / OpenAI-compatible | ✅ |
| 9.2 Prompt template | Architecture planning engine → valid ArchitectureProject JSON only | ✅ |
| 9.3 Validation flow | Parse → validate → repair → deterministic fallback | ✅ |
| 9.4 Mode toggle | deterministic / AI / hybrid | ✅ |
| 9.5 Settings UI | Provider, mode, key-configured status | ✅ |
| 9.6 AI test prompts | Mock provider tests — repair/fallback/mode; 32 new cases (124 total) | ✅ |

**Accept:** AI mode works when key present; deterministic always available; bad output handled.

## Phase 10 — Design Options MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 10.1 Option model | `DesignOption(option_id, variant, score, summary, warnings, preview)`; `StoredProject.options`; frontend `DesignOption` type | ✅ |
| 10.2 Variant generation | `size_modifier` in `DesignRequirements`; generator scales all room sizes by modifier; `options_generator.py` produces compact (0.82×) / balanced (1.0×) / spacious (1.2×) | ✅ |
| 10.3 Option cards | `OptionsPanel` with mini SVG plan (room-type colours), score badge, built area, summary; triggered by "compare options" link in prompt panel | ✅ |
| 10.4 Apply option | Selected option's preview becomes active design; canvas + schedule + params update; "Applied" badge on card | ✅ |
| 10.5 Save options | `POST /generate/options`; options PATCH'd to stored project; reloaded from storage on workspace open; 25 pytest cases | ✅ |

**Accept:** 3 options generate, selectable, selected becomes editable active project.

## Phase 11 — Software Export Adapters MVP (SketchUp + Revit prioritized) — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 11.1 DXF deepening | HATCH poché fill (ANSI31), DIMLINEAR room dims, opening call-out tags (D1/W1), north arrow, title block; new layers A-HATCH / A-ANNO / A-TITLE | ✅ |
| 11.2 SketchUp Ruby | `.rb` script: ground slab, hollow room walls (double-rect pushpull), room materials by type, door opening markers, roof slab, camera reset; S-SITE/S-ROOMS/S-ROOF tags | ✅ |
| 11.3 Revit add-in strategy | `docs/integrations/revit-addin-strategy.md`: C# project structure, add-in manifest, External Application/Command, JSON import flow, element creation (Levels→Walls→Floors→Rooms→Doors→Windows), FamilyFinder, round-trip sync, shared-parameter ID persistence | ✅ |
| 11.4 Blender Python | `.py` script: box_mesh helper, room walls + Boolean Difference for hollow rooms + door/window cuts, Principled BSDF materials, top ortho + exterior perspective cameras, sun + area lights, EEVEE render preset, collections | ✅ |
| 11.5 Rhino script strategy | `docs/integrations/rhino-strategy.md`: RhinoPython script structure, unit conversion strategy, Boolean Difference openings, Grasshopper data flow, custom GH cluster "Scotch Sync", plugin recommendations | ✅ |

**Backend**: `sketchup` and `blender` added to `ExportFormat`; `POST /projects/{id}/exports/sketchup` → `floor_plan.rb`; `POST .../blender` → `floor_plan.py`.  
**Frontend**: SketchUp (.rb) and Blender (.py) buttons in export panel with format tooltip.  
**Tests**: 46 export tests (26 new for Phase 11); 175 total passing.

**Accept:** DXF improved; .rb and .py exporters generate runnable scripts; Revit/Rhino strategy docs complete.

## Phase 12 — Presentation Sheet MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 12.1 Sheet data model | `page_size`, `title`, `subtitle`, `architect`, `concept_text` params; A3/A2/A1 page sizes | ✅ |
| 12.2 SVG sheet export | A3 landscape (420×297 mm viewBox); 7 Illustrator-compatible layer groups: `sheet-border`, `title-block`, `plan-viewport`, `schedule`, `legend`, `notes`, `footer`; north arrow; room schedule table; muted pastel room fills; `export_sheet_svg()` | ✅ |
| 12.3 PDF sheet export | reportlab Canvas; same layout as SVG sheet; `_pt()` mm→points, `_yf()` top-down→bottom-up; `clipPath()` plan viewport clipping; `export_sheet_pdf()` | ✅ |
| 12.4 Illustrator-friendly layering | Named `<g id="...">` groups map directly to Illustrator layers; XML export preserves editability | ✅ |
| 12.5 Presentation strategy doc | `docs/integrations/presentation-sheets-strategy.md` — Illustrator SVG workflow, Photoshop Smart Object board template, InDesign multi-page layout, PDF/X-1a print spec | ✅ |

**Accept:** sheet exports with plan/title/schedule/notes; structured SVG layers; PDF print-ready board; API endpoints `POST /projects/{id}/exports/sheet_svg` and `sheet_pdf`; 191 tests passing.

## Phase 13 — Architecture Intelligence MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 13.1 Spatial quality checks | `spatial_checks.py`: room_too_small, bath_bedroom_proximity (>25 ft), ventilation (no window), bathroom_missing, parking_missing (≥2 beds), coverage ratio (over/under), circulation (no door access); 7 check functions → `run_spatial_checks()` | ✅ |
| 13.2 Area calculations | `area_calculator.py`: site_area, built_up_area, carpet_area (×0.85), circulation_area, coverage_ratio %, floor_efficiency %; per-room RoomAreaEntry; `compute_areas()` | ✅ |
| 13.3 Vastu suggestions | `vastu.py`: 8-direction compass from room centroid; rules for kitchen (SE), master bed (SW), bathroom (avoid NE), living (N/E), study (E/N), puja (NE), dining (W/E); entrance orientation check; `run_vastu_checks()` | ✅ |
| 13.4 Room schedule export | `schedule_exporter.py`: `export_schedule_json()` and `export_schedule_csv()` with gross + carpet areas; `POST /projects/{id}/exports/schedule_json` → `room_schedule.json`; `schedule_csv` → `room_schedule.csv` | ✅ |
| 13.5 Intelligence panel UI | `intelligence-section.tsx`: AreaCard (site/built/carpet/open, Coverage %, Efficiency %), Design Quality list (severity icons, "N more" expand), 🪔 Vastu Shastra toggle (refetches with vastu=true, amber on-state); added to DataPanel between Room Schedule and Exports; Schedule JSON + CSV buttons added to Exports section | ✅ |

**API**: `GET /projects/{id}/intelligence?vastu=false` → IntelligenceReport (spatial_checks, area_summary, vastu_suggestions).  
**Tests**: 36 new Phase 13 tests; 227 total passing, 0 TypeScript errors.

**Accept:** warnings + area calcs + schedule export + optional vastu all working.

## Phase 14 — Revit Plugin MVP — ✅ Done

| Stage | Scope | Status |
|---|---|---|
| 14.1 C# add-in project setup | `ScotchRevit.csproj` (net48/x64, `System.Text.Json` v6.0.10); `ScotchRevit.addin` XML manifest; `App.cs` IExternalApplication with "Scotch" ribbon panel + Import/Sync buttons | ✅ |
| 14.2 JSON import | `Models/ArchitectureProject.cs` — all DTOs with `[JsonPropertyName]`; `Commands/ImportCommand.cs` — file picker → `JsonSerializer.Deserialize` → `Transaction` → `ElementMapper.Import` → result dialog | ✅ |
| 14.3 Element creation | `Mapping/CoordinateConverter.cs` — unit conversion + wall/opening/centroid geometry; `Mapping/FamilyFinder.cs` — width-matched door/window symbols; `Mapping/WallResolver.cs` — (roomId:side → ElementId); `Mapping/ElementMapper.cs` — Levels → WallType/FloorType → Walls (deduped via segment key) → Floors → Rooms → Doors → Windows; `ImportResult` summary | ✅ |
| 14.4 Mapping documentation | `docs/integrations/revit-mapping.md` — coordinate system, element creation order, field-level mapping tables, wall dedup detail, FamilyFinder algorithm, ScotchId shared param setup, known limitations | ✅ |
| 14.5 Round-trip sync | `Commands/SyncCommand.cs` — FilteredElementCollector rooms → BoundingBoxXYZ → RoomDto patch payload; `Services/ScotchClient.cs` — `GetProject` / `PatchProject` / `IsReachable` via `HttpClient` to `localhost:8000` | ✅ |

**Files**: `plugins/revit/` — `ScotchRevit.csproj`, `ScotchRevit.addin`, `App.cs`, `Models/ArchitectureProject.cs`, `Mapping/{CoordinateConverter,FamilyFinder,WallResolver,ElementMapper}.cs`, `Commands/{ImportCommand,SyncCommand}.cs`, `Services/ScotchClient.cs`; `docs/integrations/revit-mapping.md`.

**Build**: `dotnet build plugins/revit/ScotchRevit.csproj -c Release` (requires Revit 2024 SDK or `REVIT_PATH` env var pointing to Revit install).  
**Install**: copy `.dll` + `.addin` to `%APPDATA%\Autodesk\Revit\Addins\2024\`.  
**Accept:** PoC add-in imports Scotch JSON, creates Levels/Walls/Floors/Rooms/Doors/Windows; round-trip sync PATCH back to Scotch backend; mapping fully documented. (Live test requires Revit installed.)

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
