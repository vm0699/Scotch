# Session Handoff — Implement Phases 7, 8, 9

> Written 2026-06-13 at the close of Phase 6. Read [CLAUDE.md](../CLAUDE.md) first, then this. The live status tracker is [docs/product/roadmap.md](product/roadmap.md).

## Where the product stands (Phases 0–6 ✅)

Scotch is a working local product: prompt → deterministic floorplan → architectural SVG drawing → CADAM-style editing (on-canvas popover + panel) → regenerate → persist. **72 backend pytest cases green**, frontend builds clean with strict TS.

- **Run:** `npm run dev:api` (FastAPI :8000) + `npm run dev:web` (Next.js :3000) from repo root. Tests: `npm run test:api`.
- **One commit per stage**, message format `Phase N Stage N.M: <what>`, ending with the Claude co-author line. Working tree is clean at `c866bc5`.
- **Verification pattern used so far:** backend pytest per stage; frontend `npm run build` + live checks via the `.claude/launch.json` preview servers (`web`, `api`) with `preview_eval` DOM assertions; visual plan checks by cloning the SVG full-screen via eval before screenshotting (the preview viewport is small and screenshots downscale).
- **Process:** the user prefers a whole phase done in one run ("complete phase X altogether, ping me" — send PushNotification at phase close), with per-stage focus, per-stage commits, and roadmap/docs/README status updates. UI must be minimalist-premium CADAM-grade (see memory `ui-quality-bar`); never ship a "basic" screen.

## Load-bearing architecture facts

- **ArchitectureProject JSON is the single source of truth.** Pydantic: `services/api/app/core/models/project.py`. TS mirror: `apps/web/src/features/project/types.ts` (snake_case, 1:1 — never let them drift).
- **Plan space:** x across site width, y along depth, **y = 0 is the entrance edge (drawn at top)**. Door/window `wall` is plan-local (north = top/entrance). Units: feet. SCALE = 12 px/ft in the frontend renderer.
- **Validator** (`core/validation/validator.py`) is shared by generation, regeneration, and PATCH; routes merge its advisory warnings into `project.warnings` (dedupe by id). Exports must reuse it too.
- **Generator** (`core/architecture/floorplan_generator.py`): band-packing; internal helpers `_Spec`, `_GenState`, `_pack_bands(bands, site_width, site_depth, state)`, `_openings(rooms, site_width, state)` are already reused by `regenerate.py` — reuse, don't duplicate.
- **Storage** (`core/storage/`): `ProjectStore` ABC with `user_id` threading (always `local-user` for now); `LocalProjectStore` at `app/data/users/{user}/projects/{id}/project.json` (gitignored), atomic writes. **`save_export_manifest(project_id, manifest)` already exists and appends to `exports/manifest.json` — Phase 7 builds on it.** `ExportManifest` model exists (filename/format/path/created_at). Routes get the store via `Depends(get_project_store)`; tests override with `app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)`.
- **Frontend state:** `workspace.tsx` owns project/selection/busy/notice; `client.ts` is the only fetch layer (`apiRequest` helper handles POST/PATCH/DELETE/204). `FloorPlanSvg` is pure & interactive (selection via `data-room-id` delegation in `preview-panel.tsx`).

## Phase 7 — Export MVP (stages 7.1–7.6)

Goal: JSON, layered SVG, PNG, DXF exports saved under each project's `exports/` folder, tracked in the manifest, downloadable from the export panel.

**Design intent:**
- New backend package `app/core/exports/`: one module per format, each consuming **only** an `ArchitectureProject` (never renderer internals). Validate before exporting.
- **SVG exporter (7.2)** must be a Python port of the frontend renderer's geometry (rooms as poché rects, door gaps + swing arcs, window symbols, labels, dimension slash ticks, north arrow) with **named layer groups**: `<g id="site|rooms|walls|doors|windows|labels|dimensions">`. Hardcode print-friendly colors (black/grays) instead of CSS vars. This SVG becomes the canonical 2D output (Phase 12 sheets reuse it).
- **PNG (7.3)** — rasterize the SVG. Try `cairosvg` (pip wheel may need cairo DLLs on Windows); if painful, fall back to `svglib` + `reportlab`, or draw directly with Pillow from project geometry (acceptable: simple rect/line/arc drawing). Spec says PNG is "if straightforward" — don't sink the phase into it; document the chosen route.
- **DXF (7.4)** — add `ezdxf` to requirements.txt. Layers: `A-SITE, A-WALL, A-DOOR, A-WINDOW, A-ROOM-TEXT, A-DIMS`. Walls as LWPOLYLINE rects per room (poché-equivalent: outer boundary polylines), door arcs as ARC, windows as LINEs, room labels as TEXT/MTEXT, site dims as simple lines+text (real DIMENSION entities optional).
- **API:** `POST /projects/{id}/exports/{format}` (format ∈ json|svg|png|dxf) → writes file to `exports/`, appends manifest, returns manifest entry; `GET /projects/{id}/exports` → manifest list; `GET /projects/{id}/exports/{filename}` → FileResponse download. Project must have design data (409/422 if `project` is null).
- **Frontend (7.6):** wire the four existing buttons in `data-panel.tsx` (currently disabled with "Phase 7" tooltips): enabled when `storedId && project`, busy spinners, then trigger browser download (fetch blob → object URL anchor click). Show last-export feedback subtly. For unsaved sessions, JSON export can be generated client-side (download the in-memory project) — nice degradation.
- **Tests:** per-exporter pytest (file exists, layers/groups present — parse SVG/DXF text; ezdxf can read back the DXF), manifest appending, API flow, no-design rejection.

## Phase 8 — 3D Massing MVP (stages 8.1–8.6)

Goal: 2D plan → simple 3D massing in the workspace's 3D tab, synced with edits.

**Design intent:**
- `npm i three @react-three/fiber @react-three/drei` in apps/web (+ `@types/three` if needed).
- **8.1 data generator:** pure TS module `apps/web/src/features/massing/massing-data.ts`: project → slab (site or built footprint, ~0.5 ft thick), wall segments per room edge (height = `building.floor_height`, thickness 0.5) with **openings cut as boxes** is hard — MVP: walls as boxes, door/window openings rendered as inset boxes (glass material) on the wall face rather than CSG cuts. Roof: flat slab over built footprint. Map plan (x,y) → three.js (x, z); height = y-up.
- **8.2 viewer:** `massing-viewer.tsx` (client, dynamic import with `next/dynamic` ssr:false — Next 16 + R3F needs this) rendered in the existing 3D tab of `preview-panel.tsx` (replace the placeholder EmptyState). OrbitControls (drei), soft lighting (ambient + directional), neutral background matching the dot-grid aesthetic, ground plane. Reset-camera button; reuse the existing zoom-cluster slot or add a small overlay control.
- **8.5 sync:** viewer derives entirely from the `project` prop — parameter edits already flow through workspace state, so sync is free; verify it.
- **8.4 materials:** simple `meshStandardMaterial` palette (walls white/light gray, floor warm gray, glass translucent blue, roof darker) defined in one map — Phase 17 extends it.
- **8.6 GLTF prep:** drei/three `GLTFExporter` wired behind a function (e.g. `exportGltf(scene)`) + a disabled-or-working "GLTF" button — document the path; full export UX can wait.
- **Verify:** preview_eval can check canvas existence + no console errors (`preview_console_logs`); screenshot for visuals. R3F in the small preview window is fine. Frontend-only phase (no pytest) — rely on strict TS + build + browser checks.

## Phase 9 — AI Provider Integration MVP (stages 9.1–9.6)

Goal: real LLM generation behind the existing abstraction, deterministic always available.

**Design intent:**
- `app/core/ai/`: `provider.py` (ABC `AIProvider.generate_project(prompt) -> ArchitectureProject` + `DeterministicProvider` wrapping the Phase 5 engine + `AnthropicProvider` + `OpenAICompatibleProvider`), `prompt_templates.py` (system prompt from the brief: "You are an architecture planning engine… Return only valid JSON" + embed the JSON schema via `ArchitectureProject.model_json_schema()`), `schema_repair.py` (strip markdown fences, extract first JSON object, coerce common issues, re-validate; on failure → deterministic fallback with an info warning "AI output invalid — deterministic fallback used").
- SDKs: add `anthropic` and `openai` to requirements but **import lazily** inside providers so the API runs without them configured. Keys via settings: `SCOTCH_ANTHROPIC_API_KEY` / `SCOTCH_OPENAI_API_KEY` / `SCOTCH_OPENAI_BASE_URL` (note: `.env.example` currently has unprefixed `ANTHROPIC_API_KEY` — either add `SCOTCH_`-prefixed vars or give Settings explicit `validation_alias`es; update `.env.example` accordingly). Default models: claude-sonnet-4-6 (good cost/quality for JSON generation) and gpt-class via base_url.
- **Modes:** `deterministic | ai | hybrid` (hybrid = try AI, fall back silently to deterministic). Request-level: `POST /generate/from-prompt` gains optional `mode`; default from settings `SCOTCH_GENERATION_MODE=deterministic`. Always run the validator + advisory merge regardless of source; AI output also goes through repair.
- **Settings UI (9.5):** `GET /settings/generation` → `{mode, provider, anthropic_configured: bool, openai_configured: bool}` (booleans only — never echo keys). Frontend: make the dashboard sidebar "Settings" item live → small settings surface (dialog or section) showing provider/mode with the AI mode toggle enabled only when a key is configured; also unlock the locked "AI" segment in `prompt-panel.tsx` accordingly.
- **Tests (9.6):** mock the provider (inject a fake returning good JSON / broken JSON / garbage) — verify validation, repair, fallback; mode selection; settings endpoint redaction. Never call real APIs in tests. The 6 spec prompts (2BHK, villa, studio, cafe, office, duplex) stay deterministic-tested; run them through AI mode manually only if the user provides a key.

## Gotchas learned (save yourself the re-discovery)

- **PowerShell 5.1:** no `&&`; use `;` or `if ($?)`. Multiline commit messages via `@'…'@` here-strings (closing `'@` at column 0). Git pipelines sometimes exit 255 from stderr warnings while the commit succeeds — check `git log`.
- **CRLF warnings** on every commit are noise; ignore.
- **shadcn CLI (new):** non-interactive needs `-b radix -p nova`; `-y` alone still prompts for preset (first run hung and had to be killed).
- **Next 16:** `searchParams` is a Promise in page props; AGENTS.md says check `node_modules/next/dist/docs` when unsure; route conflicts — keep `/projects/sample` registered before `/projects/{id}`.
- **Preview tooling:** viewport is narrow and screenshots downscale — for plan-quality checks, eval-clone the SVG to full-screen `document.body` then screenshot (reload restores). `preview_start` needs port 3000/8000 free (stop background `npm run start` tasks first). React state updates aren't visible in the same eval tick — re-eval after.
- **Edit tool:** roadmap table rows have been reworded in place — re-read the exact text before search/replace.
- **`lru_cache` on `get_project_store`/`get_settings`:** env-dependent config is cached per-process; tests must use `dependency_overrides`, not env mutation.

## Suggested execution order

Phase 7 backend exporters + tests → commit per stage → frontend export panel → verify downloads in preview → docs/roadmap → commit → **Phase 8** install R3F → massing data → viewer → sync verify → GLTF prep → docs → **Phase 9** provider package + tests → mode plumbing → settings UI → docs → ping the user (PushNotification) at each phase close, with the Stage Completion Format report per phase.
