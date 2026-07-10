# Scotch — Post-MVP Wedge Strategy & Phase 21–27 Roadmap

Status values: ✅ Done · 🔵 In progress · ⬜ Not started

---

## Strategic Context

Scotch v1.0-beta shipped all 20 phases: deterministic + AI text-to-floorplan, editable parameters,
2D SVG + 3D R3F preview, 13 export formats (DXF, SketchUp, Blender, Rhino, glTF, sheets, CSV),
SketchUp / Revit / Rhino plugins, version history, spatial + Vastu intelligence, local-first storage
with cloud seams. 384 tests passing.

**Niche (locked):** Small-studio architects + students (+ interior designers). India-flavored
(feet / BHK / Vastu). Schematic stage. Export-as-moat. Never a walled garden.

**The market signals four things:**
- Text-to-plan is already wanted (Maket, Drafted $16M seed, Planner5D, RoomSketcher)
- Professional AI/BIM design is happening at the top (Snaptrude, Autodesk Forma, Finch, Architechtures)
- **Exports + integrations are the moat** — the serious tools all name Revit, Rhino, IFC, DXF
- Pure image AI is not enough — structured, validated models win over pretty renders

**Research confirms:** prompt → structured model → validation → editable output; RL-with-verifiable-rewards
for constraint following; MCP-driven IFC manipulation (MCP4IFC 2025 paper).

---

## The Wedge

> **Scotch is the agent-addressable, interoperable schematic layer that sits ON TOP of the architect's
> existing toolchain — not another walled-garden generator.** The validated `ArchitectureProject` model
> is the product; SketchUp, Revit, Rhino, AutoCAD, IFC, and our own web UI are interchangeable
> **clients** of it.

**"Model is the product, tools are clients"**

Competitors are destination apps that leak a dead export (Maket, Planner5D, Drafted) or walled SaaS
hubs (Snaptrude, Forma). Scotch makes the model canonical and every tool a view/editor over it — like
a Git object store with many client UIs. Edit in SketchUp → change flows back into the model → shows up
in the web app and all other tools. Combined with MCP (agents call the model) and round-trip (tools sync
to the model), Scotch becomes **infrastructure under the toolchain**, not an app you abandon after export.

This is the gap Snaptrude/Forma gesture at but haven't opened to the long tail.

**Two brand pillars:**
1. **Agentic / MCP-native model** — driven first by our own in-app chat
2. **Round-trip interop** — flagship-polished on SketchUp first

**Inspiration map (threaded through every phase):**
- **Snaptrude** — program→model spreadsheet (P21); brief→BIM/IFC (P22); agentic design (P24)
- **Forma** — site/sun/environmental context + IFC/OBJ (P22, P27)
- **Maket** — conversational refine loop + style recommendations (P23, P24)

---

## Decisions Locked

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary segments | Small firms/studios + students (co-equal) | Both live in SketchUp; students = top-of-funnel → firms |
| Flagship host | SketchUp | Most-used by the primary segments; extension exists |
| Headline agentic surface | In-app chat | Fully controlled UX; best demo; no external dependency |
| North-star UX | Snaptrude program→model | Unified with our editable parameters (same surface, not separate) |
| Market flavor | India-first | NBC/byelaws, BHK, feet, Vastu already in the DNA |

---

## Roadmap at a Glance

| Phase | Theme | Pillar / Bucket | Inspo |
|-------|-------|-----------------|-------|
| 21 | Program→Model spine = editable parameters | North-star foundation | Snaptrude |
| 22 | IFC export + multi-floor | Catch-up (BIM) | Snaptrude, Forma |
| 23 | In-app AI rendering | Catch-up (visual) | Maket, Veras/LookX |
| 24 | In-app agentic chat + MCP-native model | **Wedge pillar 1** | Snaptrude, Maket |
| 25 | SketchUp round-trip + MCP bridge | **Wedge pillar 2 (flagship)** | (moat) |
| 26 | Furniture / interior layout | Catch-up (secondary) | Planner5D, Maket |
| 27 | India compliance + Revit/Rhino round-trip + site/sun | Enhancement / expansion | Forma, Architechtures |

---

## Phase 21 — Program→Model Spine ✅

**Goal:** One Snaptrude-style live design-program table that *is* our editable-parameter surface.
Edit a cell → instant re-layout → 2D + 3D update. Program editing and parameter editing become
the same thing — not two separate concepts.

**Inspo:** Snaptrude's spreadsheet-style program that updates the 3D model instantly.

**Acceptance:** Program grid is live; cell edit debounces → regenerate → 2D + 3D update in <1 s;
room IDs stable across re-layout; add/remove row works; on-canvas inline edit stays in sync.

| Stage | Scope | Status |
|-------|-------|--------|
| 21.1 Stable room IDs | Implement semantic room-ID matching in `core/architecture/regenerate.py` so IDs survive re-layout (fixes the known ID-churn limitation). Use room `type` + ordinal as stable key (e.g. `bed-1`, `bath-1`) rather than regenerating from scratch. Add property test: generate → change site width → IDs of unchanged rooms are preserved. | ✅ |
| 21.2 Add/remove room via changes | Extend `ParameterChange` in `core/architecture/regenerate.py` to support `key="add_room"` (type, name) and `key="remove_room"` (target_id). Wire into `apply_changes()` so adding a bedroom triggers a re-pack with the new room inserted in the correct band, and removing one drops it cleanly. | ✅ |
| 21.3 Program grid backend | Add `GET /projects/{id}/program` route in `api/routes/generate.py` (or new `api/routes/program.py`) returning a structured program table: site rows (width/depth/orientation/floors), room rows (id/name/type/width/depth/area), totals (built-up area, coverage). This is a read-only projection of the existing model — no new storage needed. | ✅ |
| 21.4 Program grid UI | Replace the separate "Parameters" + "Room Schedule" sections in `apps/web/src/components/workspace/data-panel.tsx` with a single unified `ProgramGrid` component. Rows: site block (width, depth, orientation, floors as editable cells), then one row per room (name, width, depth, area auto-computed). Editing any cell calls the existing `onApplyChanges` path. Debounce 400 ms before firing. | ✅ |
| 21.5 Add/remove room UI | In the program grid, add a "+ Add room" row at the bottom (dropdown to pick type: bedroom/bathroom/kitchen/living/study/storage/balcony/parking) and a "×" delete button per row. Wire to the new `add_room`/`remove_room` change keys from stage 21.2. | ✅ |
| 21.6 Live 2D + 3D sync | Ensure the program grid edit → regenerate response → `floor-plan-svg.tsx` + `massing-viewer.tsx` update without a full page re-render. The existing `onApplyChanges` prop chain in `workspace.tsx` already handles this; verify debounce path and confirm no flicker on rapid cell edits. | ✅ |
| 21.7 On-canvas sync | Confirm the CADAM-style on-canvas inline edit popover (click room → popover) writes through the same `onApplyChanges` path and the program grid row updates to reflect the new value — the two surfaces must stay in lockstep. | ✅ |
| 21.8 Tests | Extend `services/api/tests/test_regenerate.py`: ID-stability property test (generate → site resize → unchanged room IDs preserved); add_room → valid re-layout; remove_room → rooms decrease; program endpoint returns correct row count and totals. | ✅ |

---

## Phase 22 — IFC Export + Multi-Floor ✅

**Goal:** Real BIM citizen and break the single-floor ceiling. The two most-cited pro-tool gaps
(Snaptrude, Forma, Architechtures all name IFC). OBJ optional follow-up for Forma parity.

**Acceptance:** `POST /projects/{id}/exports/ifc` returns a valid `.ifc` file that opens in a viewer;
multi-floor 2BHK prompt with `floors=2` generates stacked levels with a stair core; level selector in
the 2D/3D view switches active floor.

| Stage | Scope | Status |
|-------|-------|--------|
| 22.1 Multi-floor generator | Extend `core/architecture/floorplan_generator.py` to stack G+N floors when `req.floors > 1`. Ground floor gets parking + public program; upper floors get bedrooms + baths. A vertical circulation core (stair/lift room, id `stair-g`, `stair-1`, etc.) is placed consistently at the same x/y across all levels. Each `Room` already carries a `level` field — set it correctly per floor. | ✅ |
| 22.2 Multi-floor regenerate | Extend `core/architecture/regenerate.py` to handle multi-level re-packing. When `project.building.floors` changes, re-run the multi-floor generator with the existing room program distributed across the new floor count. | ✅ |
| 22.3 Level selector (frontend) | Add a level tab/selector to `apps/web/src/features/plan/floor-plan-svg.tsx` and `massing-viewer.tsx`. Filter rooms/doors/windows by `room.level === activeLevel`. The 3D viewer shows all levels stacked (correct elevation offset = `level * building.floor_height`). | ✅ |
| 22.4 Level row in program grid | Add a "Level" column to the program grid from Phase 21.4. Allow re-assigning a room to a different floor level. | ✅ |
| 22.5 IFC exporter | New `services/api/app/core/exports/ifc_exporter.py` using `ifcopenshell`. Map: `ArchitectureProject → IfcProject / IfcSite / IfcBuilding / IfcBuildingStorey (per level) / IfcSpace (per room)`. Coordinate transform: feet → metres (× 0.3048). | ✅ |
| 22.6 IFC API + UI | Register `ifc` in `ExportFormat` enum, wire `POST /projects/{id}/exports/ifc` in `api/routes/exports.py`. Add "IFC" button in "BIM" export group in `data-panel.tsx`. | ✅ |
| 22.7 Tests | `test_exports.py`: 8 IFC tests (file produced, parseable, space count, storey count, space names, multi-floor, API, download). `test_floorplan_generator.py`: 7 multi-floor tests. `test_regenerate.py`: 6 multi-floor regenerate tests. | ✅ |

---

## Phase 23 — In-App AI Rendering ✅

**Goal:** Generate presentation renders inside Scotch — not only export to Blender/Lumion.
One-click from the 3D viewer to a photoreal exterior or interior render. Inspo: Maket's instant
style renders, Veras/LookX render-from-model approach.

**Acceptance:** "Render" tab in the preview panel; pick a camera preset + style → render appears
in-app within 10–30 s (or massing capture fallback with no key); download as PNG.

| Stage | Scope | Status |
|-------|-------|--------|
| 23.1 Render provider seam | Extend `core/ai/provider.py` with a `RenderProvider` ABC (`render_image(project, camera_id, style) → bytes`). Implementations: `DeterministicRenderProvider` (returns the raw massing screenshot — never a hard failure); `StableDiffusionRenderProvider` (img2img from massing capture + style prompt); any SD-compatible API endpoint. Same factory pattern as the text providers. | ✅ |
| 23.2 Massing capture | Add a server-side or client-side massing capture path. Client-side: `THREE.WebGLRenderer` `render()` → `toDataURL()` in `massing-viewer.tsx` — already possible since the R3F canvas is accessible. Send base64 PNG to the render route as the conditioning image. | ✅ |
| 23.3 Style presets | Define render style presets in `core/render/styles.py`: `photorealistic_exterior`, `architectural_sketch`, `warm_interior`, `night_render`, `pencil_line`. Each carries a prompt suffix and negative prompt. Inspo: Maket style picker, LookX style adapters. | ✅ |
| 23.4 Render route | New `services/api/app/api/routes/render.py` with `POST /projects/{id}/render` accepting `{camera_id, style, conditioning_image_b64}`. Returns `{render_b64, style, camera_id}`. Route registered in `main.py`. | ✅ |
| 23.5 Render tab UI | Add "Render" tab to the preview panel in `apps/web/src/components/workspace/preview-panel.tsx` (alongside 2D / 3D). Content: camera preset selector (reuse the 5 presets from `/cameras`), style picker (5 preset cards with thumbnail swatches), "Generate Render" button, render result image, download button. Show loading skeleton while rendering. | ✅ |
| 23.6 Tests | No-key fallback returns the massing capture bytes (not an error). Style preset list returns 5 items. Route rejects missing camera_id. | ✅ |

---

## Phase 24 — In-App Agentic Chat + MCP-Native Model ✅

**Goal:** Drive the whole program→model spine by natural-language conversation. The model becomes
agent-callable — every operation exposed as an MCP tool. Inspo: Snaptrude's brief→BIM agentic
design; Maket's conversational refine loop.

**Acceptance:** Chat panel in workspace; "add a powder room near the entry" → room appears in
plan + program grid; "make the kitchen 10×12" → dimensions update; every AI edit is validator-gated;
MCP server runs independently and passes tool contract tests.

| Stage | Scope | Status |
|-------|-------|--------|
| 24.1 MCP server scaffold | New `services/mcp/` Python package. FastMCP or raw MCP SDK server exposing tools as thin wrappers over existing service/route logic — no business-logic duplication. Server registers with the existing FastAPI app or runs as a sibling process. | ✅ |
| 24.2 MCP tools — model read | Tools: `get_project(project_id) → ArchitectureProject`, `list_projects() → [StoredProjectMeta]`, `get_program(project_id) → ProgramTable`, `list_versions(project_id) → [VersionMeta]`. Thin wrappers over `core/storage` and the program endpoint from P21. | ✅ |
| 24.3 MCP tools — generate/edit | Tools: `generate_design(prompt, mode?) → ArchitectureProject`, `add_room(project_id, type, name?) → ArchitectureProject`, `remove_room(project_id, room_id) → ArchitectureProject`, `set_parameter(project_id, key, value, target_id?) → ArchitectureProject`. Each calls the existing `apply_changes` / generate path and runs the validator before returning — validator gate is non-negotiable. | ✅ |
| 24.4 MCP tools — intelligence + export | Tools: `run_intelligence(project_id, vastu?) → IntelligenceReport`, `export(project_id, format) → {filename, download_url}`, `render(project_id, camera_id, style) → {render_b64}`, `restore_version(project_id, version_id) → ArchitectureProject`. Thin wrappers over existing routes. | ✅ |
| 24.5 Chat panel UI | New `apps/web/src/components/workspace/chat-panel.tsx`. Collapsible bottom panel in the workspace. Message thread (user + assistant bubbles). Input textarea (Enter to send). Starter prompts when empty. Tool-call badges on assistant messages. | ✅ |
| 24.6 Chat → program grid sync | When chat triggers an `add_room`, `remove_room`, or `set_parameter` tool call, the updated `ArchitectureProject` is pushed back into workspace state via `handleChatProjectUpdate`. Program grid and 2D/3D update automatically — no separate refresh needed. | ✅ |
| 24.7 Tests | 24 tests in `test_chat.py`: tool contract tests (read + generate/edit + intelligence), validator-gate rejection, chat route integration (add/remove/resize/floors/show/help/404). | ✅ |

---

## Phase 25 — SketchUp Round-Trip + MCP Bridge ✅

**Goal:** Make SketchUp a true bidirectional client — the flagship proof that the model is canonical.
Edit in SketchUp → change flows back into Scotch → reflected in web app and version history.
This is the **moat**: competitors can't claim this without Scotch's validated central model.

**Acceptance:** Move/resize/rename a room in SketchUp → "Sync to Scotch" button in extension →
model updates in web app; version snapshot created; diff shows the change cleanly.

| Stage | Scope | Status |
|-------|-------|--------|
| 25.1 Stable sync protocol | New `services/api/app/core/sync/` package. Define `SyncContract`: a diff-able JSON payload keyed on stable room IDs from Phase 21. Fields per room: `id`, `name`, `type`, `x`, `y`, `width`, `depth`, `level`. Doors/windows as optional arrays. Protocol is append-only: unknown fields are ignored (forward-compatible). | ✅ |
| 25.2 Sync push route | New `POST /projects/{id}/sync` in `api/routes/` accepting a `SyncPayload` (rooms array from the host tool). Logic: for each room in payload, find by stable ID → update position/size; new IDs → add room; IDs absent from payload but present in model → flag for review (not auto-delete, to be safe). Run validator. Auto-snapshot with `change_type="sync"` (reuse Phase 19 version machinery). Return updated `ArchitectureProject`. | ✅ |
| 25.3 Sync pull route | `GET /projects/{id}/sync` returns the current `SyncContract` projection of the model — the minimal representation the plugin needs to reconstruct or update the SketchUp model. | ✅ |
| 25.4 SketchUp extension — push edits | Extend `integrations/sketchup/scotch/` (existing tags S-ROOMS / S-OPENINGS / S-LABELS already exist). Add `sync_push.rb`: traverses the Scotch group hierarchy, reads room group names (which encode `room_id`), extracts current bounding-box positions/sizes, builds the `SyncPayload`, POSTs to `POST /projects/{id}/sync`. Shows a result dialog with the diff summary. | ✅ |
| 25.5 SketchUp extension — pull updates | Add `sync_pull.rb`: GETs `GET /projects/{id}/sync`, compares with current model, moves/resizes room groups to match. Only moves groups; does not rebuild geometry — preserves any extra detail the architect added in SketchUp. | ✅ |
| 25.6 Extension UI | Add "Sync ↑ to Scotch" and "Sync ↓ from Scotch" menu items + toolbar buttons to the existing `scotch_importer.rb` extension. Show project ID picker (reads from a stored `.scotch_project_id` attribute on the model). | ✅ |
| 25.7 MCP bridge in-extension | Add an MCP client mode to the extension: when `SCOTCH_MCP_ENABLED=true` is set, the extension connects to the MCP server and exposes a "Chat with Scotch" dialog inside SketchUp. Agent calls manipulate the canonical model; the extension auto-pulls after each agent turn. This is the MCP4IFC-direction move for SketchUp. | ✅ |
| 25.8 Conflict handling | On sync push, if the incoming room dimensions differ from the model by more than a tolerance (0.5 ft), surface a conflict summary in the result dialog. The version snapshot (25.2) ensures any sync is fully reversible via the existing restore flow. | ✅ |
| 25.9 Tests | Round-trip test: generate project → build SyncPayload with one room resized → POST sync → GET project → room dimensions match. ID stability: sync does not create duplicate rooms. Validator gates: sync payload with invalid room size (< MIN_ROOM_DIM) is rejected. | ✅ |

---

## Phase 26 — Furniture / Interior Layout ✅

**Goal:** Plans that look real. Auto-place furniture so the 2D plan and 3D massing read as real
spaces, not empty boxes. Feeds renders (Phase 23) and serves the interior-designer slice of the niche.
Inspo: Planner5D's furniture placement, Maket's room visualization.

**Acceptance:** Generated 2BHK plan includes furniture (bed/wardrobe in bedrooms, sofa/TV in living,
counter/appliances in kitchen); furniture renders in 2D SVG as plan symbols and in 3D as basic blocks;
included in SketchUp and Blender exports.

| Stage | Scope | Status |
|-------|-------|--------|
| 26.1 FurnitureItem model | Add `FurnitureItem(id, type, room_id, x, y, width, depth, rotation)` to `services/api/app/core/models/project.py` and the TS mirror `apps/web/src/features/project/types.ts`. Add `furniture: list[FurnitureItem] = []` to `ArchitectureProject`. | ✅ |
| 26.2 Furniture defaults library | New `core/architecture/furniture_defaults.py` — per-room-type furniture templates: `bedroom` → bed (6×6), wardrobe (6×2); `living` → sofa (8×3), coffee table (4×2), TV unit (6×1.5); `kitchen` → counter (varies with room width), refrigerator (3×3); `dining` → table (5×3), chairs; `study` → desk (5×2.5), chair; `bathroom` → WC (2.5×2), basin (2×1.5), shower (3×3). Pattern mirrors the existing `defaults.py` room-size library. | ✅ |
| 26.3 Deterministic placement | New `core/architecture/furniture_placer.py`. For each room, load the template from 26.2 and place items with a clearance rule (min 2.5 ft walkway between items). Items that don't fit are skipped with an info warning. Generator calls the placer after `_openings()` and before returning the project. AI placement optional via the existing provider seam. | ✅ |
| 26.4 2D SVG symbols | Extend `apps/web/src/features/plan/floor-plan-svg.tsx` to render furniture plan symbols: bed (rectangle with headboard line), sofa (rectangle with back arc), counter (L-shape), WC/basin (standard symbols). Render as a `<g id="furniture">` layer. | ✅ |
| 26.5 3D furniture blocks | Extend `apps/web/src/features/massing/massing-viewer.tsx` and `massing-data.ts` to add simple box geometry per furniture item (height derived from type: bed 2 ft, table 2.5 ft, sofa 3 ft). Materials from room color palette, slightly darker. | ✅ |
| 26.6 Export inclusion | Include `furniture` in SketchUp Ruby exporter (`core/exports/sketchup_exporter.py`): each item as a flat box group in an `S-FURNITURE` tag. Include in Blender Python exporter (`core/exports/blender_exporter.py`): boxes in a `Scotch_Furniture` collection. Include in IFC exporter (Phase 22): `IfcFurnishingElement` per item. | ✅ |
| 26.7 Toggle | Add a "Show furniture" toggle in the program grid / data panel so users can opt out if they want a clean structural plan. Persisted as a project parameter. | ✅ |
| 26.8 Tests | Furniture placed within room bounds; min clearance respected; per-typology coverage (bedroom has bed, living has sofa); export files reference furniture geometry. | ✅ |

---

## Phase 27 — India Compliance + Round-Trip Rollout + Site/Sun ⬜

**Goal:** Deepen the regional moat; extend round-trip beyond SketchUp; add Forma-style site context.
Turns "smart defaults + Vastu" into a real design-review layer (NBC / local byelaws). Revit and Rhino
adopt the Phase 25 sync protocol.

**Acceptance:** Compliance report emitted alongside intelligence report; generated plan for a 30×50 ft
site in Mumbai passes NBC coverage and setback checks; Revit add-in has bidirectional sync; Rhino has
GH round-trip; sun/shadow widget in the 3D viewer.

| Stage | Scope | Status |
|-------|-------|--------|
| 27.1 Compliance engine | New `services/api/app/core/compliance/` package. `compliance_rules.py` encodes India NBC rules and common local byelaw patterns: FSI/FAR limits (e.g. 1.0–2.5 depending on zone), setbacks (front 3 m, side 1.5 m, rear 3 m), min room areas (bedroom ≥ 9.5 m², kitchen ≥ 5 m²), ventilation/light ratios (window area ≥ 1/8 floor area), min stair width (0.9 m), parking norms (1 per 2 BHK+). Build on `core/intelligence/spatial_checks.py` and `vastu.py` — same check-function pattern. | ⬜ |
| 27.2 Generator respects byelaws | Feed setback and FSI as hard constraints into `floorplan_generator.py`. After packing, verify FSI = built_up / site_area ≤ allowed_FSI; if exceeded, compress rooms proportionally and warn. Setback insets the usable area before band-packing (shrink site_width / site_depth by setback amounts). | ⬜ |
| 27.3 Compliance report API | Extend `GET /projects/{id}/intelligence` (or add `GET /projects/{id}/compliance`) to return a `ComplianceReport`: per-rule pass/fail with value vs. limit, overall `passes_review: bool`, and a plain-English summary. | ⬜ |
| 27.4 Compliance UI | Add a "Compliance" sub-section to the Intelligence panel in `data-panel.tsx`. Show a pass/fail badge per rule (green tick / red cross), overall "Passes review" / "Needs attention" status badge, and a download "Compliance report PDF" button. | ⬜ |
| 27.5 Revit round-trip | Extend the existing `plugins/revit/Commands/SyncCommand.cs` (currently rooms-only) to full bidirectional element sync using the Phase 25 sync protocol. Map Revit Wall/Floor/Room/Door/Window → `SyncPayload` and POST to `POST /projects/{id}/sync`. Pull syncs the other direction. | ⬜ |
| 27.6 Rhino/Grasshopper round-trip | Promote the existing RhinoPython exporter to a parameter-mapped GH round-trip. Add a Grasshopper "Scotch Sync" cluster (per the `rhino-grasshopper-strategy.md` spec from Phase 16.3) that reads from Scotch via `GET /projects/{id}/sync`, feeds GH sliders, and pushes changes back via `POST /projects/{id}/sync`. | ⬜ |
| 27.7 Site/sun context | Add a sun/shadow widget to the 3D massing viewer (`massing-viewer.tsx`): a time-of-day slider + date picker → compute sun direction from latitude/longitude (default: India, 20°N) using a simple solar position formula. Cast shadows from building massing using Three.js `DirectionalLight` with `castShadow`. Show shadow footprint on the ground plane. Extends the existing orientation + Vastu context into Forma-style environmental awareness. | ⬜ |
| 27.8 Tests | Compliance: 30×50 ft site passes NBC coverage; setback inset reduces usable area correctly; FSI over-limit triggers warning. Round-trip: Revit sync payload → model update → re-export → no drift. Sun: shadow direction changes with time of day. | ⬜ |

---

## Operating Model

Follow all CLAUDE.md phase rules for Phases 21–27:
- Every stage fully implemented before the next
- After each stage: Stage Completion Format report (Phase / Stage / Summary / Files created /
  Files modified / How to run-test / What works now / Known limitations / Next recommended stage)
- Ask "Should I continue to the next stage?" — do not start the next stage without confirmation
- Backend pytest coverage for all parser/generator/validation/export/sync logic
- Frontend verified manually + strict TypeScript (`npx tsc --noEmit` must pass)
- Update this file's status column as each stage completes

## Verification Checklist (per phase)

- `cd services/api && pytest` — all tests pass including new phase tests
- `cd apps/web && npm run dev` — workspace at http://localhost:3000; test the new surface
- `GET http://localhost:8000/health` → `{"app":"scotch","status":"ok",...}` unchanged
- **P22 IFC:** validate `.ifc` opens in a viewer (FZKViewer, BIMvision, or `ifcopenshell` script)
- **P24 MCP:** run MCP server; call each tool; confirm valid `ArchitectureProject` round-trips
- **P25 round-trip:** edit in SketchUp → sync → diff shows only the intended change
- **P27 compliance:** generated plan for known site emits expected pass/fail results

## Open Follow-ups (out of scope for this plan)

- **Cloud/multi-user + light collaboration** — the `CloudProjectStore` stub + `ProjectStore` ABC are
  the seam. Natural once agent/sync traffic justifies a hosted backend; serves the firms segment.
- **External-agent MCP access** (Claude Desktop / Cursor pointing at the MCP server) — same MCP server
  from P24, just open the port and document the connection string.
- **In-software MCP bridge for Revit/Rhino** — after SketchUp proves the pattern (P25).
- **Cost/feasibility/yield** — developer expansion segment (TestFit/Architechtures territory);
  unlocks once compliance engine (P27) is solid.
- **Scan-to-plan** (Magicplan direction) — site survey / photo upload → floor plan; post-P27.
