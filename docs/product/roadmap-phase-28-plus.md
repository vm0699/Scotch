# Scotch — Phase 28+ "Prompt-to-Production" Roadmap

Status values: ✅ Done · 🔵 In progress · ⬜ Not started

This is the live tracker for the prompt-to-production arc (Phases 28–42), continuing from
[roadmap.md](roadmap.md) (Phases 0–20) and [roadmap-phase-21-27.md](roadmap-phase-21-27.md). It is the
master execution document. Companions: [phase-28-founder-requirements-map.md](phase-28-founder-requirements-map.md)
(requirement traceability) · [../architecture/external-services-and-data.md](../architecture/external-services-and-data.md)
(external dependencies) · [demo-script-v1.1.md](demo-script-v1.1.md) (v1.1 demo).

---

## Strategic context

Scotch v1.0-beta shipped Phases 0–27: deterministic + AI text-to-floorplan, editable parameters,
2D SVG + 3D R3F preview, 13 export formats, SketchUp/Revit/Rhino/Blender integrations, version history,
spatial + Vastu + NBC intelligence, MCP-native chat, local-first storage with cloud seams. 530 backend
tests pass; TypeScript clean.

**New direction (founder):** a **prompt-to-production architecture workflow system** that automates the
tedious parts of architectural production — working drawings, MEP layers, detail drawings, material/BOQ/
cost, Tamil Nadu advisory compliance, client-change management, and 2D-first → render-ready 3D — driven
primarily by plain-English prompting.

**The litmus prompt:** *"Create a 2BHK villa in Tamil Nadu on a 30x50 ft east-facing plot. Make it
budget friendly, include parking, furniture, plumbing, electrical, lighting, AC points, working drawing
dimensions, tile quantity, toilet detail, kitchen detail, and check Tamil Nadu advisories."* → the
system understands, creates/updates the project, generates drawings/layers/details/BOQ/advisories, and
shows editable outputs.

## Non-negotiable invariants (apply to every stage)

1. `ArchitectureProject` JSON is the single source of truth. New modules read/write it (inline) or a
   validated sidecar.
2. Every generate / edit / sync / export path runs `validate_project` before returning or persisting.
3. Pydantic models (`services/api/app/core/models/`) ↔ TypeScript types
   (`apps/web/src/features/project/types.ts`) stay 1:1, snake_case.
4. Deterministic generation works with **no AI key**. AI (via `core/ai/provider.py`) only improves
   intent understanding/adaptation; deterministic fallback always available.
5. Conceptual/semi-working outputs (MEP, details, advisories) carry `confidence` + `needs_review`
   (and `needs_professional_verification` for regulations).
6. CADAM-grade, minimalist-premium UI bar. Never a basic screen.
7. Frontend is a **non-standard Next.js** — consult `node_modules/next/dist/docs/` before any frontend
   code (`apps/web/AGENTS.md`).

## Schema-placement principle

- **Inline in `ArchitectureProject`** (versions with the project): `stairs`, `dimensions`, `mep_plan`,
  `material_plan`, `cost_plan`, `detail_drawings`, `client_brief`, `feasibility`.
- **Sidecar files + index** (workflow/account metadata, mirrors existing `versions/`): `client_change_requests`,
  `reference_assets`, user/architect-twin `profile`, review comments/issues.

## Universal per-phase implementation pattern (applied 29→42)

1. **Recon doc** `docs/product/phase-NN-*-current-state.md` — inspect exact seams before coding.
2. **Schema** — extend `project.py` (inline) or add sidecar model; mirror in `types.ts`; default-empty
   for back-compat; add to validator defaults / load path.
3. **Deterministic engine** — template-driven JSON under `services/api/app/data/...`; works with no AI
   key; emits `confidence`/`needs_review`/warnings.
4. **Validated pathway** — runs `validate_project` (+ module checks) before persist; reuse `_apply_and_save`.
5. **Prompt commands** — add `ParameterChange` keys and/or chat tools; register Anthropic tool schema +
   `_execute_tool` dispatch + deterministic keyword branch; surface tool-call badges + affected items.
6. **Studio UI** — new workspace tab/panel; layer toggles, editable tables, selection→properties,
   warnings/confidence; reuse `onApplyChanges`; consult Next.js docs first.
7. **Exports** — register new formats; named layers; tie to version; mark stale after changes.
8. **Tests** — backend pytest per module; strict `tsc --noEmit`; keep all existing tests green.
9. **Stage Completion Format report** + "Should I continue?" checkpoint ping.

## Seams every phase plugs into (verified against codebase)

| Seam | File |
|---|---|
| Universal model | `services/api/app/core/models/project.py` |
| TS mirror | `apps/web/src/features/project/types.ts` |
| Validated edit path | `core/architecture/regenerate.py` (`apply_changes`, `ParameterChange`) |
| Validator | `core/validation/validator.py` (`validate_project`) |
| Generator internals | `core/architecture/floorplan_generator.py` (`generate_floorplan`, `_pack_bands`, `_openings`, `_stair_spec`) |
| Chat tools (shared chat + MCP) | `core/chat_tools.py` (`_load`/`_save`/`_apply_and_save`) |
| Chat route | `api/routes/chat.py` (`_TOOL_SCHEMAS`, `_execute_tool`, deterministic fallback) |
| Export registration | `api/routes/exports.py` (`ExportFormat`, `_EXT`, `_MIME`, `_EXPORTERS`) |
| Router wiring | `app/main.py` |
| Frontend workspace | `components/workspace/workspace.tsx` → prompt/preview/data/chat panels |
| Storage + versions | `core/storage/` + sidecar `versions/` |

---

## Roadmap at a glance

| Phase | Theme | Bucket | Status |
|---|---|---|---|
| 28 | Planning restructure (docs) | Planning | ✅ |
| 29 | MEP Production Layer Studio | Production core | ✅ |
| 30 | Detail Drawing KB + Generator | Production core | ✅ |
| 31 | Material / Tile / BOQ / Cost | Production core | ✅ |
| 32 | Tamil Nadu Advisory Pack | Regional moat | ✅ |
| 33 | Architect-Twin Personalization | Differentiation | ⬜ |
| 34 | Client Change Mgmt + Affected-Item | Workflow | ⬜ |
| 35 | 2D-to-3D Production + Render-Ready | Visual | ⬜ |
| 36 | Prompt-First Toolchain Completion | Wedge | ⬜ |
| 37 | Cloud/Auth prep for twin memory | Infra | ⬜ |
| 38 | External MCP + software control | Wedge/interop | ⬜ |
| 39 | Reference / Scan-to-Plan ingestion | Expansion | ⬜ |
| 40 | Feasibility / Yield (TestFit-lite) | Expansion | ⬜ |
| 41 | Collaboration / Review / QA | Studio workflow | ⬜ |
| 42 | Release hardening + pilot package | Release | ⬜ |

---

## Phase 28 — Planning Restructure 🔵

**Goal:** convert the founder's 25 answers into a precise, implementation-ready roadmap; produce the
full picture before implementation begins.

| Stage | Scope | Status |
|---|---|---|
| 28.1 | Founder requirements map — [phase-28-founder-requirements-map.md](phase-28-founder-requirements-map.md) | ✅ |
| 28.2 | This roadmap (Phases 28–42, stage-by-stage) | ✅ |
| 28.3 | Product spec updates — [roadmap.md](roadmap.md) pointer, [prd.md](prd.md) positioning, [demo-script-v1.1.md](demo-script-v1.1.md), [external-services-and-data.md](../architecture/external-services-and-data.md) | ✅ |

**Accept:** all 25 requirements + 2 MAKE-SURE directives mapped; every Phase 29–42 stage has scope +
acceptance + tests + docs; product docs reflect prompt-to-production positioning; v1.1 demo target clear.

---

## Phase 29 — MEP Production Layer Studio ✅

**Goal:** plumbing, electrical, lighting, AC as editable, prompt-controlled, exportable 2D layers that
"think like an architect" (room-type → service-needs, prompt overrides respected, confidence +
needs_review surfaced). Conceptual/semi-working, clearly flagged. Stage 29.0 lands the real-scale
dimension/units/stairs groundwork that MEP and details depend on.

**Acceptance:** prompt "add plumbing, electrical, lighting, AC" → visible editable 2D layers → export
with named layers; warnings/confidence shown; MEP updates or goes stale-with-warning when rooms change;
user overrides preserved across regen.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 29.0 Dimension+units+stairs groundwork | `UnitConversionService` (feet↔meters, project-unit-aware); `DimensionEntity` + `dimensions: list[…]=[]`; `AutoDimensionEngine` (room/external/opening dims); SVG dimension layer + visibility toggle; explicit `stairs` extending `_stair_spec` (riser/tread/width defaults, 2D symbol, basic 3D); defaults documentation | `core/units.py`(new), `core/architecture/dimension_engine.py`(new), `core/architecture/stairs.py`(new), `models/project.py`, `types.ts`, `floor-plan-svg.tsx`, `massing-data.ts` | `test_units.py`, `test_dimension_engine.py`, stair tests; metric round-trip | ✅ |
| 29.1 MEP recon | Inspect model, validator, floor-plan renderer, chat routing, exports | — | `docs/product/phase-29-mep-current-state.md` | ✅ |
| 29.2 MEP schema | `mep_plan: MEPPlan{plumbing,electrical,lighting,ac}`; `ServicePoint(id, system, kind, room_id, x, y, mount_height, confidence, needs_review, user_override)`; `ServiceRoute(id, system, polyline:[[x,y]], kind, confidence)`; `Fixture/Switch/Socket/LightPoint/ACUnit` typed; warnings; default-empty back-compat | `models/project.py`, `core/models/__init__.py`, `types.ts`, `validator.py` | `test_mep_model.py` (old project loads; defaults) | ✅ |
| 29.3 MEP template library | `data/mep_templates/{plumbing,electrical,lighting,ac_split}_residential.json`: symbol, room-type→needs map, default placement logic, editable params, warnings, confidence, source note, needs_review | new JSON | `test_mep_model.py` (templates load + schema-valid) | ✅ |
| 29.4 MEP generator | `core/architecture/mep_generator.py`: `MEPIntentResolver` (room-type→service-needs), plumbing points (kitchen/toilet/utility) + conceptual pipe/drain routes, electrical switch/socket, lighting points, split-AC; `WetAreaAnalyzer` + `PlumbingRouteLengthEstimator` (advisory, never forces grouping); confidence scorer; **preserves `user_override`** on regen; runs after `_openings()` + on regenerate | `mep_generator.py`(new), `floorplan_generator.py`, `regenerate.py` | `test_mep_generation.py` (points within rooms; toilet→plumbing; wet-area advisory not forced; override preserved; stale on room change) | ✅ |
| 29.5 MEP prompt commands | Verbs: add plumbing/electrical/lighting/AC layer, "shift AC to opposite wall", "move sink point", "add two sockets in bedroom", "show only electrical", "regenerate lighting", "explain MEP warnings". Chat tools `generate_mep`, `edit_mep_point`; schema+dispatch+deterministic keyword branch | `chat_tools.py`, `api/routes/chat.py` | `test_mep_chat.py` (each verb mutates + validates) | ✅ |
| 29.6 MEP Studio UI | `MEPStudio` tab: layer toggles (arch/plumbing/electrical/lighting/AC/dims), editable point table, `ServiceRouteOverlay`, warnings/confidence panel, selection→properties, prompt-action badges; CADAM-grade | `components/workspace/mep-studio.tsx`(new), `workspace.tsx`, `preview-panel.tsx` | manual + `tsc --noEmit` | ✅ |
| 29.7 MEP export | SVG/DXF/(PDF) named layers `P-PIPE/P-FIXTURE/E-LIGHT/E-SWITCH/E-SOCKET/E-ROUTE/M-AC`; register `mep_svg`/`mep_dxf` formats | `core/exports/svg_exporter.py`, `dxf_exporter.py`, `api/routes/exports.py` | `test_mep_exports.py` (layers present, points emitted) | ✅ |
| 29.8 Tests | All four MEP test files green; existing 530 still green | — | `pytest` all pass | ✅ |

---

## Phase 30 — Detail Drawing Knowledge Base + Generator ✅

**Goal:** schematic→working-level detail drawings from structured templates linked to project objects;
details go stale when source objects change. Reduces manual 2D-detail time (MAKE SURE #1, 2D-first).

**Acceptance:** "generate toilet detail for bath-1" → dimensioned detail linked to that bathroom; goes
stale after the bathroom changes; previews + exports to SVG/PDF/(DXF).

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 30.1 Recon | Inspect sheet exports, SVG/PDF exporters, drawing model, door/window schedule, object IDs | — | `docs/product/phase-30-detail-current-state.md` | ✅ |
| 30.2 Detail template library | 6 JSON templates in `data/detail_templates/`: toilet, kitchen, door_window, wall_section, tile_layout, stair; confidence, needs_review, source, annotations per template | new JSON | `test_detail_templates.py` (load + schema-valid + required fields) | ✅ |
| 30.3 Detail model | `DetailDrawing(id, name, detail_type, source_object_ids, primitives:[LinePrimitive|ArcPrimitive|TextPrimitive|DimPrimitive|HatchPrimitive], canvas_w/h, scale, view, warnings, annotations, confidence, needs_review, stale)`; discriminated union via `Annotated[Union[…], Field(discriminator="kind")]`; `detail_drawings: list[…]=[]` inline | `models/project.py`, `types.ts` | round-trip + back-compat | ✅ |
| 30.4 Detail generators | `core/architecture/detail_engine.py`: `DetailEngine.generate(project, detail_type, source_id)` dispatches to 6 generators; primitive geometry from project objects + templates; `mark_stale_for_source`, `replace_or_add`, `remove` | `detail_engine.py`(new), `regenerate.py` | `test_detail_generation.py` (22 tests) | ✅ |
| 30.5 Prompt commands | "generate toilet detail", "wall section", "tile layout", "delete detail". Chat tools `generate_detail`, `list_details`, `delete_detail`; Anthropic schema + dispatch + keyword branch | `chat_tools.py`, `api/routes/chat.py` | `test_detail_chat.py` (9 tests) | ✅ |
| 30.6 Detail Studio UI | Detail Drawings panel: generate form (type+source dropdowns), detail cards with SVG preview, stale warning, annotations, export SVG link, delete; CADAM-grade | `components/workspace/detail-studio.tsx`(new), `workspace.tsx`, `data-panel.tsx` | manual + `tsc --noEmit` | ✅ |
| 30.7 Detail exports | `core/exports/detail_exporter.py` (40px/ft, named layers: outline/fixture/appliance/hatch/annotation/dim, title block, "FOR REVIEW" watermark); `GET /projects/{id}/details/{did}/svg`; `api/routes/details.py` router (5 endpoints) | `detail_exporter.py`(new), `details.py`(new), `main.py` | `test_detail_exports.py` (13 tests) | ✅ |
| 30.8 Tests | 94 detail tests green (5 files); existing 598 still green → **692 total** | — | `pytest` 692 passed | ✅ |

---

## Phase 31 — Material / Tile / BOQ / Cost Engine ✅

**Goal:** material planning + early cost estimation; quantities trace to objects; manual editable rates
first (INR ₹, per-sqft — see open questions); BOQ updates after plan changes.

**Acceptance:** change tile size/rate → updated tile quantity + cost; BOQ recomputes after room/area
change; missing rates flagged; export CSV/JSON/PDF.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 31.1 Recon | Inspect material model, program table, schedule exports, area calc, export manager | — | `docs/product/phase-31-boq-current-state.md` | ✅ |
| 31.2 Material plan | `material_plan: MaterialPlan{room_finishes, tile_specs, paint_specs, wall_finish_specs, door_window_specs, fixture_specs, editable_rates, assumptions}`; `TileSpec(size_w, size_h, rate, wastage_pct)`; `RoomFinish(room_id, floor, wall, ceiling)`; inline | `models/project.py`, `types.ts` | back-compat | ✅ |
| 31.3 Quantity engine | `core/boq/quantity_engine.py`: floor area, tile count (+wastage), skirting length, toilet/kitchen wall-tile area, paint area, opening counts, furniture/fixture/MEP-fixture counts; each `BOQItem` carries `source_object_ids`. Reuse `core/intelligence/area_calculator.py` | `core/boq/quantity_engine.py`(new) | `test_quantity_engine.py` (tile count = ceil(area×(1+wastage)/tile_area); skirting = perimeter−openings) | ✅ |
| 31.4 BOQ/cost plan | `cost_plan: CostPlan{boq_items, category_totals, grand_total, missing_rates, assumptions, confidence, needs_review}`; `BOQItem(id, category, description, source_object_ids, unit, quantity, rate, amount, source, editable, confidence)` | `models/project.py`, `types.ts` | round-trip | ✅ |
| 31.5 Manual rate system | `core/boq/rates.py`: editable rate table, blank/manual rates, missing-rate warnings, CSV-import placeholder (no live vendor data) | `core/boq/rates.py`(new) | `test_boq.py` (missing rate → warning, amount excluded) | ✅ |
| 31.6 BOQ Studio UI | BOQ/cost tab: material editor, tile-size editor, rate editor, category totals, missing-rate warnings, assumptions list, export | `components/workspace/boq-studio.tsx`(new), `workspace.tsx` | manual + tsc | ✅ |
| 31.7 Prompt commands | "calculate tile quantity", "change tile size to 600x600", "set tile rate to 80 per sqft", "reduce cost by 10 percent", "show missing rates", "export BOQ", "explain cost changes". Chat tools `calculate_boq`, `edit_rate` | `chat_tools.py`, `chat.py` | `test_boq_chat.py` | ✅ |
| 31.8 BOQ exports | CSV, JSON, PDF summary, schedule export; register formats | `core/exports/boq_exporter.py`(new), `api/routes/exports.py` | `test_boq_exports.py` | ✅ |
| 31.9 Tests | All BOQ tests green; recompute after plan change | — | `pytest` | ✅ |

---

## Phase 32 — Tamil Nadu Advisory Rule Pack ✅

**Goal:** source-backed TN advisories above existing NBC; advisory (not certified), versioned sources,
confidence, missing-input prompts, professional-verification flags. NBC stays intact.

**Acceptance:** "check Tamil Nadu compliance" → advisory results + missing inputs + source metadata +
confidence + verification flag; NBC still works; advisory nature explicit; 30×50 ft TN plot produces
expected pass/fail/advisory results.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 32.1 Recon | Inspect `core/compliance/{models,rules,engine}.py`, compliance route/UI, tests | — | `docs/product/phase-32-compliance-current-state.md` | ✅ |
| 32.2 Source library | `data/regulations/tamil_nadu/{sources,rules}.json`; rule fields: rule_id, title, category, required_inputs, check_logic_key, source_id, confidence, needs_professional_verification. Placeholder values + real source metadata | new data files | `test_regulation_sources.py` (schema; every rule has source + verification flag) | ✅ |
| 32.3 TN advisory engine | `core/compliance/tamil_nadu.py`: site-completeness, setback (road-width-tier), FSI, ground-coverage, parking, rainwater-harvesting (TN mandatory), stair, approval checklist; layered ABOVE NBC | `core/compliance/tamil_nadu.py`(new) | `test_tn_regulations.py` (advisory results; NBC unchanged) | ✅ |
| 32.4 Source UI | `TNAdvisorySection` in data-panel: rule source, missing-input prompts, confidence, placeholder flag, professional-verification badge, advisory_items checklist | `components/workspace/data-panel.tsx` | manual + tsc | ✅ |
| 32.5 Prompt commands | "check Tamil Nadu compliance/CMDA/DTCP rules", "check TN advisory". Chat tool `check_tn_rules`; new TN endpoint `GET /compliance/tn` | `chat_tools.py`, `chat.py`, `api/routes/compliance.py` | `test_regulation_chat.py` | ✅ |
| 32.6 Source ingestion prep | `docs/architecture/regulation-ingestion-plan.md`; ingestion steps, PDF source list, RAG roadmap, confidence levels, amendment tracking | `docs/architecture/regulation-ingestion-plan.md` | doc complete | ✅ |
| 32.7 Tests | 48 TN tests green (sources + engine + chat); 808 total passing; NBC regression green | — | `pytest` | ✅ |

---

## Phase 33 — Architect-Twin Personalization ⬜

**Goal:** output depends on budget, location, family, preferences, site, profile — same prompt ≠ same
design; explain why (simplified reasoning).

**Acceptance:** "2BHK villa" produces different output for low-budget family vs premium compact studio
preference; preferences persist locally; reasoning shows which profile/brief values influenced output.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 33.1 Recon | Inspect auth seam, settings, user_id flow, project metadata, local storage | — | `docs/product/phase-33-profile-current-state.md` | ⬜ |
| 33.2 User preference model | Local sidecar `data/users/{uid}/profile.json`: role, preferred_units, default_location, drawing_style, default_layers, preferred_room_sizes, material_preferences, output_preferences, explanation_style, common_project_types; `LocalUserProfileStore` | `core/profile/`(new), `types.ts` | `test_profile_model.py` | ⬜ |
| 33.3 Client brief model | `client_brief: ClientBrief{name, family_size, lifestyle, budget, style, vastu_pref, parking, future_expansion, special_needs, material_preference, notes}` inline | `models/project.py`, `types.ts` | round-trip | ⬜ |
| 33.4 Prompt/profile fusion | `core/profile/fusion.py` (`PromptProfileFusion` + `PersonalizedDefaultsResolver`): generation fuses prompt + brief + preferences + site + location + past edits + output mode; budget→default sizes/materials | `requirement_parser.py`, `defaults.py`, `core/profile/fusion.py`(new) | `test_profile_generation.py` (low-budget family ≠ premium compact) | ⬜ |
| 33.5 Profile + brief UI | User-preference panel; project/client-brief panel; "update profile from prompt"; "apply profile to generation" | `components/workspace/*`, settings page | manual + tsc | ⬜ |
| 33.6 Personalized reasoning | `core/reasoning.py` (`DesignReasoning`/`ChangeReasoning`/`TradeoffSummary`/`ClientFacingExplanationGenerator`): which profile/brief values influenced output, budget/location/style assumptions, tradeoffs (cost/ventilation/circulation/MEP route/regulation/drawing impact); attach to generate/change responses; `ReasoningPanel` | `core/reasoning.py`(new), `chat_tools.py`, UI | `test_profile_chat.py` | ⬜ |
| 33.7 Tests | Profile/brief/generation/chat tests green; preferences persist | — | `pytest` | ⬜ |

---

## Phase 34 — Client Change Management + Affected-Item Engine ⬜

**Goal:** professional revision workflow — changes versioned/revertible, affected drawings/items shown,
client requests tracked as tasks.

**Acceptance:** "client wants attached toilet added to bedroom" → change request created; change applied/
previewed; affected plan/MEP/BOQ/details/exports listed; version created; before/after summary; revert works.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 34.1 Recon | Inspect versions API, diff API, history UI, chat edit flow, export-stale logic | — | `docs/product/phase-34-change-current-state.md` | ⬜ |
| 34.2 Change request model | Sidecar `data/users/{uid}/projects/{id}/changes/`: `ClientChangeRequest(id, request_text, source, status, priority, affected_modules, before_version, after_version, summary, cost_impact, drawing_impact, mep_impact, detail_impact, export_impact)` | `core/changes/`(new), `types.ts` | `test_client_changes.py` | ⬜ |
| 34.3 Affected-item engine | `core/changes/affected_items.py`: compute impacts across rooms/walls/dims/furniture/MEP/BOQ/compliance/details/exports/plugins-needing-sync; reuse version diff (P19) | `core/changes/affected_items.py`(new) | `test_affected_items.py` | ⬜ |
| 34.4 Change Inbox UI | Client-changes tab: request status, affected-items list, approve/apply, reject, restore/revert, before/after summary | `components/workspace/change-inbox.tsx`(new), `workspace.tsx` | manual + tsc | ⬜ |
| 34.5 Prompt commands | "client asked to add attached toilet", "reduce budget by 10 percent", "make kitchen bigger", "move bedroom to back", "show impact of this change", "revert last client change", "list pending client changes". Chat tools `create_client_change`, `show_affected_items` | `chat_tools.py`, `chat.py` | `test_change_chat.py` | ⬜ |
| 34.6 Revision metadata | revision number/note/date, affected sheets, exports-stale status; `ExportStaleTracker` marks exports after design change | `core/changes/revisions.py`, export manifest | `test_revision_metadata.py` | ⬜ |
| 34.7 Tests | All change tests green; exports flagged stale | — | `pytest` | ⬜ |

---

## Phase 35 — 2D-to-3D Production + Render-Ready Pipeline ⬜

**Goal:** 3D/render outputs derive from accurate 2D architecture/interior/material/MEP — not random
rendering (MAKE SURE #1).

**Acceptance:** 3D reflects 2D/interior/material data; render prompts use project context (material/
style/budget/location/camera); Blender/GLTF export includes materials + furniture.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 35.1 Recon | Inspect `massing-data.ts`, `massing-viewer.tsx`, render endpoint, blender exporter, material exporter, camera presets | — | `docs/product/phase-35-3d-current-state.md` | ⬜ |
| 35.2 2D→3D mapping upgrade | Map walls/floors/openings/stairs/furniture/kitchen counters/sanitary fixtures/tile-material zones/AC units/(MEP placeholders) from validated model into massing | `features/massing/massing-data.ts` | `test_3d_mapping.py` (or TS unit) | ⬜ |
| 35.3 Interior 3D blocks | Simple blocks: bed, sofa, dining, wardrobe, kitchen counter, WC, basin, shower zone, AC indoor unit (heights by type) | `massing-data.ts`, `massing-viewer.tsx` | manual + tsc | ⬜ |
| 35.4 Material mapping | Map floor tile/wall finish/paint/glass/wood-door/counter/sanitary/ceiling-roof from `material_plan` to 3D + export materials | `massing-data.ts`, `core/exports/blender_exporter.py` | `test_blender_export_materials.py` | ⬜ |
| 35.5 Render prompt generator | `core/render/prompt_generator.py`: context-aware prompts for exterior/living/bedroom/kitchen/toilet/top/client-mood incl. material choices, style, budget, location/climate, camera preset | `core/render/prompt_generator.py`(new), `api/routes/render.py` | `test_render_prompt_generator.py` (prompt includes project context) | ⬜ |
| 35.6 Exporter updates | Blender materials+furniture; GLTF/OBJ path; render-endpoint massing-capture fallback (no key) | `blender_exporter.py`, render route | tests green | ⬜ |
| 35.7 Tests | 3D-mapping + render-prompt + blender-material tests green | — | `pytest` | ⬜ |

---

## Phase 36 — Prompt-First Toolchain Completion ⬜

**Goal:** prompt/chat is the primary control surface for all production workflows.

**Acceptance:** the full v1.1 demo runs mostly through prompts; tool calls visible as badges;
validation + versioning run after every tool action.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 36.1 Recon | Inspect chat route, tool router, command parsing, tool-call badges, chat tests | — | `docs/product/phase-36-chat-current-state.md` | ⬜ |
| 36.2 Unified prompt-command schema | Ensure prompts trigger: plan-gen, dimension edits, MEP gen/edit, detail gen, BOQ gen/edit, TN check, export, client change, version restore, affected-item explain, render-prompt gen; `PromptCommand` schema + `PromptIntentClassifier` | `core/chat_tools.py`, `chat.py` | — | ⬜ |
| 36.3 Tool router expansion | Register/audit tools: generate_mep, edit_mep_point, generate_detail, calculate_boq, edit_rate, check_tn_rules, create_client_change, show_affected_items, export_drawing, generate_render_prompt (schemas + dispatch + deterministic keyword branches) | `chat.py`, `chat_tools.py` | `test_prompt_toolchain.py` | ⬜ |
| 36.4 Tool-call UI | Upgrade chat panel: tool-call badges, action summary, warnings, affected items, undo/revert link, export links | `components/workspace/chat-panel.tsx` | manual + tsc | ⬜ |
| 36.5 Prompt demo flow | One full prompt-driven demo (TN 2BHK → MEP → toilet detail → tiles → TN advisory → export → client change → affected items) | — | scripted/manual | ⬜ |
| 36.6 Tests | `test_prompt_toolchain.py` + updated `test_chat.py` green | — | `pytest` | ⬜ |

---

## Phase 37 — Cloud/Auth Preparation for Architect-Twin Memory ⬜

**Goal:** prepare personalization + multi-user storage without breaking local-first.

**Acceptance:** local twin profile persists; Google OAuth path documented; no local-first regression.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 37.1 Recon | Inspect `ProjectStore` ABC, `LocalProjectStore`, `CloudProjectStore` stub, `get_current_user_id`, cloud/auth/database docs | — | `docs/product/phase-37-cloud-auth-current-state.md` | ⬜ |
| 37.2 Local profile store | Persist user preferences + project/client profile locally; local account-mode indicator | `core/profile/store.py`, storage | tests | ⬜ |
| 37.3 Google OAuth plan | `docs/architecture/google-oauth-plan.md`: env vars, callback flow, JWT/session, user/project ownership, local→cloud migration | doc | doc complete | ⬜ |
| 37.4 Cloud-store interface tests | Store interface + local impl + cloud-stub expected behavior + migration planning | `tests/test_cloud_store.py` | green | ⬜ |
| 37.5 Account/profile UI | Local profile page/panel, sign-in-ready placeholder, cloud-mode indicator | frontend | manual + tsc | ⬜ |

---

## Phase 38 — External MCP + Software Control Expansion ⬜

**Goal:** expose production tools to external agents (Claude Desktop/Cursor); extend plugin control.

**Acceptance:** external agent access available or clearly documented; every external call authenticates,
loads, applies, validates, versions, returns warnings; deterministic fallback preserved.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 38.1 Recon | Inspect chat route, SketchUp MCP bridge, sync endpoints, Revit/Rhino sync docs | — | `docs/product/phase-38-mcp-current-state.md` | ⬜ |
| 38.2 External MCP contract | Tools: list/get_project, generate_from_prompt, chat_edit_project, generate_mep, generate_detail, calculate_boq, check_compliance, export_project, get_sync_contract, push_sync_update, create/restore_version | `services/mcp/server.py` | contract tests | ⬜ |
| 38.3 External MCP server | Implement/document bridge for Claude Desktop, Cursor, local agents | `services/mcp/`, docs | smoke docs | ⬜ |
| 38.4 Tool safety | auth/local-token, load, apply, validate, version, return warnings, deterministic fallback | `services/mcp/` | tests | ⬜ |
| 38.5 Revit/Rhino bridge expansion | Extend/document Revit + Rhino MCP bridges; conflict handling; validation-result display | integration docs | docs | ⬜ |
| 38.6 Tests/smoke | MCP tool tests if feasible + manual setup docs + smoke checklist | — | green/docs | ⬜ |

---

## Phase 39 — Reference / Scan-to-Plan Ingestion ⬜

**Goal:** sketches/PDFs/screenshots/plans become project references (upload + manual scale + overlay
first; AI extraction documented as roadmap).

**Acceptance:** reference files upload; scale calibrates; overlay works; future extraction path documented.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 39.1 Reference asset model | Sidecar `ReferenceAsset(id, type, file_path, source, scale_status, extracted_entities, needs_review, linked_project_objects)` | `core/references/`(new), `types.ts` | `test_reference_assets.py` | ⬜ |
| 39.2 Upload + storage | Image/PDF upload route + metadata + local storage | `api/routes/references.py`(new) | tests | ⬜ |
| 39.3 Scale calibration | User marks known dimension → compute scale → align to project coords | `core/references/scale.py` | `test_scale_calibration.py` | ⬜ |
| 39.4 Overlay UI | Reference overlay on 2D plan, opacity, lock/unlock, trace/confirm | frontend | manual | ⬜ |
| 39.5 Extraction roadmap | Doc: wall detection, OCR labels, vector-PDF extraction, AI image-to-plan, Magicplan-style | doc | complete | ⬜ |
| 39.6 Tests | Upload + calibration + overlay tests green | — | `pytest` | ⬜ |

---

## Phase 40 — Feasibility / Yield Analysis (TestFit-lite) ✅

**Goal:** residential-plot feasibility/yield.

**Acceptance:** feasibility metrics generate; options compare clearly; prompt commands work.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 40.1 Feasibility model | `feasibility: Feasibility(site_area, coverage, fsi_far, buildable_area, parking_estimate, unit_count_options, warnings, assumptions)` | `models/project.py`, `types.ts` | round-trip | ✅ |
| 40.2 Feasibility engine | site area, footprint coverage, rough FSI, buildable envelope, parking assumption, missing-input list (TN setback table) | `core/feasibility/engine.py` | `test_feasibility.py` | ✅ |
| 40.3 Option generator | compact/balanced/spacious/future-expansion/rental-friendly options | `core/feasibility/options.py` | tests | ✅ |
| 40.4 Feasibility UI | metrics, option comparison, warnings, assumptions | `feasibility-section.tsx` | manual | ✅ |
| 40.5 Prompt commands | "run feasibility", "compare development options" | `chat_tools.py`, `chat.py` | `test_feasibility.py` | ✅ |
| 40.6 Tests | 57 feasibility tests green | — | `pytest` | ✅ |

---

## Phase 41 — Collaboration, Review, QA Workflows ✅

**Goal:** review/QA for small studios + students.

**Acceptance:** comments attach to project objects; QA checklist works; review export works.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 41.1 Review model | Sidecar: project comments, issue status, assigned_to, object references, review category, resolved status | `core/review/`, `types.ts` | `test_review_workflow.py` | ✅ |
| 41.2 Issues UI | CRUD issue list, QA tab, status actions, export buttons | `review-section.tsx` | manual | ✅ |
| 41.3 QA checklist engine | 10 checks: validation, rooms, dims, MEP, details, BOQ, exports | `core/review/qa_checklist.py` | tests | ✅ |
| 41.4 Review export | JSON + plain-text report with ASCII icons | `core/exports/review_exporter.py` | tests | ✅ |
| 41.5 Tests | 44 review workflow tests green | — | `pytest` | ✅ |

---

## Phase 42 — Release Hardening + Pilot Package ⬜

**Goal:** prepare v1.1 for real users / demo / pilot.

**Acceptance:** tests clean; UI presentable; demo flow works; pilot package ready; docs complete.

| Stage | Scope | Key files | Tests / docs | Status |
|---|---|---|---|---|
| 42.1 Regression + test expansion | All backend tests + tsc + frontend build + export smoke + plugin smoke; add tests for gaps | — | all green | ⬜ |
| 42.2 Performance pass | 2D SVG many-layers, MEP overlays, detail previews, BOQ calc, 3D viewer, export gen | cross-cutting | perf acceptable | ⬜ |
| 42.3 UX polish | MEP/Detail/BOQ Studios, TN Advisory, Change Inbox, Prompt Toolchain, Export Manager | frontend | CADAM-grade | ⬜ |
| 42.4 Demo projects | 2BHK TN house, 3BHK villa, student studio, small cafe, renovation/reference plan | data/fixtures | load + generate | ⬜ |
| 42.5 Pilot feedback system | Feedback button, bug/feature templates, pilot-issue export | frontend | works | ⬜ |
| 42.6 Release docs | `docs/product/{release-notes-v1.1, demo-script-v1.1, known-limitations-v1.1, pilot-package-v1.1}.md` | docs | complete | ⬜ |

---

## Operating model (per CLAUDE.md)

- Every stage fully implemented before the next.
- After each stage: **Stage Completion Format** report (Phase / Stage / Summary / Files inspected /
  Files created / Files modified / Docs updated / Tests run / Test result / How to run-test / What
  works now / Known limitations / Next recommended stage) — then ask **"Should I continue to the next
  stage?"** Do not start the next stage without confirmation.
- Backend pytest for all parser/generator/validation/export/sync/MEP/detail/BOQ/compliance logic;
  frontend = strict `tsc --noEmit` + manual preview check.
- Update this file's status column as each stage completes.

## Verification checklist (per implementation phase)

- `cd services/api && pytest` — all tests pass incl. new phase tests (baseline: 530 green).
- `cd apps/web && npx tsc --noEmit` — 0 errors; `npm run dev` — new Studio renders at localhost:3000.
- `GET http://localhost:8000/health` → `{"app":"scotch","status":"ok",...}` unchanged.
- **P29 MEP:** prompt adds layers; export shows `P-*/E-*/M-*` layers; overrides survive regen.
- **P30 details:** detail generated, linked, goes stale on source change; exports.
- **P31 BOQ:** quantity + cost recompute after plan change; missing rates flagged.
- **P32 TN:** advisory results + sources + verification flag; NBC unchanged.
- **P34 change:** affected items listed; version created; revert works; exports flagged stale.
- **P35 3D:** render prompt embeds project material/style/camera context.

## Open follow-ups (out of scope until their phase)

- Live vendor pricing / stock / quotation (after P31 manual rates prove out).
- Expert-reviewed MEP + construction-ready details (after templates prove out).
- Real TN rule ingestion / RAG (after P32 placeholder structure + source docs available).
- Cloud multi-user + collaboration (P37 seam → hosted backend later).
- AI image-to-plan extraction (P39 roadmap → later).
