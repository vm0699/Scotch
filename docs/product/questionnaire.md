# Phase 0 Stage 0.1 — Product Questionnaire (Decisions of Record)

Completed 2026-06-12 via structured Q&A. These answers are locked requirements; changes require explicit product-owner approval and a roadmap update.

## 1. Product Identity
**Name:** Scotch (used everywhere — code, API, UI, docs; the `RARCH` folder name is historical).
**Tagline:** "Text-to-design for architecture."
**Positioning:** premium, serious AI architecture software — never a student demo.

## 2. Target Users
Primary: **architects in small studios**. Also: architecture students and interior designers. Homeowner/client mode deferred.

## 3. First MVP Use Case
**2BHK apartment end-to-end**: prompt → plan → edit → export, on a 30x50 ft east-facing site (living, kitchen, 2 bedrooms, 2 bathrooms, balcony, parking). Long-term direction: grow toward full architect-software capability.

## 4. Architecture Design Scope
Concept/schematic stage. Single-floor plans first; multi-floor and facade work in later phases.

## 5. Supported Building Types
Phase 5 generator: **residential** (apartment, villa, studio, duplex) **+ small cafe**. Office layouts in a later stage.

## 6. Prompt Input Behavior
**Smart defaults + warnings:** generate immediately, filling gaps with sensible defaults (e.g. 30x50 ft, east-facing); every assumption surfaced as an editable warning. No blocking follow-up questions.

## 7. Editable Parameters
Site width/depth, orientation, floor height, floors, style, room width/depth/name/type. Parameter model: key, label, value, unit, min, max, editable, category, target entity ID.

## 8. 2D Floor Plan Requirements
**Architectural standard:** double-line walls with thickness, door swing arcs, window symbols, dimension lines, room labels with areas, north arrow, site boundary.

## 9. 3D Preview Requirements
Simple massing: floor slabs, wall extrusions, openings, roof plane; orbit/zoom/pan/reset; 2D/3D toggle; synced with parameter edits.

## 10. Export Requirements
Phase 7 must-haves: **JSON, layered SVG, PNG, and DXF** (layers: A-SITE, A-WALL, A-DOOR, A-WINDOW, A-ROOM-TEXT, A-DIMS).

## 11. Software Integration Priority
**SketchUp and Revit first**, then Blender, then Rhino/Grasshopper. AutoCAD covered via DXF from Phase 7.

## 12. Plugin Priority
Same order — SketchUp extension and Revit add-in are the flagship plugins; script exporters precede full plugins.

## 13. Revit / SketchUp / Rhino / Blender Priority
SketchUp (Ruby script → extension) and Revit (C# add-in PoC) first, then Blender (Python automation), then Rhino (Python script + Grasshopper strategy).

## 14. Rendering Workflow Expectations
Phase 17: render-ready exports (named/grouped objects, material metadata, camera suggestions) plus documented workflows for Lumion, D5, Enscape, V-Ray, and Blender.

## 15. Sheet Presentation Expectations
Phase 12: SVG presentation sheet (title block, plan viewport, room schedule, notes, legend), PDF if feasible, Illustrator-friendly layer structure, Photoshop/InDesign packaging strategy.

## 16. AI Provider and API Keys
**Both providers behind one abstraction from day one:** deterministic / Anthropic / OpenAI-compatible modes selectable in Settings. Keys added later via `.env`. Deterministic mode always works without a key. AI output is parsed, Pydantic-validated, schema-repaired, with deterministic fallback.

## 17. Storage and Auth
Local filesystem: `services/api/app/data/users/local-user/projects/{project_id}/project.json`. No auth for MVP; the `local-user` abstraction allows cloud auth to slot in at Phase 18.

## 18. Local vs Cloud
Local-first. Cloud-ready storage abstraction and strategy at Phase 18; local mode must always keep working.

## 19. UI/UX Direction
**CADAM/adam.new-inspired** premium white interface: left prompt panel, center 2D/3D canvas, right parameters/schedule/exports/warnings. Soft gray borders, professional typography, studio-grade spacing, clean shadows. **In-screen parameter editing after generation, CADAM-style: BOTH right panel and on-canvas (click room → highlight + inline edit popover near selection).**

## 20. Tech Stack Confirmation
Frontend: Next.js (App Router) + React + TypeScript + Tailwind CSS + shadcn/ui + SVG 2D + React Three Fiber 3D.
Backend: Python + FastAPI + Pydantic v2 + local filesystem (optional SQLite later).
Desktop: Tauri later. Mobile companion: Flutter later.
**Units default: feet.**

## 21. Testing and Demo Expectations
Backend **pytest** per stage (parser, generator, validation, exports) + manual UI verification + strict TypeScript. Full demo script at Phase 20.

## 22. Long-Term Product Goals
The 25-item vision list in [brief.md](brief.md) — through versioning, cloud readiness, and team collaboration.

## 23. Existing Project Constraints
Windows 11 dev machine; Node 18+/Python 3.10+/npm assumed available (versions verified at Stage 1.1). No git repo yet — initialized at Stage 1.1. Everything runs fully local.

## 24. Final Acceptance Definition
Phase 20 demo script works end-to-end: create project → 2BHK prompt → generate → edit room dimensions (panel + on-canvas) → regenerate → view 3D → export SVG/JSON/PNG/DXF → show software-integration roadmap. UI presentable to professional architects.
