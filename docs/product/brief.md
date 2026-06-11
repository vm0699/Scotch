# Scotch — Product Brief

## What Scotch Is

Scotch is an **AI-native architecture design platform** — "CADAM for architecture." It lets architects, architecture students, interior designers, and small studios type natural-language prompts and generate **editable architectural designs**.

Inspiration: CADAM / adam.new / cadxstudio-style AI CAD tools (https://github.com/Adam-CAD/CADAM), applied specifically to architecture workflows. Scotch begins with its own strong CADAM-like interface, then expands into exports and integrations for professional tools.

**Tagline:** Text-to-design for architecture.

## Core Product Flow

```
Text prompt
→ architecture requirement understanding
→ universal architecture model (ArchitectureProject JSON — the source of truth)
→ editable parameters
→ 2D floor plan preview
→ 3D massing/model preview
→ exports
→ software integrations/plugins
```

## Core System Pipeline

```
User prompt
→ requirement parser
→ universal ArchitectureProject JSON
→ validator
→ editable parameter model
→ 2D renderer (SVG)
→ 3D renderer (React Three Fiber)
→ export adapters
→ software integrations/plugins
```

## Target Professional Tools

| Workflow | Tools |
|---|---|
| Drafting | AutoCAD (via DXF), Revit |
| Modelling | SketchUp, Revit, Rhino, Blender |
| Rendering | Lumion, D5, Enscape, V-Ray, Blender |
| Sheet presentation | Photoshop, Illustrator, InDesign |

Integration priority (locked in Phase 0): **SketchUp and Revit first**, then Blender, then Rhino/Grasshopper. AutoCAD is served via DXF export from Phase 7.

## Technology Stack

**Frontend:** Next.js (App Router), React, TypeScript, Tailwind CSS, shadcn/ui, SVG renderer for 2D floor plans, React Three Fiber for 3D massing.

**Backend:** Python, FastAPI, Pydantic v2, local filesystem storage (optional SQLite later for indexing).

**AI:** provider abstraction from day one — deterministic rule-based generator first; Anthropic and OpenAI-compatible providers behind one interface; AI output as structured JSON, always backend-validated (with schema repair and deterministic fallback) before rendering/exporting.

**Desktop/mobile direction:** web-first core editor; Tauri wrapper later for desktop; Flutter considered later for a mobile viewer / client presentation mode / companion dashboard.

## Complete Product Vision (long-term feature list)

1. Text-to-floor-plan
2. Text-to-3D architecture massing
3. Editable parameters
4. Parameter-based regeneration
5. Multiple design options
6. Room schedule
7. Area calculations
8. Material suggestions
9. Basic architecture intelligence
10. Optional vastu suggestions
11. Basic building/site warnings
12. 2D drawing export
13. 3D model export
14. Presentation sheet export
15. AutoCAD workflow through DXF
16. SketchUp integration
17. Revit integration
18. Rhino/Grasshopper integration
19. Blender automation
20. Rendering workflow preparation for Lumion, D5, Enscape, V-Ray, Blender
21. Illustrator/Photoshop/InDesign-friendly sheet export
22. Local project storage
23. Cloud-ready architecture later
24. Version history
25. Team collaboration later

## Final Product Completion Target

**Core:** CADAM-like architecture web interface · prompt-to-design · editable parameters (panel + on-canvas) · universal ArchitectureProject JSON · validation · 2D floor plan preview · 3D massing preview · project storage · exports · AI provider abstraction.

**Exports:** JSON · SVG · PNG · DXF · GLTF preparation · presentation sheet export.

**Architecture intelligence:** room schedule · area calculations · spatial warnings · optional vastu suggestions · design options · version history.

**Software workflows:** AutoCAD through DXF · SketchUp script/plugin · Revit plugin proof-of-concept · Rhino/Grasshopper path · Blender script · Lumion/D5/Enscape/V-Ray workflow strategy · Illustrator/Photoshop/InDesign-friendly exports.

**Scale readiness:** local-first storage · cloud-ready storage abstraction · future auth strategy · future team/collaboration strategy.

## Execution Model

The build proceeds in **Phases 0–20** (see [roadmap.md](roadmap.md)). Each phase is a mini-MVP; each stage inside a phase is implemented fully before moving forward. After every stage: tests run/explained, docs updated, a Stage Completion summary reported, and confirmation requested before the next stage.
