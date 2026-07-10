# Implementation Plan — Phases 15–20

> Detailed build plan for the final arc of Scotch: SketchUp plugin, Rhino/Grasshopper,
> rendering workflows, cloud readiness, version history, and product completion.
> Derived from [roadmap.md](roadmap.md). Read [CLAUDE.md](../../CLAUDE.md) and
> [docs/HANDOFF.md](../HANDOFF.md) first. Assumes Phases 0–14 complete.

## Conventions (apply to every stage)

- **Source of truth:** `ArchitectureProject` JSON. Pydantic [`services/api/app/core/models/project.py`](../../services/api/app/core/models/project.py) ↔ TS [`apps/web/src/features/project/types.ts`](../../apps/web/src/features/project/types.ts), snake_case, 1:1.
- **Exporters** live in `services/api/app/core/exports/`, consume only an `ArchitectureProject`, and register a format on `ExportFormat`. **Strategy/integration docs** live in `docs/integrations/`.
- **Every project-producing or project-reading endpoint runs the validator** and merges advisories into `project.warnings` (deduped by `.id`).
- **Reuse generator internals** (`_pack_bands`, `_openings`, `_Spec`) and the massing math (plan `(x,y)` → 3D `(x,z)`, height = `floor_height`); don't duplicate geometry logic.
- **Per stage:** implement fully → backend `pytest` (frontend = strict TS + build + preview checks) → one commit `Phase N Stage N.M: <what>` with the Claude co-author line → update [roadmap.md](roadmap.md) status → report in Stage Completion Format → ask before next stage.
- **UI bar:** CADAM-grade, minimalist-premium. Never a "basic" screen.
- **Plugin philosophy:** scripts before plugins (zero-install value first); plugins read the same JSON the scripts do; each ships mapping docs + a future-sync note.

---

## Phase 15 — SketchUp Plugin MVP

**Goal:** promote the Phase 11 one-shot `.rb` exporter into an installable SketchUp extension that imports Scotch JSON and builds an editable model. Live test requires SketchUp (2021+, Ruby API) installed; code + docs are deliverable regardless.

| Stage | Scope | Key files | Tests / acceptance |
|---|---|---|---|
| **15.1 Ruby script improvement** | Harden the Phase 11 generator: hollow rooms via double-rect pushpull, real door/window voids (erase face on shared wall), per-type materials, roof slab, grouped components named by room id, units set to feet. | `core/exports/sketchup_exporter.py` (extend) | pytest: script contains a group per room, material defs, opening markers; valid Ruby (smoke-parse for balanced `end`s). |
| **15.2 Extension shell** | A loadable SU extension package: `scotch_importer.rb` registering a `SketchupExtension`, a toolbar button + menu item, and an `extensions/scotch/` folder with loader. Backend serves it via a download endpoint. | `integrations/sketchup/scotch_importer.rb`, `integrations/sketchup/scotch/main.rb` | Manual load test doc; file-structure pytest (manifest registers extension, version string present). |
| **15.3 JSON import** | Extension reads a Scotch `project.json` (file picker dialog) and parses it into Ruby hashes; validate required keys, surface a messagebox on malformed input. | `integrations/sketchup/scotch/importer.rb` | Fixture `project.json` round-trips; missing-key path shows error (documented manual test). |
| **15.4 Model creation** | From parsed JSON build: ground slab, hollow room walls, door/window voids, room name 3D text labels, materials by room type, grouped + tagged (`S-SITE`/`S-ROOMS`/`S-ROOF`/`S-LABELS`). | `integrations/sketchup/scotch/builder.rb` | Manual: import sample 2BHK → editable grouped model; checklist in workflow doc. |
| **15.5 Workflow documentation** | `docs/integrations/sketchup-workflow.md`: export from Scotch → install extension → import → edit; screenshots placeholders; troubleshooting; version matrix. | `docs/integrations/sketchup-workflow.md` | Doc complete; linked from docs index. |

**Backend touchpoints:** `GET /integrations/sketchup/extension` (zips and serves `integrations/sketchup/`), or document manual copy to the SketchUp Plugins folder. Reuse `sketchup_exporter` for the script body so extension and one-shot export never diverge.
**Frontend:** in the export panel, add a "SketchUp extension" help affordance linking to the workflow doc (the `.rb` one-shot button already exists from Phase 11).
**Accept:** extension/script builds the model in SketchUp; documented.

---

## Phase 16 — Rhino / Grasshopper MVP

**Goal:** a RhinoPython export path plus a documented Grasshopper parametric strategy. Live test requires Rhino 7+/Grasshopper; code + docs deliverable regardless.

| Stage | Scope | Key files | Tests / acceptance |
|---|---|---|---|
| **16.1 Rhino Python script export** | New exporter emits `floor_plan_rhino.py` (RhinoPython): unit setup (feet→model units), layers per category (`Scotch::Site/Walls/Doors/Windows/Labels`), slab + walls as extrusions, door/window openings via `BooleanDifference`, room text dots. | `core/exports/rhino_exporter.py`; register `rhino` on `ExportFormat`; `POST /projects/{id}/exports/rhino` | pytest: script defines layers, one extrusion per room, BooleanDifference calls, valid Python (`ast.parse`). |
| **16.2 Massing import** | Script builds the 3D massing (walls extruded to `floor_height`, roof slab) matching the R3F viewer, so Rhino and the in-app 3D agree. | same exporter (massing section) | pytest: extrusion heights == floor_height; roof present. |
| **16.3 Grasshopper parameter strategy** | `docs/integrations/rhino-grasshopper-strategy.md`: expose site W/D, floor height, room sizes, facade params as GH inputs; data tree mapping from Scotch JSON; "Scotch Sync" cluster; recommended plugins (Pufferfish/Human). (Phase 11.5 strategy doc is the seed — extend, don't duplicate.) | `docs/integrations/rhino-grasshopper-strategy.md` | Doc complete; parameter table maps each `Parameter.key` → GH input. |
| **16.4 Parametric facade prototype** | If feasible: a small GH definition / RhinoPython routine generating a parametric facade (window grid from WWR ratio) on the front elevation; otherwise document the approach with a worked example. | `integrations/rhino/facade_prototype.py` or doc section | Prototype runs (manual) **or** documented with sample params + expected output. |

**Frontend:** add a "Rhino (.py)" button to the export panel (mirrors the SketchUp/Blender buttons).
**Accept:** Rhino script workflow exists; massing imports; GH strategy documented.

---

## Phase 17 — Rendering Workflow MVP

**Goal:** make exported models render-ready and document the path into Lumion, D5, Enscape, V-Ray, and Blender.

| Stage | Scope | Key files | Tests / acceptance |
|---|---|---|---|
| **17.1 Render-friendly export** | Audit GLTF + SketchUp + Blender exports for clean, named, grouped hierarchy: `Scotch/Walls/<room>`, `Scotch/Floors`, `Scotch/Roof`, `Scotch/Glass`; no ngons; consistent naming so render engines map materials by object name. | extend `gltf` path + `sketchup_exporter` + `blender_exporter` | pytest: object/group names follow the scheme; GLTF node hierarchy asserted. |
| **17.2 Material metadata** | Add `Material` records (wall/floor/glass/door/roof/exterior) with finish + base color + roughness hints to generated projects; carry into GLTF (KHR materials), Blender (Principled BSDF), SketchUp (material defs). | `core/architecture/materials.py` (assign defaults by room/element type); extend exporters | pytest: project has a material per element class; exporters emit them. |
| **17.3 Camera suggestions** | `core/architecture/cameras.py`: derive suggested cameras (exterior 3/4, top ortho, street eye-level, living-room interior, balcony) from site bbox + room centroids → `CameraSuggestion(name, position, target, fov)`. Surface in 3D viewer as preset buttons; embed in Blender/Rhino scripts. | `core/architecture/cameras.py`; `GET /projects/{id}/cameras`; viewer preset buttons | pytest: 5 cameras, positions outside/inside bbox as expected; viewer buttons jump the R3F camera. |
| **17.4 Blender automation** | Extend `blender_exporter`: full scene (sun + area lights, world bg), the suggested cameras, EEVEE/Cycles render preset, output settings, optional headless `--background` render note. | `core/exports/blender_exporter.py` (extend) | pytest: script defines lights, cameras, render engine + resolution; `ast.parse` valid. |
| **17.5 Rendering strategy docs** | `docs/integrations/rendering-workflows.md`: per-engine import path (Lumion via FBX/SKP, D5 via SKP/glTF, Enscape live-link from SketchUp, V-Ray, Blender native), material reassignment tips, camera/lighting starting points. | `docs/integrations/rendering-workflows.md` | Doc covers all 5 engines with concrete steps. |

**Frontend:** camera preset buttons in the 3D tab; "Render-ready" badge/tooltip on GLTF/Blender exports.
**Accept:** render-ready exports + material metadata + camera suggestions + Blender automation + documented engine workflows.

---

## Phase 18 — Cloud & Account MVP (preparation)

**Goal:** make Scotch cloud-ready without breaking local mode. The `ProjectStore` ABC + `user_id` threading (already in place) is the seam; this phase adds the abstractions and strategy, not a live cloud deployment.

| Stage | Scope | Key files | Tests / acceptance |
|---|---|---|---|
| **18.1 Auth strategy** | `docs/architecture/auth-strategy.md`: local-user → Google OAuth (PKCE), session/JWT, `user_id` derivation, project ownership, future team ownership. Add an `AuthContext` seam: `get_current_user_id()` dependency (returns `local-user` today) injected where routes currently hardcode the user. | `core/auth/context.py`; wire `Depends(get_current_user_id)` into project/export routes | pytest: routes still default to `local-user`; dependency override swaps the id and isolates data. |
| **18.2 Database strategy** | `docs/architecture/database-strategy.md`: Postgres (metadata/index) vs Mongo (document) trade-off; schema for users, projects, exports, versions; when JSON-on-disk graduates to a DB-backed index. Optional: a `ProjectIndex` SQLite implementation behind an interface for fast listing. | `docs/architecture/database-strategy.md`; optional `core/storage/sqlite_index.py` | Doc complete; optional index has pytest parity with directory scan. |
| **18.3 Cloud storage strategy** | `docs/architecture/cloud-storage-strategy.md`: S3/Supabase object layout mirroring the local tree (`users/{id}/projects/{id}/...`), signed-URL export downloads, asset/reference uploads. | `docs/architecture/cloud-storage-strategy.md` | Doc maps every local path to a cloud key. |
| **18.4 Local/cloud storage abstraction** | Confirm `ProjectStore` covers all cloud needs; add any missing methods (e.g. `list_export_manifests`, `get_export_path` already exist — verify); add a stub `CloudProjectStore` raising `NotImplementedError` to lock the contract; `get_project_store()` selects via `SCOTCH_STORAGE_BACKEND`. | `core/storage/cloud_store.py` (stub); `core/storage/factory.py` | pytest: factory returns local by default; cloud stub satisfies the ABC. |
| **18.5 Cloud-ready API structure** | Ensure routes are stateless and ownership-scoped: every project access goes through `(user_id, project_id)`; document pagination + auth headers for scalable listing. | route audit; `docs/architecture/cloud-api-readiness.md` | pytest: no route reads global state; all use the store + user dependency. |

**Accept:** local mode untouched; cloud-ready abstractions + strategy docs in place.

---

## Phase 19 — Versioning & History MVP

**Goal:** professional design iteration — every generation/edit snapshots, history is browsable, and any version restores.

| Stage | Scope | Key files | Tests / acceptance |
|---|---|---|---|
| **19.1 Version model** | `ProjectVersion(version_id, created_at, change_type: 'generate'|'regenerate'|'edit'|'option'|'restore', summary, snapshot: ArchitectureProject)`. `StoredProject.versions: list[ProjectVersion] = []` (or sidecar `versions/` files to keep `project.json` lean — prefer sidecar for large histories). Store appends a version on every design-mutating save. | `core/models/project.py`; `core/storage/*` (append on save) | pytest: generate→regenerate→edit yields 3 ordered versions with correct `change_type`. |
| **19.2 History timeline UI** | `history-section.tsx` (or right-panel tab): reverse-chronological list with change_type icon, summary, relative time, room count/area delta; mini SVG thumbnail per version. | `apps/web/src/components/workspace/history-section.tsx`; `GET /projects/{id}/versions` | TS clean; preview shows entries after edits. |
| **19.3 Restore version** | Restoring writes the snapshot as the active project **and appends a `restore` version** (never destroys history). Confirm dialog. | `POST /projects/{id}/versions/{version_id}/restore`; UI button | pytest: restore sets active = snapshot, appends restore version, history intact. |
| **19.4 Compare strategy** | `docs/product/version-compare-strategy.md` + a `GET /projects/{id}/versions/{a}/diff/{b}` returning structured diffs (added/removed/resized rooms, parameter changes, area deltas). UI compare can be minimal (side-by-side stats) for MVP. | diff endpoint; strategy doc; optional compare UI | pytest: diff detects room add/remove/resize and area change between two snapshots. |

**Accept:** version history records, displays, and restores; compare path defined.

---

## Phase 20 — Product Completion & QA MVP

**Goal:** make Scotch demo-ready and production-presentable end-to-end.

| Stage | Scope | Key files | Tests / acceptance |
|---|---|---|---|
| **20.1 Full end-to-end QA** | Exercise every flow: create → prompt generate (deterministic/AI/hybrid) → options → edit (panel + canvas) → regenerate → 3D + cameras → all exports (JSON/SVG/PNG/DXF/SketchUp/Blender/Rhino/sheet/schedule) → intelligence → history/restore → persistence across restart. Capture a QA checklist doc; fix every defect found. | `docs/product/qa-checklist.md`; fixes across the codebase | Checklist all-green; full `pytest` green; clean build. |
| **20.2 Error handling** | Backend: consistent error envelopes, 4xx/5xx with messages. Frontend: toast system, loading states on every async action, empty states, export-failure + offline messaging, validation surfacing. | `apps/web/src/components/ui/` toast; error boundaries; API error mapping | Inject failures (stop API, bad input) → graceful UI; pytest for error envelopes. |
| **20.3 Performance** | Profile + optimize: SVG render (memoize, avoid re-layout), 3D (instancing/dispose), generation latency, project load, export generation; debounce live edits; lazy-load the 3D bundle. | targeted edits; React `memo`/`useMemo`; dynamic imports | Before/after notes; no jank on the 2BHK→3BHK villa range; large-site smoke test. |
| **20.4 UI final polish** | Spacing/typography/icon pass; refined selected-room + parameter-edit + export UX; consistent empty/loading skeletons; keyboard affordances; responsive desktop polish; dark-surface review. | workspace + dashboard components | Visual QA at desktop widths; CADAM-grade bar met. |
| **20.5 Final documentation** | README + docs: product overview, setup, architecture, data model, full API reference, exports, all integrations, roadmap status, known limitations. Refresh the docs index. | `README.md`, `docs/**` | Docs cover every endpoint + integration; links valid. |
| **20.6 Demo script** | `docs/product/demo-script.md`: open → new project → 2BHK prompt → generate → edit dims → regenerate → 3D + camera → export SVG/JSON/DXF → show options → intelligence → history → integration roadmap. Timed, narrated, with fallback notes. | `docs/product/demo-script.md` | Script runs start-to-finish on a clean machine. |

**Accept:** product runs end-to-end, presentable, documented, demo works.

---

## Suggested execution order & checkpoints

1. **15** SketchUp extension (build on Phase 11 `.rb`) → commit per stage → ping at phase close.
2. **16** Rhino exporter + GH strategy.
3. **17** Rendering: materials → cameras → Blender automation → engine docs (depends on 15/16 export hierarchy).
4. **18** Cloud prep (docs + abstractions; no behavior change to local mode).
5. **19** Versioning (touches the model + store — land after exports stabilize).
6. **20** QA, polish, docs, demo — last, once everything else is in.

Each phase: full implementation, tests green, roadmap updated, Stage Completion Format report, PushNotification at phase close. Confirm before starting the next phase.

## Risks & notes

- **Plugin live-testing** (SketchUp/Rhino) needs the host app installed; deliver code + docs + automated structural tests, mark live verification as a manual checklist item.
- **Versioning storage growth:** prefer sidecar `versions/{version_id}.json` over inlining snapshots in `project.json` to keep loads fast; cap or prune very long histories if needed.
- **Material/camera additions** change the `ArchitectureProject` shape — update the Pydantic model **and** the TS mirror together, and bump any sample/factory fixtures + tests.
- **Phase 18 is preparation, not deployment** — do not break or complicate the local-first path; everything must still run with zero cloud config.
