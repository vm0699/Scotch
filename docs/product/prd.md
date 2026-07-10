# Scotch — Product Requirement Document (PRD)

Phase 0 Stage 0.2 deliverable. Sources: [brief.md](brief.md) + [questionnaire.md](questionnaire.md) (locked decisions).

## Product Summary

Scotch is an AI-native architecture design platform — "CADAM for architecture." Users type a natural-language brief ("Design a 2BHK apartment on a 30x50 ft east-facing site…") and receive an editable architectural design: a validated universal model, an architectural-standard 2D floor plan, 3D massing, editable parameters (panel + on-canvas, CADAM-style), and exports that feed professional workflows.

## Core User

Architects in small studios (primary), architecture students, and interior designers — people who think in plans, schedules, and tool pipelines, and will judge the product by drawing quality and export usefulness.

## MVP Scope (Phases 1–9)

- Local web app: Next.js frontend + FastAPI backend, no auth, local filesystem storage.
- CADAM-like 3-panel workspace (prompt | 2D/3D canvas | parameters, schedule, exports, warnings).
- Universal **ArchitectureProject JSON** as the single source of truth, with reusable backend validation.
- Deterministic prompt → floor plan generation (residential + small cafe), feet units, smart defaults + assumption warnings.
- Editable parameters with live preview, room selection, on-canvas inline editing, and regeneration.
- Exports: JSON, layered SVG, PNG, DXF.
- 3D massing viewer (R3F) synced to parameters; GLTF preparation.
- AI provider abstraction (deterministic / Anthropic / OpenAI-compatible) with validation, repair, and fallback.

## Later Scope (Phases 10–20)

Design options (compact/balanced/spacious) · presentation sheets (SVG/PDF, Illustrator-friendly) · architecture intelligence (spatial checks, area calcs, optional vastu, room schedule export) · SketchUp + Revit plugins (priority), then Blender + Rhino/Grasshopper · rendering workflow prep (Lumion, D5, Enscape, V-Ray, Blender) · cloud/auth readiness · version history · final QA, polish, and demo.

## Software Support Strategy

1. **Phase 7:** DXF gives AutoCAD users a workflow immediately.
2. **Phase 11:** script exporters (SketchUp Ruby, Blender Python) — value without installing plugins; Revit/Rhino strategies documented.
3. **Phases 14–16:** SketchUp extension and Revit C# add-in PoC (priority pair), then Rhino/Grasshopper.
4. **Phase 17:** render-engine workflows ride on clean, named, material-tagged 3D exports.
5. **Phase 12:** Adobe suite served by layered SVG, PNG assets, and PDF packages.

## First Workflow (acceptance benchmark)

Create project → type 2BHK prompt → generate → inspect plan/schedule/warnings → click a room and edit dimensions (panel + inline popover) → regenerate → view 3D massing → export SVG/JSON/PNG/DXF.

## Technical Stack

See questionnaire heading 20. Notable choices: Pydantic v2 models mirrored by TypeScript types; SVG (not canvas) for 2D so exports and previews share geometry logic; React Three Fiber for 3D; `ezdxf` for DXF; local filesystem storage with a `local-user` namespace for future cloud auth.

## Data Model Strategy

`ArchitectureProject` (id, name, units, site, building, parameters, rooms, walls, doors, windows, materials, notes, warnings) plus `ExportManifest`. One validator module enforces invariants (positive dimensions, rooms inside site, unique IDs, valid level refs) and emits warnings; generation, editing, and exports all call it. Versions/options extend the model additively in Phases 10 and 19.

## Export Strategy

Every export adapter consumes ArchitectureProject only (never renderer internals). SVG is the canonical 2D geometry; PNG rasterizes it; DXF maps geometry to A-* layers; scripts (Ruby/Python) and GLTF derive from the same model. Exports are written under each project's `exports/` folder and tracked in the manifest.

## Plugin Strategy

Scripts before plugins (zero-install value first), plugins read the same JSON the scripts do, and each plugin ships with mapping documentation (Scotch entities → tool entities) plus a future-sync strategy.

## UI Direction

CADAM/adam.new-inspired premium white interface (see questionnaire heading 19). The signature interaction is in-screen parameter editing after generation: select on canvas, edit inline, see the plan update live.

## Prompt-to-Production Direction (v1.1, Phases 28–42)

After v1.0-beta (Phases 0–27 complete), the product direction extends from "text-to-design" to a
**prompt-to-production architecture workflow system**: plain-English prompts produce editable
*production* outputs — working-drawing dimensions (real-scale, metric-compatible), furniture/interior
layout, MEP layers (plumbing/electrical/lighting/AC), detail drawings (toilet/kitchen/door-window/wall-
section/tile), material/tile/BOQ/cost, and **Tamil Nadu** source-backed advisories above NBC — plus
client-change management with affected-item tracking, and a 2D-first → render-ready 3D pipeline.

**Module priorities (founder build order):** 29 MEP → 30 Details → 31 BOQ → 32 Tamil Nadu advisory →
33 architect-twin personalization → 34 client-change mgmt → 35 2D-to-3D/render → 36 prompt-first
toolchain → 37 cloud/auth → 38 external MCP → 39 scan-to-plan → 40 feasibility → 41 review/QA →
42 release hardening (v1.1).

**Invariants carried forward:** `ArchitectureProject` JSON is the single source of truth (new design/
geometry data inline, workflow/account metadata in sidecars); every generate/edit/sync/export path runs
the validator before persist; Pydantic ↔ TypeScript stay 1:1; deterministic generation always works
with no AI key; conceptual outputs (MEP, details, advisories) carry `confidence`/`needs_review` (and
`needs_professional_verification` for regulations); the v1.1 demo is fully runnable offline.

**External dependencies:** nothing external is blocking — only the Tamil Nadu rule source material is a
real external *content* dependency (handled via ingestion-ready placeholders + verification flags); AI
and render-image keys are optional enhancers. Full analysis:
[../architecture/external-services-and-data.md](../architecture/external-services-and-data.md).

**Known limitations (v1.1 target):** MEP is conceptual/semi-working (not engineering-certified);
details start schematic and improve toward construction-ready; BOQ uses manual rates (no live vendor
pricing); TN advisories are advisory and require professional verification; scan-to-plan is upload +
manual scale only (AI extraction is a documented roadmap); cloud/multi-user is prepared behind seams,
not wired.

See the full staged plan: [roadmap-phase-28-plus.md](roadmap-phase-28-plus.md) ·
[phase-28-founder-requirements-map.md](phase-28-founder-requirements-map.md) ·
[demo-script-v1.1.md](demo-script-v1.1.md).

## Assumptions

- Single local user; no concurrency or auth until Phase 18.
- Rectangular sites and predominantly rectangular room layouts for MVP generation.
- Feet as default units; unit flexibility carried in the data model.
- Node 18+/Python 3.10+ available on the dev machine.
- Revit/SketchUp live testing depends on those tools being installed; code + docs are deliverable regardless.

## Risks

- **Layout quality** is the product's make-or-break: rule-based generation must produce plausible plans, not just non-overlapping rectangles. Mitigation: zoning rules, defaults library, warnings, and the options system (Phase 10).
- **DXF/Revit fidelity** can absorb unlimited effort. Mitigation: explicitly scoped "basic" exports with documented limitations per phase.
- **AI output instability.** Mitigation: strict validation, schema repair, deterministic fallback — AI never blocks the core flow.
- **Scope creep across 20 phases.** Mitigation: hard stage gates with acceptance criteria and per-stage confirmation.

## Dependencies

FastAPI, Pydantic v2, uvicorn, pytest, httpx, ezdxf (Phase 7), Pillow or resvg for PNG (Phase 7), Next.js, Tailwind, shadcn/ui, three/@react-three/fiber/@react-three/drei (Phase 8), Anthropic & OpenAI SDKs (Phase 9, optional at runtime).
