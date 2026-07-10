# Phase 28.1 — Founder Requirements Map (Prompt-to-Production)

> Traceability matrix converting the founder's detailed answers into implementation-ready work.
> Every requirement is mapped to: implementation meaning · affected existing files · new files likely
> needed · data-model impact · UI impact · API impact · export impact · tests needed · external data
> needed · assigned phase. The **coverage checklist** at the end proves no requirement is dropped.
>
> Source of truth stays `ArchitectureProject` JSON. Every new module reads/writes it (inline) or a
> validated sidecar; every generate/edit/sync/export path runs `validate_project` before persist;
> Pydantic ↔ TypeScript stay 1:1; deterministic generation works with no AI key.
>
> Companion docs: [roadmap-phase-28-plus.md](roadmap-phase-28-plus.md) (stage-by-stage execution) ·
> [../architecture/external-services-and-data.md](../architecture/external-services-and-data.md)
> (service architecture / external dependencies) · [demo-script-v1.1.md](demo-script-v1.1.md).

---

## How to read this map

- **Affected files** are verified against the current codebase (Phases 0–27 complete, 530 tests green).
- **Inline vs. sidecar** follows the schema-placement principle: design/geometry data lives inside
  `ArchitectureProject` (versions with the project); workflow/account metadata lives in sidecar files
  next to `versions/` (`client_change_requests`, `reference_assets`, profile, review).
- **Phase** column is the founder's build order: 29 MEP → 30 Detail → 31 BOQ → 32 TN → 33 Twin →
  34 Change → 35 3D → 36 Prompt → 37 Cloud → 38 MCP → 39 Scan → 40 Feasibility → 41 Review → 42 Release.

---

## 1. Units and scale
- **Implementation meaning:** feet-first with metric compatibility; every element real-scale; units
  shown clearly in UI; exporters preserve real-world dimensions; dimension labels visible in 2D.
- **Affected files:** `core/models/project.py` (`units` already exists), `features/plan/floor-plan-svg.tsx`,
  all `core/exports/*`.
- **New files:** `core/units.py` (UnitConversionService), `core/architecture/dimension_engine.py`.
- **Data model:** add `DimensionEntity` + `dimensions: list[DimensionEntity]=[]`; unit-safe float fields.
- **UI:** unit display + dimension-visibility toggles on the 2D canvas.
- **API:** dimensions ride inside the project payload (no new route needed); regenerate recomputes.
- **Export:** SVG/DXF/PDF carry dimension layer; values converted on metric export.
- **Tests:** `test_units.py` (feet↔meter round-trip), dimension-engine tests.
- **External data:** none.
- **Phase:** **29.0 groundwork** (prereq for MEP/details).

## 2. Tamil Nadu first
- **Implementation meaning:** TN regulation profile as first jurisdiction layer above NBC; advisory,
  source-backed, versioned; UI shows sources + confidence; missing inputs requested.
- **Affected files:** `core/compliance/{models,rules,engine}.py`, `api/routes/compliance.py`, `data-panel.tsx`.
- **New files:** `data/regulations/tamil_nadu/{sources,rules,amendments}.json`, `core/compliance/tamil_nadu.py`.
- **Data model:** `RegulationProfile`, `TamilNaduRuleSource`, advisory `RuleResult` extensions.
- **UI:** TN advisory section with source/citation display + verification flag.
- **API:** extend `GET /projects/{id}/compliance` (jurisdiction param) or add TN section.
- **Export:** compliance/advisory PDF (later); part of review report.
- **Tests:** `test_tn_regulations.py`, `test_regulation_sources.py`, `test_regulation_chat.py`.
- **External data:** **TN Combined Development & Building Rules + amendments** (see open question 1).
- **Phase:** **32**.

## 3. Default dimensions and wall thickness
- **Implementation meaning:** use prompt/client values when given; else practical defaults that depend
  on project type, budget, location, profile; defaults documented + editable.
- **Affected files:** `core/architecture/defaults.py`, `requirement_parser.py`, `floorplan_generator.py`.
- **New files:** `core/profile/fusion.py` (PersonalizedDefaultsResolver), defaults doc section.
- **Data model:** `client_brief` + user profile feed the resolver.
- **UI:** brief/profile panels; defaults shown as editable.
- **API:** generation reads brief/profile; no new route (profile via sidecar store).
- **Export:** n/a.
- **Tests:** `test_profile_generation.py` (budget changes defaults).
- **External data:** none.
- **Phase:** **33** (resolver), seeded in **29.0** (defaults documentation).

## 4. 2D creation and interior integration
- **Implementation meaning:** 2D working drawing is the core surface with layers (architecture,
  furniture, interiors, MEP, dimensions, materials, details); interiors placed in 2D first; 3D and
  render derive from the validated 2D/project model. **(MAKE SURE #1.)**
- **Affected files:** `features/plan/floor-plan-svg.tsx`, `features/massing/massing-data.ts`, `api/routes/render.py`.
- **New files:** Studio components (MEP/Detail/BOQ), `core/render/prompt_generator.py`.
- **Data model:** layered entities (mep_plan, dimensions, detail_drawings, material_plan) all inline.
- **UI:** layered 2D renderer + layer toggles; 2D→3D mapper; render-prompt generator.
- **API:** render route consumes project context.
- **Export:** layered SVG/DXF/PDF; render-ready Blender/GLTF.
- **Tests:** `test_3d_mapping.py`, `test_render_prompt_generator.py`.
- **External data:** optional render-image AI (SD-compatible).
- **Phase:** spans **29 (layers) + 30 (details) + 35 (2D→3D/render)**.

## 5. Stairs
- **Implementation meaning:** stairs in core schema (dims, orientation, start/end level, width,
  riser/tread, warnings); 2D symbol; 3D massing; intelligence/compliance warns on weak assumptions.
- **Affected files:** `floorplan_generator.py` (`_stair_spec`, `_STAIR_W/_D` exist), `regenerate.py`,
  `floor-plan-svg.tsx`, `massing-data.ts`, `core/compliance/*`.
- **New files:** `core/architecture/stairs.py` (StairDefaults/placement) if needed.
- **Data model:** explicit `stairs: list[Stair]` (extend existing stair handling).
- **UI:** stair symbol in 2D; basic stair massing in 3D.
- **API:** part of project payload.
- **Export:** stairs in SVG/DXF/IFC/3D exports.
- **Tests:** stair placement + symbol + compliance tests (in 29.0 + 32).
- **External data:** none.
- **Phase:** **29.0 groundwork** (+ compliance check in 32, 3D in 35).

## 6. All relevant dimensions
- **Implementation meaning:** room/external/wall/opening/stair/major-furniture-clearance dims; show/hide
  per type; dimension layers export cleanly.
- **Affected files:** `floor-plan-svg.tsx`, `core/exports/{svg,dxf,sheet_pdf}_exporter.py`.
- **New files:** `core/architecture/dimension_engine.py` (AutoDimensionEngine).
- **Data model:** `DimensionEntity` + `dimensions` list; visibility flags.
- **UI:** DimensionVisibilityControls.
- **API:** dimensions in project payload.
- **Export:** dimension layer in DXF/SVG/PDF.
- **Tests:** auto-dimension tests.
- **External data:** none.
- **Phase:** **29.0 groundwork**.

## 7. Editable options
- **Implementation meaning:** nothing static — rooms, dimensions, layers, MEP, materials, rates,
  details, client specs editable; prompt + manual edits both update the project; changes create versions.
- **Affected files:** `regenerate.py` (`apply_changes`/`ParameterChange`), `chat_tools.py`,
  versions machinery (`api/routes/versions.py`), workspace state.
- **New files:** none core (extend change keys + chat tools per module).
- **Data model:** existing parameter/version models extend additively.
- **UI:** every Studio has editable tables + on-canvas edit + prompt edit.
- **API:** regenerate/PATCH already auto-snapshot versions.
- **Export:** edits flow to exports (marked stale after change — req 18/19).
- **Tests:** per-module chat + edit tests.
- **External data:** none.
- **Phase:** cross-cutting (**29–36**); editability is a property of every phase.

## 8. MEP included
- **Implementation meaning:** plumbing/wiring/electrical/lighting/AC as separate, editable, exportable
  2D layers; conceptual/semi-working level; prompt-controlled.
- **Affected files:** `models/project.py`, `validator.py`, `floorplan_generator.py`, `chat_tools.py`,
  `chat.py`, `core/exports/{svg,dxf}_exporter.py`, `preview-panel.tsx`, `workspace.tsx`.
- **New files:** `core/architecture/mep_generator.py`, `data/mep_templates/*.json`,
  `components/workspace/mep-studio.tsx`.
- **Data model:** `mep_plan: MEPPlan` (plumbing/electrical/lighting/ac) with `ServicePoint`/`ServiceRoute`/
  `Fixture`/`Switch`/`Socket`/`LightPoint`/`ACUnit`; inline.
- **UI:** MEP Studio with layer toggles + editable point list + route overlay + warnings/confidence.
- **API:** `generate_mep` / `edit_mep_point` via chat tools (no separate REST route required; reuse PATCH).
- **Export:** named layers `P-PIPE/P-FIXTURE/E-LIGHT/E-SWITCH/E-SOCKET/E-ROUTE/M-AC`.
- **Tests:** `test_mep_model.py`, `test_mep_generation.py`, `test_mep_chat.py`, `test_mep_exports.py`.
- **External data:** in-repo MEP template JSON (no external API).
- **Phase:** **29**.

## 9. MEP logic should think like an architect
- **Implementation meaning:** infer needs from room types + prompt (toilet/kitchen/utility/balcony/shaft/
  AC rooms/appliances drive placement); respect prompt overrides; show confidence + needs_review.
- **Affected files:** `mep_generator.py`.
- **New files:** `MEPIntentResolver`, `RoomTypeToServiceNeeds` map (in mep_generator), `MEPConfidenceScorer`.
- **Data model:** `confidence`, `needs_review`, `user_override` on `ServicePoint`.
- **UI:** confidence/review badges; override indicator.
- **API:** regenerate updates MEP or marks stale; overrides preserved.
- **Export:** confidence not exported to CAD but shown in app + review report.
- **Tests:** room-type→service mapping; override preservation; stale-on-room-change.
- **External data:** none.
- **Phase:** **29.4**.

## 10. Wet area grouping
- **Implementation meaning:** advisory only — suggest shorter pipe runs / wet-wall grouping; allow
  non-grouped layouts; warnings explain tradeoffs. Never force.
- **Affected files:** `mep_generator.py`.
- **New files:** `WetAreaAnalyzer`, `PlumbingRouteLengthEstimator` (in mep_generator).
- **Data model:** advisory warnings + override tracking.
- **UI:** suggestion in MEP warnings panel.
- **API:** advisory in project warnings.
- **Export:** n/a (advisory).
- **Tests:** far-apart wet areas → warn but not relayout.
- **External data:** none.
- **Phase:** **29.4**.

## 11. Wiring conceptual for now
- **Implementation meaning:** electrical routing not engineering-complete; conceptual switch/socket/light
  points + routing; needs_review flags; export layers; future-ready for circuits.
- **Affected files:** `mep_generator.py`, exporters.
- **New files:** conceptual electrical layer logic (in mep_generator).
- **Data model:** `needs_review=True` on electrical points by default.
- **UI:** "conceptual / review needed" labels.
- **API:** part of mep_plan.
- **Export:** `E-*` layers.
- **Tests:** electrical points marked conceptual.
- **External data:** none.
- **Phase:** **29.4**.

## 12. MEP UI as separate editable 2D layer window
- **Implementation meaning:** MEP Studio / Layer Studio tab; toggle architecture/plumbing/electrical/
  lighting/AC/furniture/dimensions/materials; editable point tables; selected-object properties; prompt
  panel targets active layer.
- **Affected files:** `workspace.tsx`, `preview-panel.tsx`.
- **New files:** `components/workspace/mep-studio.tsx`, `LayerTogglePanel`, `ServicePointEditor`,
  `ServiceRouteOverlay`.
- **Data model:** n/a (reads mep_plan).
- **UI:** the Studio itself.
- **API:** n/a.
- **Export:** n/a.
- **Tests:** manual + tsc; chat targets active layer.
- **External data:** none.
- **Phase:** **29.6**.

## 13. Regulations advisory with sources
- **Implementation meaning:** TN source library (URL/path, version date, category, confidence); advisory
  checks state missing inputs; source display visible; "needs professional verification" where apt.
- **Affected files:** `core/compliance/*`, `data-panel.tsx`.
- **New files:** `data/regulations/tamil_nadu/*`, `core/compliance/tamil_nadu.py`, `SourceDisplay` component.
- **Data model:** `TamilNaduRuleSource`, `AdvisoryRuleCheck`, `RuleResult` with source + confidence.
- **UI:** RegulationPanel shows rule, advisory result, missing input, source, date, confidence.
- **API:** compliance endpoint returns source metadata.
- **Export:** advisory in review/compliance report.
- **Tests:** `test_regulation_sources.py` (every rule has source + verification flag).
- **External data:** TN rule documents (open question 1).
- **Phase:** **32**.

## 14. Materials, tiles, BOQ, editable rates
- **Implementation meaning:** main materials (floor/wall tile, paint, doors, windows, sanitary, plumbing,
  electrical fixtures, kitchen counter); editable selections + rates; quantities trace to rooms/objects;
  BOQ updates after changes; vendor stock future.
- **Affected files:** `core/intelligence/area_calculator.py`, program table, schedule exports, export manager.
- **New files:** `core/boq/{quantity_engine,rates}.py`, `core/exports/boq_exporter.py`,
  `components/workspace/boq-studio.tsx`.
- **Data model:** `material_plan: MaterialPlan`, `cost_plan: CostPlan`, `BOQItem`, `TileSpec`, `RoomFinish`.
- **UI:** BOQ Studio (material/tile/rate editors, totals, missing-rate warnings, assumptions).
- **API:** `calculate_boq` / `edit_rate` via chat tools.
- **Export:** CSV/JSON/PDF BOQ.
- **Tests:** `test_quantity_engine.py`, `test_boq.py`, `test_boq_chat.py`, `test_boq_exports.py`.
- **External data:** manual rates first (no live vendor API).
- **Phase:** **31**.

## 15. Working drawing first
- **Implementation meaning:** upgrade 2D from concept to working-drawing style — line weights,
  dimensions, room labels, area tags, door/window tags, furniture, section/elevation markers,
  schedules, title block/sheet, layer names; export-ready.
- **Affected files:** `floor-plan-svg.tsx`, `core/exports/{svg,sheet_svg,sheet_pdf}_exporter.py`,
  `core/exports/schedule_exporter.py`.
- **New files:** `DrawingStyleConfig`, `AnnotationEngine`, working-drawing renderer upgrades.
- **Data model:** dimensions + tags + schedules (mostly derived).
- **UI:** working-drawing-grade 2D canvas.
- **API:** n/a (renderer + exporters).
- **Export:** title block, schedules, named layers in SVG/DXF/PDF.
- **Tests:** annotation/schedule tests; sheet exporter tests.
- **External data:** none.
- **Phase:** **29.0 groundwork + 30 (details) + 42 (polish)**.

## 16. Furniture included
- **Implementation meaning:** furniture by room type + client brief; dims/x/y/rotation/room_id +
  clearance warnings; 2D + basic 3D. *(Furniture model + placer already exist from Phase 26 — extend.)*
- **Affected files:** `core/architecture/furniture_defaults.py`, `furniture_placer.py`,
  `floor-plan-svg.tsx`, `massing-data.ts`.
- **New files:** none (extend existing; brief-aware placement).
- **Data model:** `FurnitureItem` exists; brief influences selection.
- **UI:** furniture layer toggle (exists); brief-aware.
- **API:** part of project.
- **Export:** `S-FURNITURE` (SketchUp), `Scotch_Furniture` (Blender) exist.
- **Tests:** brief-aware furniture coverage (extend `test_furniture.py`).
- **External data:** none.
- **Phase:** **33 (brief-aware) + 35 (3D blocks)** — base already shipped P26.

## 17. Door/window schedule included
- **Implementation meaning:** doors/windows have type, size, room/wall relation, tag, sill/lintel
  placeholders; schedule updates on opening change; export CSV/PDF/sheet; detail drawings link to schedule.
- **Affected files:** `core/exports/schedule_exporter.py`, `floor-plan-svg.tsx` (tags).
- **New files:** `OpeningScheduleGenerator`, `DoorWindowTagger`, `DoorWindowDetailLinker` (in detail pkg).
- **Data model:** tag + sill/lintel fields on Door/Window.
- **UI:** schedule table; tagged openings.
- **API:** schedule export endpoints exist (`schedule_json/csv`); extend.
- **Export:** door/window schedule CSV/PDF + sheet section.
- **Tests:** schedule generation + tagging tests.
- **External data:** none.
- **Phase:** **30** (linked to details) — base schedule exists P13.

## 18. Export-ready 2D plans
- **Implementation meaning:** SVG/DXF/PDF with clean layers; MEP/dimensions/furniture/details/BOQ/
  schedules exportable; exports tied to version; stale exports marked after changes.
- **Affected files:** `api/routes/exports.py`, all `core/exports/*`, export manifest.
- **New files:** `ExportStaleTracker` (in `core/changes/`).
- **Data model:** export manifest gains version + stale status.
- **UI:** Export Manager with stale indicators.
- **API:** export routes register new formats.
- **Export:** layered, versioned, stale-aware.
- **Tests:** export-stale tests (`test_revision_metadata.py`), per-format layer tests.
- **External data:** none.
- **Phase:** per-module exports (**29/30/31**) + stale tracking in **34**.

## 19. Change management and architect twin
- **Implementation meaning:** edits versioned/revertible; affected drawings/items shown; client change
  requests stored as tasks; software becomes personalized architect twin; simple prompt explanations;
  profile memory influences future outputs.
- **Affected files:** `api/routes/versions.py`, version diff, history UI, `chat_tools.py`.
- **New files:** `core/changes/{__init__,affected_items,revisions}.py`, `components/workspace/change-inbox.tsx`,
  `ArchitectTwinProfile` (in `core/profile/`).
- **Data model:** `client_change_requests` (sidecar); revision metadata; profile (sidecar).
- **UI:** Change Inbox; affected-items list; before/after summary.
- **API:** `create_client_change`, `show_affected_items` chat tools; reuse versions API.
- **Export:** exports flagged stale on change.
- **Tests:** `test_client_changes.py`, `test_affected_items.py`, `test_revision_metadata.py`, `test_change_chat.py`.
- **External data:** none (cloud later for multi-device twin — phase 37).
- **Phase:** **34** (+ profile in **33**).

## 20. Client brief and user profile
- **Implementation meaning:** output depends on budget/location/family/preferences/site/profile; same
  prompt ≠ same design; fuse prompt + brief + site + budget + family + location + style prefs + past
  edits; explain why output differs.
- **Affected files:** `requirement_parser.py`, `defaults.py`, generator.
- **New files:** `ClientBrief` model, `UserPreference` model, `core/profile/fusion.py`, `ReasoningPanel`.
- **Data model:** `client_brief` inline; user profile sidecar.
- **UI:** brief + preference panels; reasoning panel.
- **API:** generation reads both; profile via sidecar store.
- **Export:** n/a.
- **Tests:** `test_client_brief.py`, `test_profile_generation.py`.
- **External data:** none.
- **Phase:** **33**.

## 21. Google sign-in later
- **Implementation meaning:** keep current auth seam; build profile system local-first; prepare Google
  OAuth; cloud user storage after production modules.
- **Affected files:** `core/auth/context.py`, `core/storage/*`.
- **New files:** `LocalUserProfileStore`, `docs/architecture/google-oauth-plan.md`.
- **Data model:** AuthReadyUserModel; local profile.
- **UI:** sign-in-ready placeholder + cloud-mode indicator.
- **API:** unchanged seam (`get_current_user_id`).
- **Export:** n/a.
- **Tests:** `test_cloud_store.py`, profile-store tests.
- **External data:** Google OAuth credentials (later).
- **Phase:** **37**.

## 22. BOQ main materials first
- **Implementation meaning:** core quantities first (not vendor real-time); manual rates first; CSV
  import later; vendor stock/quotation later.
- **Affected files:** `core/boq/*`.
- **New files:** `EditableRateTable` (in `core/boq/rates.py`).
- **Data model:** `cost_plan` with editable rates + missing-rate warnings.
- **UI:** rate inputs; missing-rate warnings.
- **API:** `edit_rate` chat tool.
- **Export:** BOQ export.
- **Tests:** rate edit + missing-rate tests.
- **External data:** manual rates; CSV import placeholder.
- **Phase:** **31** (overlaps req 14).

## 23. Detail drawings need templates/data
- **Implementation meaning:** toilet, kitchen, door/window, wall section, electrical/plumbing details;
  start schematic → toward construction-ready; template KB (required inputs, geometry, annotations,
  dimensions, confidence, source notes, needs_review); details linked to objects; stale on source change.
- **Affected files:** sheet/SVG/PDF exporters, schedule.
- **New files:** `data/detail_templates/*.json`, `core/architecture/detail/*.py`,
  `core/exports/detail_exporter.py`, `components/workspace/detail-studio.tsx`.
- **Data model:** `detail_drawings: list[DetailDrawing]` inline (geometry primitives + stale_status).
- **UI:** Detail Studio (list, preview, source link, annotation/dimension editors, stale warning).
- **API:** `generate_detail` chat tool.
- **Export:** detail SVG/PDF/DXF + sheet bundle.
- **Tests:** `test_detail_templates.py`, `test_detail_generation.py`, `test_detail_chat.py`, `test_detail_exports.py`.
- **External data:** in-repo detail template JSON (expert-reviewed later).
- **Phase:** **30**.

## 24. Simplified design reasoning
- **Implementation meaning:** reasoning on every major generation/change; user-friendly summary +
  technical notes; explain tradeoffs (cost, ventilation, circulation, MEP route length, regulation
  advisory, drawing impact).
- **Affected files:** `chat_tools.py`, generate/regenerate responses, UI.
- **New files:** `core/reasoning.py` (DesignReasoning/ChangeReasoning/TradeoffSummary),
  `ReasoningPanel`, `ClientFacingExplanationGenerator`.
- **Data model:** reasoning attached to responses (not persisted to core model unless desired).
- **UI:** ReasoningPanel after generation/change.
- **API:** reasoning in generate/change/chat responses.
- **Export:** reasoning in review report (optional).
- **Tests:** reasoning presence in chat/generation responses.
- **External data:** AI improves phrasing; deterministic templated reasoning as fallback.
- **Phase:** **33** (+ surfaced in **34/36**).

## 25. Prompt-first execution
- **Implementation meaning:** prompt/chat is primary command path; UI supports prompt outcomes;
  intents cover generate/edit-dims/add-MEP/BOQ/detail/TN-check/export/client-change/explain-affected/
  revert; tool-call badges show what executed.
- **Affected files:** `api/routes/chat.py`, `chat_tools.py`, `components/workspace/chat-panel.tsx`.
- **New files:** `PromptIntentClassifier`, `ToolCommandRouter`, `PromptCommand` schema (in chat layer).
- **Data model:** n/a (orchestration).
- **UI:** ToolCallBadges + affected-items in chat panel.
- **API:** expanded tool schemas + dispatch + deterministic keyword branches.
- **Export:** export tools callable via prompt.
- **Tests:** `test_prompt_toolchain.py`, updated `test_chat.py`.
- **External data:** AI for best intent understanding; deterministic keyword fallback always.
- **Phase:** **36** (each tool added incrementally in 29–35; 36 unifies/audits).

---

## MAKE-SURE directives (explicit, not dropped)

### MAKE SURE #1 — 2D-first → complete 3D render (not random rendering)
Users design 2D properly first; that validated 2D/interior/material data drives the 3D + render
pipeline. Render outputs are derived from the model, never disconnected. → **Phases 30 (details) + 35
(2D→3D mapping, material mapping, context-aware render-prompt generator).** Render-prompt generator
pulls material choices/style/budget/location/camera from the project, not arbitrary prompts.

### MAKE SURE #2 — Service architecture accuracy / external dependencies
Full answer in [../architecture/external-services-and-data.md](../architecture/external-services-and-data.md).
**Net:** nothing external is *blocking*. Only real external *content* dependency = Tamil Nadu rule
source material (handled via ingestion-ready placeholders + verification flags). AI keys (Anthropic/
OpenAI-compatible) and render-image keys (SD-compatible) are *optional enhancers* — deterministic
fallback always works. Everything else is in-repo deterministic templates (MEP, details, materials) or
existing dev libraries (`ezdxf`, `reportlab`, `Pillow`, `ifcopenshell`).

---

## External data & services summary

| Need | External? | Required input | Blocking? | Phase |
|---|---|---|---|---|
| AI provider (intent/reasoning/repair) | API, optional | `ANTHROPIC_API_KEY` / OpenAI-compatible key | No (deterministic fallback) | cross-cutting |
| Tamil Nadu regulations | Content, not API | TN CDBR + amendments (PDF/text) + source metadata | No (placeholders + verification flag) | 32 |
| MEP templates | In-repo JSON | authored deterministically | No | 29 |
| Detail templates | In-repo JSON | authored deterministically | No | 30 |
| Material & rate data | In-repo + manual | manual editable rates; CSV import later | No | 31 |
| Export libraries | Dev deps (present) | reuse `ezdxf`/`reportlab`/`Pillow`/`ifcopenshell` | No | 29–31 |
| Auth/cloud (twin memory) | External later | Google OAuth + DB + object storage | No (local-first now) | 37 |
| Render image AI | API, optional | SD-compatible img2img key | No (massing-capture fallback) | 35 |
| Scan-to-plan extraction | External/AI later | OCR / vector-PDF / image-to-plan | No (manual scale first) | 39 |

---

## Coverage checklist (proof nothing is dropped)

| # | Requirement | Phase(s) | Status |
|---|---|---|---|
| 1 | Units and scale | 29.0 | ✅ mapped |
| 2 | Tamil Nadu first | 32 | ✅ mapped |
| 3 | Default dimensions/wall thickness | 29.0 + 33 | ✅ mapped |
| 4 | 2D creation + interior integration | 29 + 30 + 35 | ✅ mapped |
| 5 | Stairs | 29.0 (+32, +35) | ✅ mapped |
| 6 | All relevant dimensions | 29.0 | ✅ mapped |
| 7 | Editable options | 29–36 (cross-cutting) | ✅ mapped |
| 8 | MEP included | 29 | ✅ mapped |
| 9 | MEP thinks like an architect | 29.4 | ✅ mapped |
| 10 | Wet area grouping (advisory) | 29.4 | ✅ mapped |
| 11 | Wiring conceptual | 29.4 | ✅ mapped |
| 12 | MEP UI as separate layer window | 29.6 | ✅ mapped |
| 13 | Regulations advisory with sources | 32 | ✅ mapped |
| 14 | Materials/tiles/BOQ/editable rates | 31 | ✅ mapped |
| 15 | Working drawing first | 29.0 + 30 + 42 | ✅ mapped |
| 16 | Furniture included | 33 + 35 (base P26) | ✅ mapped |
| 17 | Door/window schedule | 30 (base P13) | ✅ mapped |
| 18 | Export-ready 2D plans | 29/30/31 + 34 | ✅ mapped |
| 19 | Change mgmt + architect twin | 34 (+33) | ✅ mapped |
| 20 | Client brief + user profile | 33 | ✅ mapped |
| 21 | Google sign-in later | 37 | ✅ mapped |
| 22 | BOQ main materials first | 31 | ✅ mapped |
| 23 | Detail drawings templates/data | 30 | ✅ mapped |
| 24 | Simplified design reasoning | 33 (+34/36) | ✅ mapped |
| 25 | Prompt-first execution | 36 (incremental 29–35) | ✅ mapped |
| M1 | 2D-first → render-ready | 30 + 35 | ✅ mapped |
| M2 | Service-architecture accuracy | external-services doc | ✅ mapped |

**All 25 requirements + 2 MAKE-SURE directives are mapped to phases. None dropped.**

---

## Open questions & assumptions (carried from the approved plan)

1. **TN rule sources (P32)** — *Assumption:* official TN CDBR text not on hand yet → build ingestion-ready
   library with placeholder values + real source-metadata fields + `needs_professional_verification`.
   **Direct answer welcome.**
2. **Currency/locale (P31)** — *Assumption:* INR (₹), feet-first with metric toggle, rates per sqft.
3. **AI keys (cross-cutting)** — *Assumption:* deterministic-first build/test; AI optional, mocked in tests.
4. **MEP depth (P29)** — *Assumption:* conceptual/semi-working only; not engineering-certified.
5. **Detail geometry (P30)** — *Assumption:* structured primitives (editable/exportable), not opaque SVG.
6. **Schema placement** — design/geometry inline; workflow/account metadata in sidecars.
7. **Stairs (P29.0)** — extend existing `_stair_spec`, don't rebuild.
8. **Demo jurisdiction** — TN, 30×50 ft east-facing, budget family-of-4 2BHK (per founder's 20-step demo).
